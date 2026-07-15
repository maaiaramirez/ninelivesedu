const express = require('express');
const path = require('path');
const fs = require('fs');
const cors = require('cors');
const morgan = require('morgan');

const { initDatabase } = require('./db/database');
const apuntesRouter = require('./routes/apuntes');
const tutoresRouter = require('./routes/tutores');
const forosRouter = require('./routes/foros');
const asistenciaRouter = require('./routes/asistencia');

const app = express();
const PORT = process.env.PORT || 3000;
const PUBLIC_DIR = path.join(__dirname, '../codigos pagina');
const UPLOADS_DIR = path.join(__dirname, '../storage/uploads');

if (!fs.existsSync(UPLOADS_DIR)) {
  fs.mkdirSync(UPLOADS_DIR, { recursive: true });
}

app.use(cors());
app.use(express.json());
app.use(morgan('dev'));

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.use('/api/apuntes', apuntesRouter);
app.use('/api/tutores', tutoresRouter);
app.use('/api/foros', forosRouter);
app.use('/api/asistencia', asistenciaRouter);

// ─────────────────────────────────────────────
// PROXY DEL CHATBOT → microservicio FastAPI (ai_service)
// El frontend le pide a este mismo dominio (/api/chat),
// y acá lo reenviamos al servicio de Python real.
// Configurá AI_SERVICE_URL en las variables de entorno de Render.
// ─────────────────────────────────────────────
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://127.0.0.1:8000';

app.post('/api/chat', async (req, res) => {
  try {
    const { message } = req.body;
    if (!message) {
      return res.status(400).json({ success: false, error: 'El mensaje no puede estar vacío.' });
    }

    const response = await fetch(`${AI_SERVICE_URL}/api/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`El servicio de IA respondió con status ${response.status}`);
    }

    const data = await response.json();
    return res.json({ success: true, reply: data.reply });
  } catch (error) {
    console.error('[Proxy /api/chat] Error al conectar con ai_service:', error.message);
    return res.status(502).json({
      success: false,
      error: 'No se pudo conectar con el servicio de IA. Asegurate de que esté encendido.',
    });
  }
});

app.use(express.static(PUBLIC_DIR));
app.use('/uploads', express.static(UPLOADS_DIR));

app.use('/api', (req, res) => {
  res.status(404).json({ message: 'Recurso no encontrado' });
});

app.use((req, res, next) => {
  if (req.method !== 'GET' || !req.accepts('html')) {
    return next();
  }
  res.sendFile(path.join(PUBLIC_DIR, 'index.html'));
});

initDatabase()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Servidor escuchando en http://localhost:${PORT}`);
    });
  })
  .catch((error) => {
    console.error('Error al inicializar la base de datos:', error);
    process.exit(1);
  });
