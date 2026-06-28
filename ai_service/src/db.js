const { Pool } = require('pg');
require('dotenv').config(); // Lee el archivo .env automáticamente

const pool = new Pool({
  user: process.env.DB_USER,
  host: process.env.DB_HOST,
  database: process.env.DB_NAME,
  password: process.env.DB_PASSWORD,
  port: process.env.DB_PORT,
});

// Al arrancar, esto te va a avisar en la consola si se conectó bien
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('❌ Error conectando a PostgreSQL:', err.stack);
  } else {
    console.log('✅ Conexión exitosa a la Base de Datos de Nine Lives Edu');
  }
});

module.exports = pool;