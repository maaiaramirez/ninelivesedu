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

    /* ── INIT ───────────────────────────────────────────── */
    function init() {
        injectGlobalBackground();
        injectHeroScene();
        initScrollReveal();
        animateCounters();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
