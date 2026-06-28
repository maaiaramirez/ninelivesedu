const fs = require('fs');
const path = require('path');
const { createHash } = require('crypto');
const initSqlJs = require('sql.js');

const { apuntes } = require('../data/apuntes');
const { tutores } = require('../data/tutores');
const { posts } = require('../data/foros');

const DB_FOLDER = path.join(__dirname, '../../storage');
const DB_FILE = path.join(DB_FOLDER, 'ninelivesedu.sqlite');
const SQL_DIST_PATH = path.join(__dirname, '../../node_modules/sql.js/dist');

let SQL = null;
let db = null;
let readyPromise = null;

const locateFile = (file) => path.join(SQL_DIST_PATH, file);
const PIN_HASH_SECRET = process.env.PIN_HASH_SECRET || 'nine-lives-edu-pin-secret';

function hashPin(pin) {
  return createHash('sha256').update(`${PIN_HASH_SECRET}:${String(pin)}`).digest('hex');
}

function ensureDb() {
  if (!db) {
    throw new Error('La base de datos aún no fue inicializada. Llama a initDatabase primero.');
  }
}

function persist() {
  ensureDb();
  const data = db.export();
  if (!fs.existsSync(DB_FOLDER)) {
    fs.mkdirSync(DB_FOLDER, { recursive: true });
  }
  fs.writeFileSync(DB_FILE, Buffer.from(data));
}

function execAll(sql, params = []) {
  ensureDb();
  const stmt = db.prepare(sql);
  stmt.bind(params);
  const rows = [];
  while (stmt.step()) {
    rows.push(stmt.getAsObject());
  }
  stmt.free();
  return rows;
}

function execOne(sql, params = []) {
  const rows = execAll(sql, params);
  return rows[0] || null;
}

function run(sql, params = [], options = { persist: true }) {
  ensureDb();
  const stmt = db.prepare(sql);
  stmt.run(params);
  stmt.free();
  if (options.persist) {
    persist();
  }
}

function createSchema() {
  db.exec(`
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT NOT NULL UNIQUE,
      full_name TEXT NOT NULL,
      role TEXT NOT NULL CHECK (role IN ('student', 'tutor', 'teacher', 'admin')),
      access_level INTEGER NOT NULL CHECK (access_level BETWEEN 1 AND 100),
      is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
      is_minor INTEGER NOT NULL DEFAULT 0 CHECK (is_minor IN (0, 1)),
      validation_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending', 'approved', 'rejected')),
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS student_profiles (
      user_id TEXT PRIMARY KEY,
      gmail_account TEXT NOT NULL UNIQUE CHECK (gmail_account LIKE '%@gmail.com'),
      birth_date TEXT,
      education_level TEXT,
      emergency_contact_name TEXT,
      emergency_contact_phone TEXT,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tutor_profiles (
      user_id TEXT PRIMARY KEY,
      pedagogical_justification TEXT NOT NULL,
      specialized_subjects_json TEXT NOT NULL DEFAULT '[]',
      ai_confidence_score REAL NOT NULL DEFAULT 0 CHECK (ai_confidence_score >= 0),
      ai_last_evaluated_at TEXT,
      verification_notes TEXT,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS teacher_profiles (
      user_id TEXT PRIMARY KEY,
      credential_document_path TEXT NOT NULL,
      credential_document_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (credential_document_status IN ('pending', 'approved', 'rejected')),
      unique_pin_ciphertext TEXT NOT NULL UNIQUE,
      pin_issued_at TEXT NOT NULL,
      hardware_terminal_alias TEXT,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS admin_profiles (
      user_id TEXT PRIMARY KEY,
      admin_scope TEXT NOT NULL DEFAULT 'full'
        CHECK (admin_scope IN ('full')),
      can_moderate_forums INTEGER NOT NULL DEFAULT 1 CHECK (can_moderate_forums IN (0, 1)),
      can_validate_teachers INTEGER NOT NULL DEFAULT 1 CHECK (can_validate_teachers IN (0, 1)),
      can_manage_finance INTEGER NOT NULL DEFAULT 1 CHECK (can_manage_finance IN (0, 1)),
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS teacher_document_audits (
      id TEXT PRIMARY KEY,
      teacher_user_id TEXT NOT NULL,
      reviewer_admin_user_id TEXT NOT NULL,
      decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
      notes TEXT,
      reviewed_at TEXT NOT NULL,
      FOREIGN KEY (teacher_user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (reviewer_admin_user_id) REFERENCES users(id) ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS teacher_attendance (
      teacher_user_id TEXT PRIMARY KEY,
      terminal_id TEXT NOT NULL,
      is_available INTEGER NOT NULL DEFAULT 0 CHECK (is_available IN (0, 1)),
      last_seen_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (teacher_user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS apuntes (
      id TEXT PRIMARY KEY,
      titulo TEXT NOT NULL,
      materia TEXT NOT NULL,
      nivel TEXT NOT NULL,
      autor TEXT,
      fecha TEXT NOT NULL,
      descripcion TEXT,
      tipo TEXT,
      rating REAL DEFAULT 0,
      descargas INTEGER DEFAULT 0,
      icono TEXT,
      archivo TEXT
    );

    CREATE TABLE IF NOT EXISTS tutores (
      id TEXT PRIMARY KEY,
      nombre TEXT NOT NULL,
      materia TEXT NOT NULL,
      nivel TEXT NOT NULL,
      precio REAL NOT NULL,
      rating REAL DEFAULT 0,
      experiencia TEXT,
      foto TEXT,
      biografia TEXT,
      materias_json TEXT,
      disponibilidad_json TEXT,
      idiomas_json TEXT,
      resenas_json TEXT
    );

    CREATE TABLE IF NOT EXISTS reservas (
      id TEXT PRIMARY KEY,
      tutor_id TEXT NOT NULL,
      estudiante TEXT NOT NULL,
      fecha TEXT NOT NULL,
      modalidad TEXT DEFAULT 'online',
      created_at TEXT NOT NULL,
      FOREIGN KEY (tutor_id) REFERENCES tutores(id)
    );

    CREATE TABLE IF NOT EXISTS swap_requests (
      id TEXT PRIMARY KEY,
      nombre TEXT NOT NULL,
      materia_ofreces TEXT NOT NULL,
      materia_solicitas TEXT NOT NULL,
      descripcion TEXT,
      fecha TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS posts (
      id TEXT PRIMARY KEY,
      titulo TEXT NOT NULL,
      contenido TEXT NOT NULL,
      autor TEXT NOT NULL,
      fecha TEXT NOT NULL,
      nivel TEXT,
      materia TEXT,
      tipo TEXT,
      tags_json TEXT,
      votos INTEGER DEFAULT 0,
      respuestas INTEGER DEFAULT 0,
      vistas INTEGER DEFAULT 0,
      resuelto INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS post_responses (
      id TEXT PRIMARY KEY,
      post_id TEXT NOT NULL,
      autor TEXT NOT NULL,
      fecha TEXT NOT NULL,
      texto TEXT NOT NULL,
      FOREIGN KEY (post_id) REFERENCES posts(id)
    );

    CREATE TRIGGER IF NOT EXISTS trg_student_profile_role_check
    BEFORE INSERT ON student_profiles
    FOR EACH ROW
    WHEN (SELECT role FROM users WHERE id = NEW.user_id) <> 'student'
    BEGIN
      SELECT RAISE(ABORT, 'El perfil de alumno solo puede asociarse a usuarios con rol student');
    END;

    CREATE TRIGGER IF NOT EXISTS trg_tutor_profile_role_check
    BEFORE INSERT ON tutor_profiles
    FOR EACH ROW
    WHEN (SELECT role FROM users WHERE id = NEW.user_id) <> 'tutor'
    BEGIN
      SELECT RAISE(ABORT, 'El perfil de tutor solo puede asociarse a usuarios con rol tutor');
    END;

    CREATE TRIGGER IF NOT EXISTS trg_teacher_profile_role_check
    BEFORE INSERT ON teacher_profiles
    FOR EACH ROW
    WHEN (SELECT role FROM users WHERE id = NEW.user_id) <> 'teacher'
    BEGIN
      SELECT RAISE(ABORT, 'El perfil de profesor solo puede asociarse a usuarios con rol teacher');
    END;

    CREATE TRIGGER IF NOT EXISTS trg_admin_profile_role_check
    BEFORE INSERT ON admin_profiles
    FOR EACH ROW
    WHEN (SELECT role FROM users WHERE id = NEW.user_id) <> 'admin'
    BEGIN
      SELECT RAISE(ABORT, 'El perfil de admin solo puede asociarse a usuarios con rol admin');
    END;
  `);
}

function seedAdminUsers() {
  const adminUsers = [
    { id: 'admin-1', email: 'admin1@ninelivesedu.org', fullName: 'Admin Principal' },
    { id: 'admin-2', email: 'admin2@ninelivesedu.org', fullName: 'Admin Operaciones' },
    { id: 'admin-3', email: 'admin3@ninelivesedu.org', fullName: 'Admin Finanzas' }
  ];

  adminUsers.forEach((admin) => {
    run(
      `INSERT OR IGNORE INTO users (
        id, email, full_name, role, access_level, is_active, is_minor,
        validation_status, created_at, updated_at
      ) VALUES (?, ?, ?, 'admin', 100, 1, 0, 'approved', datetime('now'), datetime('now'))`,
      [admin.id, admin.email, admin.fullName],
      { persist: false }
    );

    run(
      `INSERT OR IGNORE INTO admin_profiles (
        user_id, admin_scope, can_moderate_forums, can_validate_teachers, can_manage_finance
      ) VALUES (?, 'full', 1, 1, 1)`,
      [admin.id],
      { persist: false }
    );
  });
}

function seedTeacherDemoUser() {
  const teacherId = 'teacher-demo-1';
  const defaultPin = '123456';
  const nowIso = new Date().toISOString();

  run(
    `INSERT OR IGNORE INTO users (
      id, email, full_name, role, access_level, is_active, is_minor,
      validation_status, created_at, updated_at
    ) VALUES (?, ?, ?, 'teacher', 80, 1, 0, 'approved', ?, ?)`,
    [teacherId, 'profesor.demo@ninelivesedu.org', 'Profesor Demo', nowIso, nowIso],
    { persist: false }
  );

  run(
    `INSERT OR IGNORE INTO teacher_profiles (
      user_id, credential_document_path, credential_document_status, unique_pin_ciphertext, pin_issued_at, hardware_terminal_alias
    ) VALUES (?, ?, 'approved', ?, ?, ?)`,
    [teacherId, '/docs/profesor-demo.pdf', hashPin(defaultPin), nowIso, 'terminal-demo-1'],
    { persist: false }
  );
}

function seedIfEmpty() {
  seedAdminUsers();
  seedTeacherDemoUser();

  const apunteCount = execOne('SELECT COUNT(*) as total FROM apuntes');
  if (Number(apunteCount.total) === 0) {
    apuntes.forEach((apunte) => {
      run(
        `INSERT INTO apuntes (id, titulo, materia, nivel, autor, fecha, descripcion, tipo, rating, descargas, icono, archivo)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          apunte.id,
          apunte.titulo,
          apunte.materia,
          apunte.nivel,
          apunte.autor,
          apunte.fecha,
          apunte.descripcion,
          apunte.tipo,
          apunte.rating,
          apunte.descargas,
          apunte.icono,
          apunte.archivo
        ],
        { persist: false }
      );
    });
  }

  const tutorCount = execOne('SELECT COUNT(*) as total FROM tutores');
  if (Number(tutorCount.total) === 0) {
    tutores.forEach((tutor) => {
      run(
        `INSERT INTO tutores (
          id, nombre, materia, nivel, precio, rating, experiencia, foto, biografia,
          materias_json, disponibilidad_json, idiomas_json, resenas_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          tutor.id,
          tutor.nombre,
          tutor.materia,
          tutor.nivel,
          tutor.precio,
          tutor.rating,
          tutor.experiencia,
          tutor.foto,
          tutor.biografia,
          JSON.stringify(tutor.materias || []),
          JSON.stringify(tutor.disponibilidad || {}),
          JSON.stringify(tutor.idiomas || []),
          JSON.stringify(tutor.reseñas || [])
        ],
        { persist: false }
      );
    });
  }

  const postCount = execOne('SELECT COUNT(*) as total FROM posts');
  if (Number(postCount.total) === 0) {
    posts.forEach((post) => {
      run(
        `INSERT INTO posts (
          id, titulo, contenido, autor, fecha, nivel, materia, tipo,
          tags_json, votos, respuestas, vistas, resuelto
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          post.id,
          post.titulo,
          post.contenido,
          post.autor,
          post.fecha,
          post.nivel,
          post.materia,
          post.tipo,
          JSON.stringify(post.tags || []),
          post.votos,
          post.respuestas,
          post.vistas,
          post.resuelto ? 1 : 0
        ],
        { persist: false }
      );

      (post.responses || []).forEach((resp) => {
        run(
          `INSERT INTO post_responses (id, post_id, autor, fecha, texto)
           VALUES (?, ?, ?, ?, ?)`,
          [resp.id, post.id, resp.autor, resp.fecha, resp.texto],
          { persist: false }
        );
      });
    });
  }

  persist();
}

function initDatabase() {
  if (!readyPromise) {
    readyPromise = (async () => {
      SQL = await initSqlJs({ locateFile });

      if (fs.existsSync(DB_FILE)) {
        const fileBuffer = fs.readFileSync(DB_FILE);
        db = new SQL.Database(fileBuffer);
        createSchema();
        seedAdminUsers();
        seedTeacherDemoUser();
        persist();
      } else {
        db = new SQL.Database();
        createSchema();
        seedIfEmpty();
      }

      return db;
    })();
  }

  return readyPromise;
}

module.exports = {
  initDatabase,
  execAll,
  execOne,
  run,
  persist,
  hashPin
};

