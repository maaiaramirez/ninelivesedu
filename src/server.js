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

