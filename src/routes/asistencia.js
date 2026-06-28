const express = require('express');
const { execAll, execOne, run, hashPin } = require('../db/database');
const { addClient, removeClient, publishTeachers } = require('../services/attendanceRealtime');

const router = express.Router();

const ESP32_API_KEY = process.env.ESP32_API_KEY || 'esp32-local-key';

router.get('/profesores-disponibles', (req, res) => {
  try {
    const teachers = listAvailableTeachers();
    res.json({ total: teachers.length, teachers });
  } catch (error) {
    res.status(500).json({ message: 'No se pudo listar disponibilidad', detail: error.message });
  }
});

router.get('/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  addClient(res);
  res.write(`event: connected\ndata: {"status":"ok"}\n\n`);
  publishTeachers(listAvailableTeachers());

  req.on('close', () => {
    removeClient(res);
    res.end();
  });
});

router.post('/esp32/check-in', (req, res) => {
  if (!isAuthorizedEsp32(req)) {
    return res.status(401).json({ message: 'Dispositivo no autorizado' });
  }

  const { pin, terminalId } = req.body;
  if (!pin || !terminalId) {
    return res.status(400).json({ message: 'pin y terminalId son obligatorios' });
  }

  try {
    const teacher = findTeacherByPin(pin);
    if (!teacher) {
      return res.status(404).json({ message: 'PIN inválido' });
    }

    run(
      `INSERT INTO teacher_attendance (teacher_user_id, terminal_id, is_available, last_seen_at, updated_at)
       VALUES (?, ?, 1, datetime('now'), datetime('now'))
       ON CONFLICT(teacher_user_id) DO UPDATE SET
         terminal_id = excluded.terminal_id,
         is_available = 1,
         last_seen_at = datetime('now'),
         updated_at = datetime('now')`,
      [teacher.userId, terminalId]
    );

    publishTeachers(listAvailableTeachers());
    res.json({ message: 'Asistencia activada', teacher: { id: teacher.userId, nombre: teacher.fullName }, terminalId });
  } catch (error) {
    res.status(500).json({ message: 'No se pudo registrar asistencia', detail: error.message });
  }
});

router.post('/esp32/check-out', (req, res) => {
  if (!isAuthorizedEsp32(req)) {
    return res.status(401).json({ message: 'Dispositivo no autorizado' });
  }

  const { pin } = req.body;
  if (!pin) {
    return res.status(400).json({ message: 'pin es obligatorio' });
  }

  try {
    const teacher = findTeacherByPin(pin);
    if (!teacher) {
      return res.status(404).json({ message: 'PIN inválido' });
    }

    run(
      `UPDATE teacher_attendance
       SET is_available = 0, updated_at = datetime('now')
       WHERE teacher_user_id = ?`,
      [teacher.userId]
    );

    publishTeachers(listAvailableTeachers());
    res.json({ message: 'Asistencia finalizada', teacher: { id: teacher.userId, nombre: teacher.fullName } });
  } catch (error) {
    res.status(500).json({ message: 'No se pudo finalizar asistencia', detail: error.message });
  }
});

function listAvailableTeachers() {
  return execAll(
    `SELECT
      u.id AS user_id,
      u.full_name,
      u.email,
      ta.terminal_id,
      ta.last_seen_at,
      ta.updated_at
     FROM teacher_attendance ta
     INNER JOIN users u ON u.id = ta.teacher_user_id
     WHERE u.role = 'teacher'
       AND u.validation_status = 'approved'
       AND ta.is_available = 1
     ORDER BY u.full_name ASC`
  ).map((row) => ({
    userId: row.user_id,
    fullName: row.full_name,
    email: row.email,
    terminalId: row.terminal_id,
    lastSeenAt: row.last_seen_at,
    updatedAt: row.updated_at
  }));
}

function findTeacherByPin(pin) {
  const pinHash = hashPin(pin);
  return execOne(
    `SELECT u.id AS userId, u.full_name AS fullName
     FROM teacher_profiles tp
     INNER JOIN users u ON u.id = tp.user_id
     WHERE u.role = 'teacher'
       AND u.validation_status = 'approved'
       AND tp.unique_pin_ciphertext = ?`,
    [pinHash]
  );
}

function isAuthorizedEsp32(req) {
  const apiKey = req.header('x-esp32-key');
  return apiKey && apiKey === ESP32_API_KEY;
}

module.exports = router;
