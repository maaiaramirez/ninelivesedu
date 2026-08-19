/*
  NINE LIVES EDU - Conexión con el nodo físico (vía backend en Render)
  =====================================================================
  Esta web ya NO se conecta directo a la IP local del ESP32 (eso solo
  funciona si estás en la misma red Wi-Fi que el hardware). En su lugar,
  se conecta al backend público desplegado en Render, al que el ESP32
  también se conecta como cliente. Así el indicador funciona para
  cualquiera que abra el sitio, desde cualquier red.

  Antes de usar: reemplaza RENDER_HOST por el dominio que te dio Render
  al desplegar backend_ejemplo.py (sin "https://", sin barra al final).
*/

const RENDER_HOST = "nine-lives-edu-backend.onrender.com"; // <-- CAMBIAR
const AULA_ID = "A1"; // debe coincidir con el AULA_ID configurado en el .ino

let socket = null;
let reintentoTimeout = null;

function conectarAlNodo() {
  const statusEl = document.getElementById('deviceStatus');
  if (!statusEl) return; // esta pagina no tiene el indicador, no hacemos nada

  const statusText = statusEl.querySelector('.device-status-text');
  const url = `wss://${RENDER_HOST}/ws/aula/${AULA_ID}`;

  socket = new WebSocket(url);

  socket.onopen = () => {
    console.log('[Nine Lives Edu] Conectado al backend:', url);
    // El estado real llega enseguida via mensaje "estado"; mientras tanto
    // dejamos un estado neutro para no mostrar "desconectado" de mas.
  };

  socket.onmessage = (evento) => {
    let mensaje;
    try {
      mensaje = JSON.parse(evento.data);
    } catch (err) {
      console.warn('[Nine Lives Edu] Mensaje no valido del backend:', evento.data);
      return;
    }

    if (mensaje.tipo !== 'estado') return;
    actualizarIndicador(statusEl, statusText, mensaje.estado);
  };

  socket.onclose = () => {
    console.log('[Nine Lives Edu] Conexion con el backend perdida. Reintentando en 5s...');
    actualizarIndicador(statusEl, statusText, 'OFFLINE');
    reintentoTimeout = setTimeout(conectarAlNodo, 5000);
  };

  socket.onerror = (err) => {
    console.error('[Nine Lives Edu] Error de WebSocket:', err);
    socket.close();
  };
}

function actualizarIndicador(statusEl, statusText, estado) {
  switch (estado) {
    case 'DISP':
      statusEl.dataset.state = 'online';
      statusText.textContent = 'Aula disponible';
      break;
    case 'OCUP':
      statusEl.dataset.state = 'ocupado';
      statusText.textContent = 'Consulta privada en curso';
      break;
    case 'INAC':
      statusEl.dataset.state = 'offline';
      statusText.textContent = 'Sin actividad de tutoría';
      break;
    default: // OFFLINE (sin conexion con el hardware)
      statusEl.dataset.state = 'offline';
      statusText.textContent = 'Aula desconectada';
      break;
  }
}

document.addEventListener('DOMContentLoaded', conectarAlNodo);
