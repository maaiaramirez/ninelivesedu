/* ═══════════════════════════════════════════════════════
   ATLAS NOCTURNO — comportamiento del tema
   Discreto: no reemplaza cursores, no inyecta criaturas.
   Un solo gesto con propósito: la constelación del hero.
═══════════════════════════════════════════════════════ */
(function () {
    'use strict';

    /* ── 1. Fondo global fijo (estrellas + halo cálido) ── */
    function injectGlobalBackground() {
        const bg = document.createElement('div');
        bg.id = 'atlas-bg';
        document.body.prepend(bg);
    }

    /* ── 2. Constelación animada en el hero ────────────── */
    function injectHeroScene() {
        const visual = document.querySelector('.hero-visual');
        if (!visual) return;

        const svgNS = 'http://www.w3.org/2000/svg';
        const svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('id', 'atlas-scene');
        svg.setAttribute('viewBox', '0 0 420 420');
        svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

        // Nodos distribuidos con intención: forman una red, no ruido aleatorio
        const nodes = [
            { x: 60, y: 70 }, { x: 160, y: 40 }, { x: 260, y: 90 },
            { x: 340, y: 50 }, { x: 40, y: 200 }, { x: 190, y: 170 },
            { x: 310, y: 220 }, { x: 90, y: 320 }, { x: 220, y: 300 },
            { x: 350, y: 340 }, { x: 150, y: 380 },
        ];
        const edges = [
            [0, 1], [1, 2], [2, 3], [0, 4], [1, 5], [2, 5], [3, 6],
            [4, 5], [5, 6], [4, 7], [5, 8], [6, 9], [7, 8], [8, 9], [8, 10], [7, 10],
        ];

        let svgContent = '';
        edges.forEach(([a, b], i) => {
            const n1 = nodes[a], n2 = nodes[b];
            svgContent += `<line class="atlas-line" x1="${n1.x}" y1="${n1.y}" x2="${n2.x}" y2="${n2.y}" style="animation-delay:${(i * 0.06).toFixed(2)}s"/>`;
        });
        nodes.forEach((n, i) => {
            const r = i % 3 === 0 ? 3.5 : 2.2;
            svgContent += `<circle class="atlas-node" cx="${n.x}" cy="${n.y}" r="${r}" style="animation-delay:${(0.8 + i * 0.08).toFixed(2)}s, ${(1.5 + i * 0.15).toFixed(2)}s"/>`;
        });

        svg.innerHTML = svgContent;
        visual.prepend(svg);
    }

    /* ── 3. Scroll reveal (fade + rise real) ───────────── */
    function initScrollReveal() {
        const targets = document.querySelectorAll('.reveal');
        if (!targets.length) return;

        if (!('IntersectionObserver' in window)) {
            targets.forEach(t => t.classList.add('in-view'));
            return;
        }
        const io = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in-view');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15 });
        targets.forEach(t => io.observe(t));
    }

    /* ── 4. Contadores con easing suave (no a saltos) ──── */
    function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

    function animateCounters() {
        const values = document.querySelectorAll('.metric-value');
        if (!values.length || !('IntersectionObserver' in window)) return;

        const io = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                const el = entry.target;
                io.unobserve(el);

                const raw = el.textContent.trim();
                const match = raw.match(/^([\d.,]+)(.*)$/);
                if (!match) return;

                const numeric = parseFloat(match[1].replace(',', '.'));
                const suffix = match[2] || '';
                if (isNaN(numeric)) return;
                const isDecimal = match[1].includes('.') || match[1].includes(',');

                const duration = 1100;
                const start = performance.now();

                function tick(now) {
                    const progress = Math.min((now - start) / duration, 1);
                    const eased = easeOutCubic(progress);
                    const current = numeric * eased;
                    el.textContent = (isDecimal ? current.toFixed(1) : Math.round(current)) + suffix;
                    if (progress < 1) {
                        requestAnimationFrame(tick);
                    } else {
                        el.textContent = raw;
                    }
                }
                requestAnimationFrame(tick);
            });
        }, { threshold: 0.4 });

        values.forEach(v => io.observe(v));
    }

    /* ── 5. Postularse como tutor (con subida de título) ─ */
    function initTutorApplication() {
        const btns = document.querySelectorAll('.btn-tutor');
        if (!btns.length) return;

        btns.forEach(oldBtn => {
            // Si la página ya tenía un listener viejo pegado a este botón
            // (ej. el modal de mentira de index.html), lo saco clonando el
            // nodo, y engancho acá el flujo real.
            const btn = oldBtn.cloneNode(true);
            oldBtn.replaceWith(btn);
            btn.addEventListener('click', openTutorModal);
        });
    }

    function openTutorModal() {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="modal-card">
                <button class="modal-close" type="button">&times;</button>
                <div class="modal-header-simple">
                    <h2>Unirse como tutor</h2>
                    <p>Subí tu título o certificación — un moderador la revisa antes de activar tu perfil.</p>
                </div>
                <form class="modal-form" id="tutorApplyForm">
                    <input type="text" id="taName" placeholder="Nombre completo" required>
                    <input type="email" id="taEmail" placeholder="Correo electrónico" required>
                    <select id="taMateria" required>
                        <option value="">Especialidad principal</option>
                        <option>Matemáticas</option><option>Física</option>
                        <option>Química</option><option>Biología</option>
                        <option>Historia</option><option>Literatura</option>
                        <option>Inglés</option><option>Filosofía</option>
                    </select>
                    <label style="font-size:0.85rem; color:var(--muted, #999); text-align:left;">
                        Título o certificación (PDF, Word o imagen — máx. 8 MB)
                        <input type="file" id="taFile" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" required
                               style="display:block; margin-top:0.4rem; width:100%; color:inherit;">
                    </label>
                    <button type="submit" class="secondary" id="taSubmit">Enviar solicitud</button>
                    <small id="taMsg" class="form-error is-hidden"></small>
                </form>
            </div>`;
        document.body.appendChild(overlay);
        requestAnimationFrame(() => overlay.classList.add('is-visible'));

        const close = () => {
            overlay.classList.remove('is-visible');
            setTimeout(() => overlay.remove(), 400);
        };
        overlay.querySelector('.modal-close').addEventListener('click', close);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

        const form = overlay.querySelector('#tutorApplyForm');
        const msg = overlay.querySelector('#taMsg');
        const submitBtn = overlay.querySelector('#taSubmit');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            msg.classList.add('is-hidden');

            const fileInput = overlay.querySelector('#taFile');
            const file = fileInput.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('nombreCompleto', overlay.querySelector('#taName').value.trim());
            formData.append('email', overlay.querySelector('#taEmail').value.trim());
            formData.append('materia', overlay.querySelector('#taMateria').value);
            formData.append('titulo', file);

            submitBtn.disabled = true;
            submitBtn.textContent = 'Enviando…';

            try {
                const res = await fetch('/api/tutores/postularse', { method: 'POST', body: formData });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) throw new Error(data.detail || 'No se pudo enviar la solicitud.');

                form.innerHTML = `<p style="color:#8fd18f; text-align:center; padding:1rem 0;">${data.message}</p>`;
                setTimeout(close, 3200);
            } catch (err) {
                msg.textContent = err.message;
                msg.classList.remove('is-hidden');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Enviar solicitud';
            }
        });
    }

    /* ── INIT ───────────────────────────────────────────── */
    function init() {
        injectGlobalBackground();
        injectHeroScene();
        initScrollReveal();
        animateCounters();
        initTutorApplication();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
