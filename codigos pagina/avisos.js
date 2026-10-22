/* ═══════════════════════════════════════════════════════════════
   NINE LIVES EDU — AVISOS DEL SISTEMA
   Reemplaza a alert() y confirm() del navegador por avisos propios,
   con el estilo del sitio. No depende de nada más (inyecta su CSS).

   Uso:
     Aviso.exito('¡Post publicado!');
     Aviso.error('No se pudo enviar la respuesta.');
     Aviso.advertencia('Completá todos los campos.');
     Aviso.info('Abriremos un chat seguro con tu tutor.');

     // Aviso que NO desaparece solo (para datos que hay que anotar, ej. PIN)
     await Aviso.fijo('PIN del alumno', 'Anotalo ahora.', { codigo: '123456' });

     // Confirmación (reemplaza a confirm())
     if (!(await Aviso.confirmar('¿Eliminar esta cuenta?', { peligro: true }))) return;
═══════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    if (window.Aviso) return; // ya cargado

    var MAX_VISIBLES = 4;
    var DURACION = { exito: 4000, info: 4500, advertencia: 6000, error: 7000 };
    var ICONOS = { exito: '✓', error: '✕', advertencia: '!', info: 'i' };
    var TITULOS = { exito: 'Listo', error: 'Error', advertencia: 'Atención', info: 'Aviso' };

    var contenedor = null;

    /* ── CSS ─────────────────────────────────────────────── */
    function inyectarEstilos() {
        if (document.getElementById('avisos-estilos')) return;
        var css = `
        #avisos-contenedor {
            position: fixed; top: calc(1rem + env(safe-area-inset-top, 0px)); right: 1rem;
            width: min(380px, calc(100vw - 2rem));
            display: flex; flex-direction: column; gap: .6rem;
            z-index: 10000; pointer-events: none;
        }
        .aviso {
            --aviso-color: var(--violet-soft, #A78BFA);
            pointer-events: auto; position: relative; overflow: hidden;
            display: flex; align-items: flex-start; gap: .75rem;
            background: var(--ink-panel, #17132B); color: var(--parchment, #F1F0FF);
            border: 1px solid var(--line-strong, rgba(241,240,255,.24));
            border-left: 3px solid var(--aviso-color);
            border-radius: var(--radius-md, 3px);
            padding: .8rem .9rem .8rem .8rem;
            box-shadow: 0 8px 24px rgba(0,0,0,.45);
            font-family: var(--font-body, 'Inter', system-ui, sans-serif);
            font-size: .9rem; line-height: 1.4;
            opacity: 0; transform: translateX(24px);
            transition: opacity .25s ease, transform .25s ease;
        }
        .aviso.visible { opacity: 1; transform: translateX(0); }
        .aviso.saliendo { opacity: 0; transform: translateX(24px); }
        .aviso--exito       { --aviso-color: var(--success, #34D399); }
        .aviso--error       { --aviso-color: var(--danger, #F87171); }
        .aviso--advertencia { --aviso-color: var(--warning, #F0A833); }
        .aviso--info        { --aviso-color: var(--violet-soft, #A78BFA); }
        .aviso__icono {
            flex: 0 0 auto; width: 1.4rem; height: 1.4rem; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            background: var(--aviso-color); color: #0D0B18;
            font-weight: 700; font-size: .8rem; margin-top: .05rem;
        }
        .aviso__cuerpo { flex: 1 1 auto; min-width: 0; }
        .aviso__titulo { font-weight: 600; font-size: .78rem; letter-spacing: .04em;
            text-transform: uppercase; color: var(--aviso-color); margin-bottom: .1rem; }
        .aviso__texto { overflow-wrap: anywhere; white-space: pre-wrap; }
        .aviso__cerrar {
            flex: 0 0 auto; background: none; border: 0; cursor: pointer;
            color: var(--muted, #9D98C4); font-size: 1.1rem; line-height: 1;
            padding: .1rem .3rem; border-radius: 3px;
        }
        .aviso__cerrar:hover { color: var(--parchment, #F1F0FF); }
        .aviso__barra {
            position: absolute; left: 0; bottom: 0; height: 2px; width: 100%;
            background: var(--aviso-color); opacity: .7;
            transform-origin: left; animation: aviso-barra linear forwards;
        }
        .aviso:hover .aviso__barra, .aviso:focus-within .aviso__barra { animation-play-state: paused; }
        @keyframes aviso-barra { from { transform: scaleX(1); } to { transform: scaleX(0); } }

        .aviso-modal-fondo {
            position: fixed; inset: 0; z-index: 10001;
            background: rgba(5,4,12,.72);
            display: flex; align-items: center; justify-content: center; padding: 1rem;
            opacity: 0; transition: opacity .2s ease;
        }
        .aviso-modal-fondo.visible { opacity: 1; }
        .aviso-modal {
            --aviso-color: var(--violet-soft, #A78BFA);
            width: min(420px, 100%);
            background: var(--ink-panel, #17132B); color: var(--parchment, #F1F0FF);
            border: 1px solid var(--line-strong, rgba(241,240,255,.24));
            border-top: 3px solid var(--aviso-color);
            border-radius: var(--radius-lg, 4px);
            padding: 1.4rem 1.4rem 1.2rem;
            box-shadow: 0 16px 48px rgba(0,0,0,.6);
            font-family: var(--font-body, 'Inter', system-ui, sans-serif);
            transform: translateY(12px); transition: transform .2s ease;
        }
        .aviso-modal-fondo.visible .aviso-modal { transform: translateY(0); }
        .aviso-modal--peligro { --aviso-color: var(--danger, #F87171); }
        .aviso-modal__titulo { margin: 0 0 .6rem; font-size: 1.15rem; font-weight: 600;
            font-family: var(--font-display, Georgia, serif); }
        .aviso-modal__texto { margin: 0; font-size: .92rem; line-height: 1.5;
            color: var(--parchment, #F1F0FF); white-space: pre-wrap; overflow-wrap: anywhere; }
        .aviso-modal__codigo {
            margin: 1rem 0 .2rem; padding: .8rem; text-align: center;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 2rem; font-weight: 700; letter-spacing: .35em; text-indent: .35em;
            background: var(--ink, #0D0B18); border: 1px dashed var(--aviso-color);
            border-radius: var(--radius-md, 3px); user-select: all;
        }
        .aviso-modal__nota { margin: .5rem 0 0; font-size: .8rem; color: var(--muted, #9D98C4); }
        .aviso-modal__acciones { display: flex; justify-content: flex-end; flex-wrap: wrap;
            gap: .6rem; margin-top: 1.2rem; }
        .aviso-btn {
            cursor: pointer; font: inherit; font-size: .9rem; font-weight: 600;
            padding: .55rem 1.1rem; border-radius: var(--radius-md, 3px);
            border: 1px solid var(--line-strong, rgba(241,240,255,.24));
            background: transparent; color: var(--parchment, #F1F0FF);
        }
        .aviso-btn:hover { background: var(--ink-panel-2, #201A3B); }
        .aviso-btn--principal { background: var(--violet, #8B5CF6); border-color: var(--violet, #8B5CF6); color: #fff; }
        .aviso-btn--principal:hover { background: var(--violet-deep, #6D28D9); }
        .aviso-btn--peligro { background: var(--danger, #F87171); border-color: var(--danger, #F87171); color: #0D0B18; }
        .aviso-btn--peligro:hover { filter: brightness(.9); background: var(--danger, #F87171); }
        .aviso-btn:focus-visible, .aviso__cerrar:focus-visible {
            outline: 2px solid var(--violet-soft, #A78BFA); outline-offset: 2px; }

        @media (max-width: 520px) {
            #avisos-contenedor { top: auto; bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
                right: 1rem; left: 1rem; width: auto; }
            .aviso { transform: translateY(24px); }
            .aviso.visible { transform: translateY(0); }
            .aviso.saliendo { transform: translateY(24px); }
        }
        @media (prefers-reduced-motion: reduce) {
            .aviso, .aviso-modal-fondo, .aviso-modal { transition: none; transform: none; }
            .aviso__barra { animation: none; display: none; }
        }`;
        var st = document.createElement('style');
        st.id = 'avisos-estilos';
        st.textContent = css;
        document.head.appendChild(st);
    }

    function asegurarContenedor() {
        inyectarEstilos();
        if (contenedor && document.body.contains(contenedor)) return contenedor;
        contenedor = document.createElement('div');
        contenedor.id = 'avisos-contenedor';
        contenedor.setAttribute('aria-live', 'polite');
        contenedor.setAttribute('aria-atomic', 'false');
        document.body.appendChild(contenedor);
        return contenedor;
    }

    function texto(valor) {
        return valor === null || valor === undefined ? '' : String(valor);
    }

    /* ── Toasts ──────────────────────────────────────────── */
    function cerrarToast(el) {
        if (!el || el.dataset.cerrando) return;
        el.dataset.cerrando = '1';
        clearTimeout(el._timer);
        el.classList.remove('visible');
        el.classList.add('saliendo');
        setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 260);
    }

    function mostrar(mensaje, tipo, opciones) {
        opciones = opciones || {};
        if (!ICONOS[tipo]) tipo = 'info';
        var msg = texto(mensaje);
        var cont = asegurarContenedor();

        // Mismo aviso repetido (ej. clics seguidos): no lo apilamos, lo reiniciamos
        var existentes = cont.querySelectorAll('.aviso');
        for (var i = 0; i < existentes.length; i++) {
            var e = existentes[i];
            if (!e.dataset.cerrando && e.dataset.tipo === tipo && e.dataset.msg === msg) {
                cerrarToast(e);
            }
        }
        // Tope de avisos en pantalla: se va el más viejo
        var vivos = cont.querySelectorAll('.aviso:not([data-cerrando])');
        for (var j = 0; j <= vivos.length - MAX_VISIBLES; j++) cerrarToast(vivos[j]);

        var duracion = opciones.duracion || DURACION[tipo];

        var el = document.createElement('div');
        el.className = 'aviso aviso--' + tipo;
        el.dataset.tipo = tipo;
        el.dataset.msg = msg;
        el.setAttribute('role', tipo === 'error' || tipo === 'advertencia' ? 'alert' : 'status');

        var icono = document.createElement('span');
        icono.className = 'aviso__icono';
        icono.setAttribute('aria-hidden', 'true');
        icono.textContent = ICONOS[tipo];

        var cuerpo = document.createElement('div');
        cuerpo.className = 'aviso__cuerpo';
        var tit = document.createElement('div');
        tit.className = 'aviso__titulo';
        tit.textContent = opciones.titulo || TITULOS[tipo];
        var txt = document.createElement('div');
        txt.className = 'aviso__texto';
        txt.textContent = msg;
        cuerpo.appendChild(tit);
        cuerpo.appendChild(txt);

        var cerrar = document.createElement('button');
        cerrar.type = 'button';
        cerrar.className = 'aviso__cerrar';
        cerrar.setAttribute('aria-label', 'Cerrar aviso');
        cerrar.textContent = '×';
        cerrar.addEventListener('click', function () { cerrarToast(el); });

        var barra = document.createElement('div');
        barra.className = 'aviso__barra';
        barra.style.animationDuration = duracion + 'ms';

        el.appendChild(icono);
        el.appendChild(cuerpo);
        el.appendChild(cerrar);
        el.appendChild(barra);
        cont.appendChild(el);

        // la barra termina => se cierra (y se pausa con hover/foco, igual que la animación)
        barra.addEventListener('animationend', function () { cerrarToast(el); });

        requestAnimationFrame(function () {
            requestAnimationFrame(function () { el.classList.add('visible'); });
        });

        // Con "reducir movimiento" la barra no anima: usamos un timer común
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            el._timer = setTimeout(function () { cerrarToast(el); }, duracion);
        }
        return el;
    }

    /* ── Modales (fijo / confirmar) ──────────────────────── */
    function copiarAlPortapapeles(valor) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            return navigator.clipboard.writeText(valor);
        }
        return new Promise(function (resolve, reject) {
            try {
                var ta = document.createElement('textarea');
                ta.value = valor;
                ta.setAttribute('readonly', '');
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.select();
                var ok = document.execCommand('copy');
                document.body.removeChild(ta);
                ok ? resolve() : reject(new Error('copy'));
            } catch (err) { reject(err); }
        });
    }

    function crearModal(cfg) {
        inyectarEstilos();
        return new Promise(function (resolve) {
            var previo = document.activeElement;
            var idBase = 'aviso-modal-' + Date.now() + '-' + Math.floor(Math.random() * 1000);

            var fondo = document.createElement('div');
            fondo.className = 'aviso-modal-fondo';

            var caja = document.createElement('div');
            caja.className = 'aviso-modal' + (cfg.peligro ? ' aviso-modal--peligro' : '');
            caja.setAttribute('role', cfg.confirmar ? 'alertdialog' : 'dialog');
            caja.setAttribute('aria-modal', 'true');
            caja.setAttribute('aria-labelledby', idBase + '-t');
            caja.setAttribute('aria-describedby', idBase + '-d');

            var h = document.createElement('h2');
            h.className = 'aviso-modal__titulo';
            h.id = idBase + '-t';
            h.textContent = cfg.titulo;
            caja.appendChild(h);

            var p = document.createElement('p');
            p.className = 'aviso-modal__texto';
            p.id = idBase + '-d';
            p.textContent = cfg.mensaje;
            caja.appendChild(p);

            var botonCopiar = null;
            if (cfg.codigo) {
                var cod = document.createElement('div');
                cod.className = 'aviso-modal__codigo';
                cod.textContent = cfg.codigo;
                caja.appendChild(cod);
                if (cfg.nota) {
                    var nota = document.createElement('p');
                    nota.className = 'aviso-modal__nota';
                    nota.textContent = cfg.nota;
                    caja.appendChild(nota);
                }
                botonCopiar = document.createElement('button');
                botonCopiar.type = 'button';
                botonCopiar.className = 'aviso-btn';
                botonCopiar.textContent = 'Copiar';
                botonCopiar.addEventListener('click', function () {
                    copiarAlPortapapeles(cfg.codigo).then(function () {
                        botonCopiar.textContent = '¡Copiado!';
                        setTimeout(function () { botonCopiar.textContent = 'Copiar'; }, 1600);
                    }, function () {
                        botonCopiar.textContent = 'Seleccionalo y copialo';
                    });
                });
            }

            var acciones = document.createElement('div');
            acciones.className = 'aviso-modal__acciones';

            var botonCancelar = null;
            if (cfg.confirmar) {
                botonCancelar = document.createElement('button');
                botonCancelar.type = 'button';
                botonCancelar.className = 'aviso-btn';
                botonCancelar.textContent = cfg.textoCancelar;
                acciones.appendChild(botonCancelar);
            }
            if (botonCopiar) acciones.appendChild(botonCopiar);

            var botonOk = document.createElement('button');
            botonOk.type = 'button';
            botonOk.className = 'aviso-btn ' + (cfg.peligro ? 'aviso-btn--peligro' : 'aviso-btn--principal');
            botonOk.textContent = cfg.textoOk;
            acciones.appendChild(botonOk);

            caja.appendChild(acciones);
            fondo.appendChild(caja);
            document.body.appendChild(fondo);

            var cerrado = false;
            function cerrar(resultado) {
                if (cerrado) return;
                cerrado = true;
                fondo.classList.remove('visible');
                setTimeout(function () { if (fondo.parentNode) fondo.parentNode.removeChild(fondo); }, 220);
                if (previo && previo.focus) { try { previo.focus(); } catch (e) { /* nada */ } }
                resolve(resultado);
            }

            botonOk.addEventListener('click', function () { cerrar(true); });
            if (botonCancelar) botonCancelar.addEventListener('click', function () { cerrar(false); });

            // En confirmaciones, tocar el fondo cancela. En avisos fijos NO: no queremos
            // que se pierda un PIN por un toque accidental.
            fondo.addEventListener('mousedown', function (ev) {
                if (cfg.confirmar && ev.target === fondo) cerrar(false);
            });

            fondo.addEventListener('keydown', function (ev) {
                if (ev.key === 'Escape') { ev.stopPropagation(); cerrar(cfg.confirmar ? false : true); return; }
                if (ev.key === 'Tab') {
                    var foco = Array.prototype.slice.call(caja.querySelectorAll('button'));
                    if (!foco.length) return;
                    var primero = foco[0], ultimo = foco[foco.length - 1];
                    if (ev.shiftKey && document.activeElement === primero) { ev.preventDefault(); ultimo.focus(); }
                    else if (!ev.shiftKey && document.activeElement === ultimo) { ev.preventDefault(); primero.focus(); }
                }
            });

            requestAnimationFrame(function () {
                fondo.classList.add('visible');
                // En acciones destructivas el foco arranca en "Cancelar" para evitar un Enter accidental
                (cfg.peligro && botonCancelar ? botonCancelar : botonOk).focus();
            });
        });
    }

    function fijo(titulo, mensaje, opciones) {
        opciones = opciones || {};
        return crearModal({
            titulo: texto(titulo) || 'Aviso',
            mensaje: texto(mensaje),
            codigo: opciones.codigo ? texto(opciones.codigo) : null,
            nota: opciones.nota || null,
            textoOk: opciones.textoCerrar || 'Entendido',
            peligro: false,
            confirmar: false,
        });
    }

    function confirmar(mensaje, opciones) {
        opciones = opciones || {};
        return crearModal({
            titulo: opciones.titulo || (opciones.peligro ? 'Confirmar acción' : 'Confirmar'),
            mensaje: texto(mensaje),
            codigo: null,
            textoOk: opciones.textoOk || 'Aceptar',
            textoCancelar: opciones.textoCancelar || 'Cancelar',
            peligro: !!opciones.peligro,
            confirmar: true,
        });
    }

    window.Aviso = {
        mostrar: mostrar,
        exito: function (m, o) { return mostrar(m, 'exito', o); },
        error: function (m, o) { return mostrar(m, 'error', o); },
        advertencia: function (m, o) { return mostrar(m, 'advertencia', o); },
        info: function (m, o) { return mostrar(m, 'info', o); },
        fijo: fijo,
        confirmar: confirmar,
    };
})();
