/* ═══════════════════════════════════════════════════════
   STUDY WAWA — components.js
   Light/Dark mode toggle + Chatbot bubble
═══════════════════════════════════════════════════════ */
(function () {
    'use strict';

    /* ─────────────────────────────────────────
       THEME TOGGLE
    ───────────────────────────────────────── */
    const THEME_KEY = 'sw_theme';

    function getTheme() {
        return localStorage.getItem(THEME_KEY) ||
            (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
    }

    function injectThemeToggle() {
        // Inject button into every .header-buttons found
        const containers = document.querySelectorAll('.header-buttons');
        containers.forEach(function (container) {
            if (container.querySelector('.btn-theme-toggle')) return; // already there
            const btn = document.createElement('button');
            btn.className = 'btn-theme-toggle';
            btn.setAttribute('aria-label', 'Cambiar tema');
            btn.innerHTML = `
                <i class="fas fa-sun icon-sun"></i>
                <i class="fas fa-moon icon-moon"></i>
            `;
            btn.addEventListener('click', function () {
                const current = document.documentElement.getAttribute('data-theme') || 'dark';
                applyTheme(current === 'dark' ? 'light' : 'dark');
            });
            // Insert before the first child
            container.insertBefore(btn, container.firstChild);
        });
    }

  /* ─────────────────────────────────────────
       CHATBOT BUBBLE 
    ───────────────────────────────────────── */
    function injectChatbot() {
        if (document.getElementById('chatbot-wrapper')) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'chatbot-wrapper';
        wrapper.id = 'chatbot-wrapper';

        wrapper.innerHTML = `
            <div class="chatbot-window" id="chatbot-window">
                <div class="chatbot-header">
                    <div class="chatbot-avatar">🤖</div>
                    <div class="chatbot-header-info">
                        <h4>Wawa AI</h4>
                        <span>En línea</span>
                    </div>
                </div>
                <div class="chatbot-messages" id="chatbot-messages">
                    <div class="chat-bubble bot">
                        ¡Hola! Soy <strong>Wawa AI</strong>, tu asistente de estudio 👋<br>
                        Estoy conectado al motor de Inteligencia Artificial de Ninelives.
                    </div>
                    <div class="chat-bubble bot">
                        ¿En qué materia estás studying hoy? 📚
                    </div>
                </div>
                <div class="chatbot-input-area">
                    <textarea
                        class="chatbot-input"
                        id="chatbot-input"
                        placeholder="Escribe tu mensaje…"
                        rows="1"
                        maxlength="500"
                    ></textarea>
                    <button class="chatbot-send" id="chatbot-send" title="Enviar">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
                <p class="chatbot-footer-note">Asistente en desarrollo — Study Wawa</p>
            </div>

            <button class="chatbot-btn" id="chatbot-btn" aria-label="Abrir chat">
                <i class="fas fa-comment-dots cb-icon-chat"></i>
                <i class="fas fa-times cb-icon-close"></i>
                <span class="chatbot-unread" id="chatbot-unread">1</span>
            </button>
        `;

        document.body.appendChild(wrapper);

        const btn    = document.getElementById('chatbot-btn');
        const win    = document.getElementById('chatbot-window');
        const input  = document.getElementById('chatbot-input');
        const send   = document.getElementById('chatbot-send');
        const msgs   = document.getElementById('chatbot-messages');
        const unread = document.getElementById('chatbot-unread');

        let isOpen = false;

        function toggleChat() {
            isOpen = !isOpen;
            btn.classList.toggle('open', isOpen);
            win.classList.toggle('open', isOpen);
            if (isOpen) {
                input.focus();
                scrollToBottom();
            }
        }

        function scrollToBottom() {
            msgs.scrollTop = msgs.scrollHeight;
        }

        function addBubble(text, role) {
            const div = document.createElement('div');
            div.className = 'chat-bubble ' + role;
            div.innerHTML = text;
            msgs.appendChild(div);
            scrollToBottom();
            return div;
        }

        function showTyping() {
            const t = document.createElement('div');
            t.className = 'chat-typing';
            t.id = 'chat-typing-indicator';
            t.innerHTML = '<span></span><span></span><span></span>';
            msgs.appendChild(t);
            scrollToBottom();
            return t;
        }

        // FUNCIÓN CONECTADA AL PUENTE REAL DE NODE.JS
        function sendMessage() {
            const text = input.value.trim();
            if (!text || send.disabled) return;

            // Apuntamos al endpoint de nuestro puente de Node (Puerto 3000)
            const NODE_CHAT_API = 'http://127.0.0.1:3000/api/chat';

            addBubble(text, 'user');
            input.value = '';
            input.style.height = 'auto';

            // Bloqueamos la entrada de texto y el botón temporalmente
            input.disabled = true;
            send.disabled = true;

            // Mostramos tus tres puntitos de carga animados
            const typing = showTyping();

            // Realizamos la petición HTTP POST asincrónica hacia Node.js
            fetch(NODE_CHAT_API, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: text })
            })
            .then(response => {
                if (!response.ok) throw new Error('Error en el servidor central');
                return response.json();
            })
            .then(data => {
                typing.remove(); // Quitamos los puntitos de carga

                if (data.success) {
                    // Mostramos la respuesta de la IA generada desde Python
                    addBubble(data.reply, 'bot');
                } else {
                    addBubble('Hubo un problema al procesar la respuesta de la IA. 🐾', 'bot');
                }
            })
            .catch(error => {
                console.error('Error de conexión:', error);
                typing.remove();
                addBubble('❌ No se pudo conectar con el servidor. Asegurate de tener encendidos los backend de Node y Python. 🐾', 'bot');
            })
            .finally(() => {
                // Desbloqueamos los controles para que el alumno pueda volver a preguntar
                input.disabled = false;
                send.disabled = false;
                input.focus();
                scrollToBottom();
            });
        }

        btn.addEventListener('click', toggleChat);

        send.addEventListener('click', sendMessage);

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Auto-resize textarea
        input.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        });

        // Close on outside click
        document.addEventListener('click', function (e) {
            if (isOpen && !wrapper.contains(e.target)) {
                toggleChat();
            }
        });

        // Dismiss unread dot on first open
        btn.addEventListener('click', function () {
            if (unread) unread.style.display = 'none';
        }, { once: true });
    }

    /* ─────────────────────────────────────────
       INIT
    ───────────────────────────────────────── */
    function init() {
        applyTheme(getTheme());
        injectThemeToggle();
        injectChatbot();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
