const express = require('express');
const fs = require('fs');
const path = require('path');
const { randomUUID } = require('crypto');
const multer = require('multer');
const { execAll, execOne, run } = require('../db/database');

const router = express.Router();
const UPLOADS_FOLDER = path.join(__dirname, '../../storage/uploads');

if (!fs.existsSync(UPLOADS_FOLDER)) {
  fs.mkdirSync(UPLOADS_FOLDER, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOADS_FOLDER),
  filename: (_req, file, cb) => {
    const cleanName = file.originalname
      .toLowerCase()
      .replace(/[^a-z0-9._-]/g, '-')
      .replace(/-+/g, '-');
    cb(null, `${Date.now()}-${cleanName}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 15 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const allowedMimes = new Set([
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-powerpoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'image/png',
      'image/jpeg',
      'image/webp'
    ]);

    if (!allowedMimes.has(file.mimetype)) {
      return cb(new Error('Tipo de archivo no permitido.'));
    }

    cb(null, true);
  }
});

router.get('/', (req, res) => {
  try {
    const apuntes = execAll('SELECT * FROM apuntes ORDER BY date(fecha) DESC');
    res.json(apuntes);
  } catch (error) {
    res.status(500).json({ message: 'No se pudieron obtener los apuntes', detail: error.message });
  }
});

router.get('/:id', (req, res) => {
  try {
    const apunte = execOne('SELECT * FROM apuntes WHERE id = ?', [req.params.id]);
    if (!apunte) {
      return res.status(404).json({ message: 'Apunte no encontrado' });
    }
    res.json(apunte);
  } catch (error) {
    res.status(500).json({ message: 'No se pudo obtener el apunte', detail: error.message });
  }
});

router.post('/', upload.single('archivo'), (req, res) => {
  const body = req.body || {};
  const titulo = body.titulo;
  const materia = body.materia;
  const nivel = body.nivel;
  const autor = body.autor;
  const descripcion = body.descripcion;
  const tipo = body.tipo;
  const uploadedFile = req.file;

  if (!titulo || !materia || !nivel) {
    return res.status(400).json({ message: 'Título, materia y nivel son obligatorios.' });
  }

  const id = `apunte-${randomUUID()}`;
  const fecha = new Date().toISOString().split('T')[0];
  const nuevoApunte = {
    id,
    titulo,
    materia,
    nivel,
    autor: autor || 'Autor anónimo',
    fecha,
    descripcion: descripcion || 'Apunte recién agregado por la comunidad.',
    tipo: tipo || getExtension(uploadedFile?.originalname || ''),
    rating: 4.5,
    descargas: 0,
    icono: getMateriaIcon(materia),
    archivo: uploadedFile ? `/uploads/${uploadedFile.filename}` : `${titulo.toLowerCase().replace(/\s+/g, '_')}.pdf`
  };

  try {
    run(
      `INSERT INTO apuntes (id, titulo, materia, nivel, autor, fecha, descripcion, tipo, rating, descargas, icono, archivo)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        nuevoApunte.id,
        nuevoApunte.titulo,
        nuevoApunte.materia,
        nuevoApunte.nivel,
        nuevoApunte.autor,
        nuevoApunte.fecha,
        nuevoApunte.descripcion,
        nuevoApunte.tipo,
        nuevoApunte.rating,
        nuevoApunte.descargas,
        nuevoApunte.icono,
        nuevoApunte.archivo
      ]
    );
    res.status(201).json(nuevoApunte);
  } catch (error) {
    res.status(500).json({ message: 'No se pudo registrar el apunte', detail: error.message });
  }
});

router.get('/:id/descargar', (req, res) => {
  try {
    const apunte = execOne('SELECT * FROM apuntes WHERE id = ?', [req.params.id]);
    if (!apunte) {
      return res.status(404).json({ message: 'Apunte no encontrado' });
    }

    if (!apunte.archivo || !apunte.archivo.startsWith('/uploads/')) {
      return res.status(400).json({ message: 'Este apunte no tiene archivo físico asociado.' });
    }

    const absolutePath = path.join(UPLOADS_FOLDER, path.basename(apunte.archivo));
    if (!fs.existsSync(absolutePath)) {
      return res.status(404).json({ message: 'Archivo no encontrado en almacenamiento.' });
    }

    return res.download(absolutePath);
  } catch (error) {
    return res.status(500).json({ message: 'No se pudo descargar el archivo', detail: error.message });
  }
});

router.post('/:id/descargas', (req, res) => {
  try {
    const apunte = execOne('SELECT * FROM apuntes WHERE id = ?', [req.params.id]);
    if (!apunte) {
      return res.status(404).json({ message: 'Apunte no encontrado' });
    }

    run('UPDATE apuntes SET descargas = descargas + 1 WHERE id = ?', [apunte.id]);
    apunte.descargas += 1;

    res.json(apunte);
  } catch (error) {
    res.status(500).json({ message: 'No se pudo actualizar el contador de descargas', detail: error.message });
  }
});

function getMateriaIcon(materia) {
  const icons = {
    matematicas: 'fas fa-calculator',
    fisica: 'fas fa-atom',
    quimica: 'fas fa-flask',
    biologia: 'fas fa-microscope',
    historia: 'fas fa-landmark',
    literatura: 'fas fa-book',
    ingles: 'fas fa-language',
    filosofia: 'fas fa-brain'
  };

  return icons[materia] || 'fas fa-book-open';
}

function getExtension(filename = '') {
  const parts = filename.split('.');
  return parts.length > 1 ? parts.pop().toLowerCase() : 'pdf';
}

module.exports = router;

