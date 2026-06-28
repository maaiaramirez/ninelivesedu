const express = require('express');
const { randomUUID } = require('crypto');
const { execAll, execOne, run } = require('../db/database');

const router = express.Router();

router.get('/', (req, res) => {
  try {
    const rows = execAll('SELECT * FROM posts ORDER BY date(fecha) DESC');
    const posts = rows.map(hydratePost);
    res.json(posts);
  } catch (error) {
    res.status(500).json({ message: 'No se pudieron obtener los foros', detail: error.message });
  }
});

router.get('/:id', (req, res) => {
  try {
    const row = execOne('SELECT * FROM posts WHERE id = ?', [req.params.id]);
    if (!row) {
      return res.status(404).json({ message: 'Post no encontrado' });
    }
    res.json(hydratePost(row));
  } catch (error) {
    res.status(500).json({ message: 'No se pudo obtener el post', detail: error.message });
  }
});

router.post('/', (req, res) => {
  const { titulo, contenido, autor, nivel, materia, tipo, tags } = req.body;

  if (!titulo || !contenido || !autor) {
    return res.status(400).json({ message: 'Título, contenido y autor son obligatorios.' });
  }

  const nuevoPost = {
    id: `post-${randomUUID()}`,
    titulo,
    contenido,
    autor,
    fecha: new Date().toISOString().split('T')[0],
    nivel: nivel || 'universidad',
    materia: materia || 'general',
    tipo: tipo || 'pregunta',
    tags: Array.isArray(tags) ? tags : [],
    votos: 0,
    respuestas: 0,
    vistas: 0,
    resuelto: false,
    responses: []
  };

  try {
    run(
      `INSERT INTO posts (
        id, titulo, contenido, autor, fecha, nivel, materia, tipo,
        tags_json, votos, respuestas, vistas, resuelto
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        nuevoPost.id,
        nuevoPost.titulo,
        nuevoPost.contenido,
        nuevoPost.autor,
        nuevoPost.fecha,
        nuevoPost.nivel,
        nuevoPost.materia,
        nuevoPost.tipo,
        JSON.stringify(nuevoPost.tags),
        nuevoPost.votos,
        nuevoPost.respuestas,
        nuevoPost.vistas,
        nuevoPost.resuelto ? 1 : 0
      ]
    );

    res.status(201).json(nuevoPost);
  } catch (error) {
    res.status(500).json({ message: 'No se pudo crear el post', detail: error.message });
  }
});

router.post('/:id/vote', (req, res) => {
  try {
    const post = execOne('SELECT id, votos FROM posts WHERE id = ?', [req.params.id]);
    if (!post) {
      return res.status(404).json({ message: 'Post no encontrado' });
    }

    run('UPDATE posts SET votos = votos + 1 WHERE id = ?', [post.id]);
    res.json({ votos: Number(post.votos) + 1 });
  } catch (error) {
    res.status(500).json({ message: 'No se pudo registrar el voto', detail: error.message });
  }
});

router.post('/:id/respuestas', (req, res) => {
  const { autor, texto } = req.body;
  if (!autor || !texto) {
    return res.status(400).json({ message: 'Autor y texto son obligatorios.' });
  }

  try {
    const post = execOne('SELECT id FROM posts WHERE id = ?', [req.params.id]);
    if (!post) {
      return res.status(404).json({ message: 'Post no encontrado' });
    }

    const respuesta = {
      id: `resp-${randomUUID()}`,
      postId: post.id,
      autor,
      fecha: new Date().toISOString().split('T')[0],
      texto
    };

    run(
      `INSERT INTO post_responses (id, post_id, autor, fecha, texto)
       VALUES (?, ?, ?, ?, ?)`,
      [respuesta.id, respuesta.postId, respuesta.autor, respuesta.fecha, respuesta.texto]
    );

    run('UPDATE posts SET respuestas = respuestas + 1 WHERE id = ?', [post.id]);

    res.status(201).json({
      id: respuesta.id,
      autor: respuesta.autor,
      fecha: respuesta.fecha,
      texto: respuesta.texto
    });
  } catch (error) {
    res.status(500).json({ message: 'No se pudo agregar la respuesta', detail: error.message });
  }
});

function hydratePost(row) {
  const responses = execAll(
    'SELECT id, autor, fecha, texto FROM post_responses WHERE post_id = ? ORDER BY date(fecha) ASC, rowid ASC',
    [row.id]
  );

  return {
    id: row.id,
    titulo: row.titulo,
    contenido: row.contenido,
    autor: row.autor,
    fecha: row.fecha,
    nivel: row.nivel,
    materia: row.materia,
    tipo: row.tipo,
    tags: safeParse(row.tags_json, []),
    votos: Number(row.votos || 0),
    respuestas: Number(row.respuestas || responses.length),
    vistas: Number(row.vistas || 0),
    resuelto: Boolean(row.resuelto),
    responses
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

