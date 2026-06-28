const { Pool } = require('pg');
require('dotenv').config(); // Carga las variables del .env

// Configuración del Pool de conexiones
const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: process.env.DB_PORT,
  max: 20, // Máximo de clientes conectados simultáneos
  idleTimeoutMillis: 30000, // Tiempo para cerrar conexiones inactivas
  connectionTimeoutMillis: 2000, // Tiempo límite para conectar
});

// Verificar la conexión con el servidor de Postgres en Arch Linux
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('❌ Error crítico al conectar a PostgreSQL:', err.stack);
  } else {
    console.log('✅ Conexión exitosa y segura a la Base de Datos de Nine Lives Edu.');
  }
});

// Exportamos el pool para usarlo en los controladores de las rutas
module.exports = pool;
