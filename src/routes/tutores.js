const express = require('express');
const { randomUUID } = require('crypto');
const { execAll, execOne, run } = require('../db/database');

const router = express.Router();

router.get('/', (req, res) => {
  try {
    const rows = execAll('SELECT * FROM tutores ORDER BY nombre ASC');
    res.json(rows.map(normalizeTutor));
  } catch (error) {
    res.status(500).json({ message: 'No se pudieron obtener los tutores', detail: error.message });
  }
});

router.get('/:id', (req, res) => {
  try {
    const row = execOne('SELECT * FROM tutores WHERE id = ?', [req.params.id]);
    if (!row) {
      return res.status(404).json({ message: 'Tutor no encontrado' });
    }
    res.json(normalizeTutor(row));
  } catch (error) {
    res.status(500).json({ message: 'No se pudo obtener el tutor', detail: error.message });
  }
});

router.post('/:id/reservas', (req, res) => {
  try {
    const row = execOne('SELECT * FROM tutores WHERE id = ?', [req.params.id]);
    if (!row) {
      return res.status(404).json({ message: 'Tutor no encontrado' });
    }

    const { estudiante, fecha, modalidad } = req.body;
    if (!estudiante || !fecha) {
      return res.status(400).json({ message: 'Debes indicar estudiante y fecha deseada.' });
    }

    const reserva = {
      id: `reserva-${randomUUID()}`,
      tutorId: row.id,
      tutor: row.nombre,
      estudiante,
      fecha,
      modalidad: modalidad || 'online',
      createdAt: new Date().toISOString()
    };

    run(
      `INSERT INTO reservas (id, tutor_id, estudiante, fecha, modalidad, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [reserva.id, reserva.tutorId, reserva.estudiante, reserva.fecha, reserva.modalidad, reserva.createdAt]
    );

    res.status(201).json({
      message: 'Reserva solicitada. El tutor confirmará la disponibilidad.',
      reserva: {
        id: reserva.id,
        tutor: reserva.tutor,
        estudiante: reserva.estudiante,
        fecha: reserva.fecha,
        modalidad: reserva.modalidad
      }
    });
  } catch (error) {
    res.status(500).json({ message: 'No se pudo crear la reserva', detail: error.message });
  }
});

router.post('/intercambios', (req, res) => {
  const { nombre, materiaOfreces, materiaSolicitas, descripcion } = req.body;

  if (!nombre || !materiaOfreces || !materiaSolicitas) {
    return res.status(400).json({ message: 'Completa los campos obligatorios.' });
  }

  const solicitud = {
    id: `swap-${randomUUID()}`,
    nombre,
    materia_ofreces: materiaOfreces,
    materia_solicitas: materiaSolicitas,
    descripcion: descripcion || 'Sin descripción adicional',
    fecha: new Date().toISOString()
  };

  try {
    run(
      `INSERT INTO swap_requests (id, nombre, materia_ofreces, materia_solicitas, descripcion, fecha)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [
        solicitud.id,
        solicitud.nombre,
        solicitud.materia_ofreces,
        solicitud.materia_solicitas,
        solicitud.descripcion,
        solicitud.fecha
      ]
    );

    res.status(201).json({
      message: 'Solicitud de intercambio registrada. Te notificaremos cuando encontremos un match.',
      solicitud
    });
  } catch (error) {
    res.status(500).json({ message: 'No se pudo registrar el intercambio', detail: error.message });
  }
});

function normalizeTutor(row) {
  if (!row) return null;

  return {
    id: row.id,
    nombre: row.nombre,
    materia: row.materia,
    nivel: row.nivel,
    precio: Number(row.precio),
    rating: Number(row.rating),
    experiencia: row.experiencia,
    foto: row.foto,
    biografia: row.biografia,
    materias: safeParse(row.materias_json, []),
    disponibilidad: safeParse(row.disponibilidad_json, {}),
    idiomas: safeParse(row.idiomas_json, []),
    reseñas: safeParse(row.resenas_json, [])
  };
}

function safeParse(value, fallback) {
  if (!value) return fallback;
  try {
    return JSON.parse(value);
  } catch (error) {
    return fallback;
  }
}

module.exports = router;

