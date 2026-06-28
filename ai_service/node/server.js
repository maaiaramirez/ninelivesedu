const express = require('express');
const axios = require('axios');
const cors = require('cors');
require('dotenv').config(); // Lee el archivo .env para configuraciones dinámicas

const app = express();
app.use(cors());
app.use(express.json());

// Configuración flexible para Hosting (Render) o Desarrollo Local
const NODE_PORT = process.env.PORT || 3000;
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000/api/v1/chat';

// Endpoint del Puente para Alumnos (Chatbot) y Moderadores
app.post('/api/chat', async (req, res) => {
    try {
        const { message } = req.body;

        if (!message) {
            return res.status(400).json({ error: 'El mensaje no puede estar vacío.' });
        }

        console.log(`[NodeJS] Recibido: "${message}". Reenviando a Python...`);

        // Conexión interna con el microservicio de IA en Python
        const response = await axios.post(PYTHON_API_URL, {
            message: message
        });

        console.log('[NodeJS] Python respondió con éxito.');

        return res.json({
            success: true,
            reply: response.data.reply
        });

    } catch (error) {
        console.error('[NodeJS] Error al conectar con Python:', error.message);
        return res.status(500).json({
            success: false,
            error: '¿Te olvidaste de dejar prendido Python en la otra terminal?'
        });
    }
});

// Encendido del Servidor Central
app.listen(NODE_PORT, () => {
    console.log(`🚀 Servidor central de Node.js corriendo en el puerto ${NODE_PORT}`);
});