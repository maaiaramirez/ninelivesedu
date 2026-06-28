// JavaScript para funcionalidades interactivas
document.addEventListener('DOMContentLoaded', function() {
    
    // Smooth scrolling para enlaces de navegación
    const navLinks = document.querySelectorAll('.nav-link[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Efecto de scroll en el header
    window.addEventListener('scroll', function() {
        const header = document.querySelector('.header');
        if (window.scrollY > 100) {
            header.style.background = 'rgba(255, 255, 255, 0.98)';
            header.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
        } else {
            header.style.background = 'rgba(255, 255, 255, 0.95)';
            header.style.boxShadow = 'none';
        }
    });

    // Estado de sesión (solo frontend)
    const SESSION_KEY = 'sw_session';
    const USERS_KEY = 'sw_users';

    // Animaciones de entrada para las tarjetas
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Aplicar animaciones a las tarjetas
    const cards = document.querySelectorAll('.benefit-card, .testimonial-card');
    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition =
            'opacity 0.75s cubic-bezier(0.22, 1, 0.36, 1), transform 0.75s cubic-bezier(0.16, 1, 0.3, 1)';
        observer.observe(card);
    });

    // Funcionalidad de los botones principales
    const btnBuscarApuntes = document.querySelector('.btn-primary');
    const btnOfrecerTutorias = document.querySelector('.btn-secondary');
    const btnRegistro = document.querySelector('.btn-login');
    const btnTutor = document.querySelector('.btn-tutor');
    const btnCta = document.querySelector('.btn-cta');

    if (btnBuscarApuntes) {
        btnBuscarApuntes.addEventListener('click', function() {
            window.location.href = 'apuntes.html';
        });
    }

    if (btnOfrecerTutorias) {
        btnOfrecerTutorias.addEventListener('click', function() {
            window.location.href = 'tutores.html';
        });
    }

    if (btnRegistro) {
        btnRegistro.addEventListener('click', function() {
            if (getSession()) {
                logout();
            } else {
                showModal('login');
            }
        });
    }

    if (btnTutor) {
        btnTutor.addEventListener('click', function() {
            showModal(getSession() ? 'login' : 'tutor');
        });
    }

    if (btnCta) {
        btnCta.addEventListener('click', function() {
            showModal('register');
        });
    }

    // Función para mostrar modales
    function showModal(type) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay is-visible';

        const modal = document.createElement('div');
        modal.className = 'modal-card';

        modal.innerHTML = getModalTemplate(type);

        const closeBtn = document.createElement('button');
        closeBtn.className = 'modal-close';
        closeBtn.innerHTML = '&times;';
        modal.appendChild(closeBtn);

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        function closeModal() {
            overlay.classList.remove('is-visible');
            overlay.remove();
        }

        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) {
                closeModal();
            }
        });

        wireAuthForms(modal, closeModal);
    }

    function getModalTemplate(type) {
        if (type === 'login') {
            return `
                <div class="modal-header-simple">
                    <h2>Iniciar Sesión</h2>
                    <p>Accede a tu panel personalizado y continúa donde te quedaste.</p>
                </div>
                <form class="modal-form" id="loginForm">
                    <input type="email" id="loginEmail" placeholder="Correo electrónico" required>
                    <input type="password" id="loginPassword" placeholder="Contraseña" required>
                    <button type="submit" class="primary">Ingresar</button>
                    <small>¿No tienes cuenta? <a href="#" class="link-highlight" data-open="register">Regístrate aquí</a></small>
                    <small id="loginError" class="form-error is-hidden"></small>
                </form>
            `;
        }

        if (type === 'register') {
            return `
                <div class="modal-header-simple">
                    <h2>Crear cuenta</h2>
                    <p>Personaliza tus materias favoritas y guarda tus apuntes en la nube.</p>
                </div>
                <form class="modal-form" id="registerForm">
                    <input type="text" id="registerName" placeholder="Nombre completo" required>
                    <input type="email" id="registerEmail" placeholder="Correo electrónico" required>
                    <input type="password" id="registerPassword" placeholder="Contraseña" required>
                    <button type="submit" class="primary">Registrarme</button>
                    <small>¿Ya tienes cuenta? <a href="#" class="link-highlight" data-open="login">Inicia sesión</a></small>
                    <small id="registerError" class="form-error is-hidden"></small>
                </form>
            `;
        }

        return `
            <div class="modal-header-simple">
                <h2>Unirse como Tutor</h2>
                <p>Completa el formulario y nuestro equipo validará tu perfil en menos de 24h.</p>
            </div>
            <form class="modal-form">
                <input type="text" placeholder="Nombre completo" required>
                <input type="email" placeholder="Correo profesional" required>
                <select required>
                    <option value="">Especialidad principal</option>
                    <option>Matemáticas</option>
                    <option>Física</option>
                    <option>Química</option>
                    <option>Biología</option>
                    <option>Historia</option>
                    <option>Literatura</option>
                    <option>Inglés</option>
                </select>
                <button type="submit" class="secondary">Enviar solicitud</button>
                <small>Al continuar aceptas nuestro código de conducta para tutores.</small>
            </form>
        `;
    }

    function wireAuthForms(modal, closeModal) {
        const goToLinks = modal.querySelectorAll('[data-open]');
        goToLinks.forEach((link) => {
            link.addEventListener('click', (event) => {
                event.preventDefault();
                closeModal();
                showModal(link.dataset.open);
            });
        });

        const loginForm = modal.querySelector('#loginForm');
        const registerForm = modal.querySelector('#registerForm');

        if (loginForm) {
            loginForm.addEventListener('submit', (event) => {
                event.preventDefault();
                const email = modal.querySelector('#loginEmail')?.value?.trim().toLowerCase();
                const password = modal.querySelector('#loginPassword')?.value;
                const errorEl = modal.querySelector('#loginError');

                if (!email || !password) {
                    showError(errorEl, 'Completa tus datos.');
                    return;
                }

                const users = getUsers();
                const user = users.find((u) => u.email === email && u.password === password);

                if (!user) {
                    showError(errorEl, 'Credenciales inválidas.');
                    return;
                }

                setSession({ name: user.name, email: user.email });
                updateHeaderSession();
                closeModal();
                alert(`¡Bienvenido, ${user.name}!`);
            });
        }

        if (registerForm) {
            registerForm.addEventListener('submit', (event) => {
                event.preventDefault();
                const name = modal.querySelector('#registerName')?.value?.trim();
                const email = modal.querySelector('#registerEmail')?.value?.trim().toLowerCase();
                const password = modal.querySelector('#registerPassword')?.value;
                const errorEl = modal.querySelector('#registerError');

                if (!name || !email || !password) {
                    showError(errorEl, 'Completa todos los campos.');
                    return;
                }

                const users = getUsers();
                if (users.some((u) => u.email === email)) {
                    showError(errorEl, 'Ese correo ya está registrado.');
                    return;
                }

                users.push({ name, email, password });
                saveUsers(users);
                setSession({ name, email });
                updateHeaderSession();
                closeModal();
                alert(`Cuenta creada. ¡Hola, ${name}!`);
            });
        }
    }

    function showError(el, message) {
        if (!el) return;
        el.textContent = message;
        el.classList.remove('is-hidden');
    }

    function getUsers() {
        try {
            return JSON.parse(localStorage.getItem(USERS_KEY)) || [];
        } catch (error) {
            return [];
        }
    }

    function saveUsers(users) {
        localStorage.setItem(USERS_KEY, JSON.stringify(users));
    }

    function setSession(session) {
        localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    }

    function getSession() {
        try {
            return JSON.parse(localStorage.getItem(SESSION_KEY));
        } catch (error) {
            return null;
        }
    }

    function logout() {
        localStorage.removeItem(SESSION_KEY);
        updateHeaderSession();
        alert('Sesión cerrada.');
    }

    function updateHeaderSession() {
        const session = getSession();
        const loginBtn = document.querySelector('.btn-login');
        const tutorBtn = document.querySelector('.btn-tutor');

        if (session) {
            if (loginBtn) {
                loginBtn.textContent = 'Cerrar sesión';
            }
            if (tutorBtn) {
                tutorBtn.textContent = `Hola, ${session.name}`;
            }
        } else {
            if (loginBtn) {
                loginBtn.textContent = 'Registro/Iniciar Sesión';
            }
            if (tutorBtn) {
                tutorBtn.textContent = 'Unirse como tutor';
            }
        }
    }

    updateHeaderSession();

    // Efecto parallax suave en el hero
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const hero = document.querySelector('.hero');
        if (hero) {
            hero.style.transform = `translateY(${scrolled * 0.5}px)`;
        }
    });

    // Contador animado para estadísticas (si se agregan)
    function animateCounter(element, target) {
        let current = 0;
        const increment = target / 100;
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current);
        }, 20);
    }

    // Lazy loading para imágenes
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });

    images.forEach(img => imageObserver.observe(img));

    // Registrar service worker (PWA)
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/service-worker.js').catch((err) => {
            console.error('SW registration failed', err);
        });
    }
});
