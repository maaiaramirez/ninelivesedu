// JavaScript específico para la página de tutores conectado al backend Node.js
document.addEventListener('DOMContentLoaded', () => {
    const API_URL = '/api/tutores';
    const SWAP_URL = '/api/tutores/intercambios';
    const ATTENDANCE_API_URL = '/api/asistencia/profesores-disponibles';
    const ATTENDANCE_STREAM_URL = '/api/asistencia/stream';

    let tutoresData = [];
    let filteredTutores = [];
    let currentView = 'grid';
    const reservationModal = document.getElementById('reservationModal');
    const reservationForm = document.getElementById('reservationForm');
    const reservationTutorName = document.getElementById('reservationTutorName');
    const reservationNameInput = document.getElementById('reservaNombre');
    const reservationDateInput = document.getElementById('reservaFecha');
    const reservationTimeInput = document.getElementById('reservaHora');
    const reservationModeInput = document.getElementById('reservaModalidad');
    const reservationCancelBtn = reservationForm?.querySelector('.btn-cancel');
    const reservationCloseBtn = reservationModal?.querySelector('.close-modal');
    let activeReservationTutor = null;
    let attendanceEventSource = null;
    let attendanceFallbackTimer = null;

    initTutoresPage();

    async function initTutoresPage() {
        setupEventListeners();
        setupTeacherAttendanceRealtime();
        await loadTutores();
        setupSwapForm();
        setupReservationModal();
    }

    function setupTeacherAttendanceRealtime() {
        injectAttendancePanel();
        refreshAttendanceSnapshot();

        if (typeof EventSource === 'undefined') {
            startAttendancePolling();
            return;
        }

        attendanceEventSource = new EventSource(ATTENDANCE_STREAM_URL);
        attendanceEventSource.addEventListener('attendance', (event) => {
            try {
                const payload = JSON.parse(event.data);
                renderAttendancePanel(payload.teachers || []);
            } catch (error) {
                console.error('Error al procesar stream de asistencia:', error);
            }
        });

        attendanceEventSource.onerror = () => {
            if (attendanceEventSource) {
                attendanceEventSource.close();
                attendanceEventSource = null;
            }
            startAttendancePolling();
        };
    }

    async function refreshAttendanceSnapshot() {
        try {
            const response = await fetch(ATTENDANCE_API_URL);
            if (!response.ok) {
                throw new Error('No se pudo cargar la asistencia docente.');
            }
            const payload = await response.json();
            renderAttendancePanel(payload.teachers || []);
        } catch (error) {
            renderAttendanceError('No se pudo cargar asistencia en tiempo real.');
        }
    }

    function startAttendancePolling() {
        if (attendanceFallbackTimer) return;
        attendanceFallbackTimer = setInterval(refreshAttendanceSnapshot, 15000);
    }

    function injectAttendancePanel() {
        if (document.getElementById('teacherAttendancePanel')) {
            return;
        }

        const host = document.querySelector('.search-results') || document.querySelector('.main-content') || document.body;
        const panel = document.createElement('section');
        panel.id = 'teacherAttendancePanel';
        panel.className = 'attendance-panel';
        panel.style.margin = '1rem 0';
        panel.style.padding = '1rem';
        panel.style.borderRadius = '12px';
        panel.style.background = 'linear-gradient(135deg, #6d28d9 0%, #2563eb 100%)';
        panel.style.color = '#fff';
        panel.innerHTML = `
            <h3 style="margin:0 0 .5rem 0;">Profesores disponibles ahora</h3>
            <p id="teacherAttendanceSummary" style="margin:0 0 .75rem 0; opacity:.9;">Cargando disponibilidad...</p>
            <ul id="teacherAttendanceList" style="list-style:none; margin:0; padding:0;"></ul>
        `;

        host.prepend(panel);
    }

    function renderAttendancePanel(teachers) {
        const summaryEl = document.getElementById('teacherAttendanceSummary');
        const listEl = document.getElementById('teacherAttendanceList');
        if (!summaryEl || !listEl) return;

        summaryEl.textContent = `${teachers.length} profesor(es) disponibles para tutoría.`;
        if (teachers.length === 0) {
            listEl.innerHTML = '<li style="opacity:.9;">No hay profesores activos en este momento.</li>';
            return;
        }

        listEl.innerHTML = teachers.map((teacher) => `
            <li style="padding:.45rem 0; border-top:1px solid rgba(255,255,255,.2);">
                <strong>${teacher.fullName}</strong>
                <span style="opacity:.9;"> - Terminal: ${teacher.terminalId}</span>
            </li>
        `).join('');
    }

    function renderAttendanceError(message) {
        const summaryEl = document.getElementById('teacherAttendanceSummary');
        const listEl = document.getElementById('teacherAttendanceList');
        if (!summaryEl || !listEl) return;
        summaryEl.textContent = message;
        listEl.innerHTML = '';
    }

    async function loadTutores() {
        try {
            showStatusMessage('Cargando tutores...', 'loading');
            const response = await fetch(API_URL);
            if (!response.ok) {
                throw new Error('No se pudo cargar el catálogo de tutores.');
            }
            tutoresData = await response.json();
            filteredTutores = [...tutoresData];
            renderTutores(filteredTutores);
            updateResultsCount();
        } catch (error) {
            console.error(error);
            showStatusMessage(error.message || 'Ocurrió un error al cargar los tutores.', 'error');
        }
    }

    function setupEventListeners() {
        // Búsqueda
        const searchInput = document.getElementById('searchInput');
        const searchBtn = document.querySelector('.search-btn');
        
        if (searchInput) {
            searchInput.addEventListener('input', handleSearch);
        }
        
        if (searchBtn) {
            searchBtn.addEventListener('click', handleSearch);
        }

        // Filtros
        const nivelFilter = document.getElementById('nivelFilter');
        const materiaFilter = document.getElementById('materiaFilter');
        const precioFilter = document.getElementById('precioFilter');
        const ratingFilter = document.getElementById('ratingFilter');

        if (nivelFilter) {
            nivelFilter.addEventListener('change', applyFilters);
        }
        if (materiaFilter) {
            materiaFilter.addEventListener('change', applyFilters);
        }
        if (precioFilter) {
            precioFilter.addEventListener('change', applyFilters);
        }
        if (ratingFilter) {
            ratingFilter.addEventListener('change', applyFilters);
        }

        // Filtros adicionales
        const checkboxes = document.querySelectorAll('.availability-filter input[type="checkbox"], .language-filter input[type="checkbox"]');
        const radios = document.querySelectorAll('.experience-filter input[type="radio"]');
        
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', applyFilters);
        });
        
        radios.forEach(radio => {
            radio.addEventListener('change', applyFilters);
        });

        // Cambio de vista
        const viewBtns = document.querySelectorAll('.view-btn');
        viewBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                currentView = this.dataset.view;
                updateViewButtons();
                renderTutores(filteredTutores);
            });
        });

        // Limpiar filtros
        const btnLimpiarFiltros = document.querySelector('.btn-limpiar-filtros');
        if (btnLimpiarFiltros) {
            btnLimpiarFiltros.addEventListener('click', clearFilters);
        }

        // Modal de tutor
        setupTutorModal();
    }

    function handleSearch() {
        const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
        
        filteredTutores = tutoresData.filter(tutor => 
            tutor.nombre.toLowerCase().includes(searchTerm) ||
            tutor.materia.toLowerCase().includes(searchTerm) ||
            tutor.materias.some(materia => materia.toLowerCase().includes(searchTerm))
        );
        
        applyFilters();
    }

    function applyFilters() {
        if (!tutoresData.length) {
            return;
        }

        let filtered = [...tutoresData];

        // Filtro de búsqueda
        const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
        if (searchTerm) {
            filtered = filtered.filter(tutor => 
                tutor.nombre.toLowerCase().includes(searchTerm) ||
                tutor.materia.toLowerCase().includes(searchTerm) ||
                tutor.materias.some(materia => materia.toLowerCase().includes(searchTerm))
            );
        }

        // Filtro de nivel
        const nivelFilter = document.getElementById('nivelFilter').value;
        if (nivelFilter) {
            filtered = filtered.filter(tutor => tutor.nivel === nivelFilter);
        }

        // Filtro de materia
        const materiaFilter = document.getElementById('materiaFilter').value;
        if (materiaFilter) {
            filtered = filtered.filter(tutor => tutor.materia === materiaFilter);
        }

        // Filtro de precio
        const precioFilter = document.getElementById('precioFilter').value;
        if (precioFilter) {
            const [min, max] = precioFilter.split('-').map(p => p.replace('+', ''));
            filtered = filtered.filter(tutor => {
                if (max === undefined) {
                    return tutor.precio >= parseInt(min);
                }
                return tutor.precio >= parseInt(min) && tutor.precio <= parseInt(max);
            });
        }

        // Filtro de valoración
        const ratingFilter = document.getElementById('ratingFilter').value;
        if (ratingFilter) {
            const minRating = parseFloat(ratingFilter);
            filtered = filtered.filter(tutor => tutor.rating >= minRating);
        }

        // Filtro de disponibilidad
        const availabilityCheckboxes = document.querySelectorAll('.availability-filter input[type="checkbox"]:checked');
        if (availabilityCheckboxes.length > 0) {
            const disponibilidadesSeleccionadas = Array.from(availabilityCheckboxes).map(cb => cb.value);
            filtered = filtered.filter(tutor => {
                return Object.values(tutor.disponibilidad).some(disp => 
                    disponibilidadesSeleccionadas.includes(disp) || disp === 'disponible'
                );
            });
        }

        // Filtro de idioma
        const languageCheckboxes = document.querySelectorAll('.language-filter input[type="checkbox"]:checked');
        if (languageCheckboxes.length > 0) {
            const idiomasSeleccionados = Array.from(languageCheckboxes).map(cb => cb.value);
            filtered = filtered.filter(tutor => 
                tutor.idiomas.some(idioma => idiomasSeleccionados.includes(idioma))
            );
        }

        // Filtro de experiencia
        const experienceRadio = document.querySelector('.experience-filter input[type="radio"]:checked');
        if (experienceRadio) {
            const experienciaMinima = experienceRadio.value;
            filtered = filtered.filter(tutor => {
                const añosExperiencia = parseInt(tutor.experiencia);
                switch (experienciaMinima) {
                    case '5+':
                        return añosExperiencia >= 5;
                    case '3-5':
                        return añosExperiencia >= 3 && añosExperiencia <= 5;
                    case '1-3':
                        return añosExperiencia >= 1 && añosExperiencia <= 3;
                    default:
                        return true;
                }
            });
        }

        filteredTutores = filtered;
        renderTutores(filteredTutores);
        updateResultsCount();
    }

    function clearFilters() {
        // Limpiar búsqueda
        document.getElementById('searchInput').value = '';
        
        // Limpiar filtros principales
        document.getElementById('nivelFilter').value = '';
        document.getElementById('materiaFilter').value = '';
        document.getElementById('precioFilter').value = '';
        document.getElementById('ratingFilter').value = '';
        
        // Limpiar checkboxes
        document.querySelectorAll('.availability-filter input[type="checkbox"], .language-filter input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        // Limpiar radios
        document.querySelectorAll('.experience-filter input[type="radio"]').forEach(radio => {
            radio.checked = false;
        });
        
        filteredTutores = [...tutoresData];
        renderTutores(filteredTutores);
        updateResultsCount();
    }

    function renderTutores(tutores) {
        const container = document.getElementById('tutoresContainer');
        if (!container) return;

        if (tutores.length === 0) {
            container.innerHTML = `
                <div class="no-results status-message info">
                    <i class="fas fa-search"></i>
                    <h3>No se encontraron tutores</h3>
                    <p>Intenta ajustar tus filtros de búsqueda</p>
                </div>
            `;
            return;
        }

        const tutoresHTML = tutores.map(tutor => createTutorCard(tutor)).join('');
        container.innerHTML = tutoresHTML;
        
        // Agregar clase de vista
        container.className = `tutores-container ${currentView === 'list' ? 'list-view' : ''}`;
        
        // Agregar event listeners a los botones
        container.querySelectorAll('.btn-ver-perfil').forEach(btn => {
            btn.addEventListener('click', function() {
                const tutorId = this.dataset.id;
                showTutorModal(tutorId);
            });
        });

        container.querySelectorAll('.btn-reservar-rapido').forEach(btn => {
            btn.addEventListener('click', function() {
                const tutorId = this.dataset.id;
                openReservationModal(tutorId);
            });
        });
    }

    function createTutorCard(tutor) {
        const stars = '⭐'.repeat(Math.floor(tutor.rating)) + '☆'.repeat(5 - Math.floor(tutor.rating));
        const disponibilidadBadges = Object.values(tutor.disponibilidad)
            .filter(disp => disp !== 'no disponible')
            .slice(0, 3)
            .map(disp => `<span class="availability-badge ${disp === 'disponible' ? 'available' : ''}">${disp}</span>`)
            .join('');

        return `
            <div class="tutor-card ${currentView === 'list' ? 'list-view' : ''}">
                <div class="tutor-photo">
                    <img src="${tutor.foto}" alt="${tutor.nombre}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iNDAiIGN5PSI0MCIgcj0iNDAiIGZpbGw9IiM4YjVjZjYiLz4KPHN2ZyB4PSIyMCIgeT0iMjAiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIj4KPHBhdGggZD0iTTEyIDEyQzE0LjIwOTEgMTIgMTYgMTAuMjA5MSAxNiA4QzE2IDUuNzkwODYgMTQuMjA5MSA0IDEyIDRDOS43OTA4NiA0IDggNS43OTA4NiA4IDhDOCAxMC4yMDkxIDkuNzkwODYgMTIgMTIgMTJaIiBmaWxsPSJ3aGl0ZSIvPgo8cGF0aCBkPSJNMTIgMTRDOC42ODYyOSAxNCA2IDE2LjY4NjMgNiAyMEgxOEMxOCAxNi42ODYzIDE1LjMxMzcgMTQgMTIgMTRaIiBmaWxsPSJ3aGl0ZSIvPgo8L3N2Zz4KPC9zdmc+'">
                </div>
                <div class="tutor-info">
                    <h3 class="tutor-name">${tutor.nombre}</h3>
                    <div class="tutor-subject">${getMateriaName(tutor.materia)}</div>
                    <div class="tutor-price">$${tutor.precio}/hora</div>
                    <div class="tutor-rating">
                        <span class="stars">${stars}</span>
                        <span class="count">(${tutor.rating})</span>
                    </div>
                    <div class="tutor-experience">${tutor.experiencia} de experiencia</div>
                    <div class="tutor-availability">
                        ${disponibilidadBadges}
                    </div>
                    <div class="tutor-actions">
                        <button class="btn-ver-perfil" data-id="${tutor.id}">Ver Perfil</button>
                        <button class="btn-reservar-rapido" data-id="${tutor.id}">Reservar</button>
                    </div>
                </div>
            </div>
        `;
    }

    function getMateriaName(materia) {
        const materias = {
            'matematicas': 'Matemáticas',
            'fisica': 'Física',
            'quimica': 'Química',
            'biologia': 'Biología',
            'historia': 'Historia',
            'literatura': 'Literatura',
            'ingles': 'Inglés',
            'filosofia': 'Filosofía'
        };
        return materias[materia] || materia;
    }

    function updateViewButtons() {
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.view === currentView) {
                btn.classList.add('active');
            }
        });
    }

    function updateResultsCount() {
        const countElement = document.getElementById('resultsCount');
        if (countElement) {
            countElement.textContent = `Mostrando ${filteredTutores.length} tutores`;
        }
    }

    function showTutorModal(tutorId) {
        const tutor = tutoresData.find(t => t.id === tutorId);
        if (!tutor) return;

        const modal = document.getElementById('tutorModal');
        if (!modal) return;
        modal.dataset.tutorId = tutor.id;
        
        // Llenar información del modal
        document.getElementById('tutorName').textContent = tutor.nombre;
        document.getElementById('tutorNameInfo').textContent = tutor.nombre;
        document.getElementById('tutorPhoto').src = tutor.foto;
        document.getElementById('tutorPhoto').alt = tutor.nombre;
        
        const stars = '⭐'.repeat(Math.floor(tutor.rating)) + '☆'.repeat(5 - Math.floor(tutor.rating));
        document.getElementById('tutorStars').innerHTML = stars;
        document.getElementById('tutorRating').textContent = `(${tutor.rating})`;
        document.getElementById('tutorPrice').textContent = `$${tutor.precio}/hora`;
        
        document.getElementById('tutorBio').textContent = tutor.biografia;
        
        // Materias
        const subjectsHTML = tutor.materias.map(materia => 
            `<span class="subject-badge">${materia}</span>`
        ).join('');
        document.getElementById('tutorSubjects').innerHTML = subjectsHTML;
        
        // Disponibilidad
        const availabilityHTML = createAvailabilityCalendar(tutor.disponibilidad);
        document.getElementById('tutorAvailability').innerHTML = availabilityHTML;
        
        // Reseñas
        const reviewsHTML = tutor.reseñas.map(review => `
            <div class="review-item">
                <div class="review-header">
                    <span class="review-author">${review.autor}</span>
                    <span class="review-rating">${'⭐'.repeat(review.rating)}</span>
                </div>
                <div class="review-text">${review.texto}</div>
            </div>
        `).join('');
        document.getElementById('tutorReviews').innerHTML = reviewsHTML;
        
        // Mostrar modal
        modal.classList.add('is-visible');
    }

    function createAvailabilityCalendar(disponibilidad) {
        const dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
        const diasCompletos = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'];
        
        let html = '<div class="availability-calendar">';
        
        // Headers
        dias.forEach(dia => {
            html += `<div class="day-header">${dia}</div>`;
        });
        
        // Celdas
        diasCompletos.forEach(dia => {
            const disp = disponibilidad[dia];
            const className = disp === 'no disponible' ? 'unavailable' : 'available';
            const texto = disp === 'no disponible' ? 'No' : 'Sí';
            html += `<div class="day-cell ${className}">${texto}</div>`;
        });
        
        html += '</div>';
        return html;
    }

    function setupTutorModal() {
        const modal = document.getElementById('tutorModal');
        if (!modal) return;
        const closeBtn = modal.querySelector('.close-modal');
        const btnReservar = modal.querySelector('.btn-reservar');
        const btnContactar = modal.querySelector('.btn-contactar');

        // Cerrar modal
        function closeModal() {
            modal.classList.remove('is-visible');
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
        }

        // Cerrar al hacer clic fuera del modal
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Botones del modal
        if (btnReservar) {
            btnReservar.addEventListener('click', function() {
                const tutorId = modal.dataset.tutorId;
                if (!tutorId) {
                    alert('Selecciona un tutor antes de reservar.');
                    return;
                }
                closeModal();
                openReservationModal(tutorId);
            });
        }

        if (btnContactar) {
            btnContactar.addEventListener('click', function() {
                alert('Abriremos un chat seguro para coordinar con tu tutor.');
                closeModal();
            });
        }
    }

    function setupReservationModal() {
        if (!reservationModal || !reservationForm) return;

        setDefaultReservationValues();

        reservationForm.addEventListener('submit', handleReservationSubmit);

        if (reservationCancelBtn) {
            reservationCancelBtn.addEventListener('click', (event) => {
                event.preventDefault();
                closeReservationModal();
            });
        }

        if (reservationCloseBtn) {
            reservationCloseBtn.addEventListener('click', closeReservationModal);
        }

        reservationModal.addEventListener('click', (event) => {
            if (event.target === reservationModal) {
                closeReservationModal();
            }
        });
    }

    function openReservationModal(tutorId) {
        if (!reservationModal || !reservationForm) return;
        const tutor = tutoresData.find((t) => t.id === tutorId);
        if (!tutor) {
            alert('No encontramos la información del tutor seleccionado.');
            return;
        }

        activeReservationTutor = tutorId;
        if (reservationTutorName) {
            reservationTutorName.textContent = `Reservar con ${tutor.nombre}`;
        }
        reservationForm.reset();
        setDefaultReservationValues();
        reservationModal.dataset.tutorId = tutorId;
        reservationModal.classList.add('is-visible');
    }

    function closeReservationModal() {
        if (!reservationModal || !reservationForm) return;
        reservationModal.classList.remove('is-visible');
        reservationForm.reset();
        setDefaultReservationValues();
        activeReservationTutor = null;
    }

    function setDefaultReservationValues() {
        if (reservationDateInput) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            reservationDateInput.value = tomorrow.toISOString().split('T')[0];
        }
        if (reservationTimeInput) {
            reservationTimeInput.value = '18:00';
        }
        if (reservationModeInput) {
            reservationModeInput.value = 'online';
        }
    }

    async function handleReservationSubmit(event) {
        event.preventDefault();
        if (!activeReservationTutor) {
            alert('Selecciona un tutor antes de reservar.');
            return;
        }

        const estudiante = reservationNameInput?.value?.trim();
        const fechaSeleccionada = reservationDateInput?.value;
        const horaSeleccionada = reservationTimeInput?.value;
        const modalidad = reservationModeInput?.value || 'online';

        if (!estudiante || !fechaSeleccionada || !horaSeleccionada) {
            alert('Completa todos los campos obligatorios.');
            return;
        }

        const fecha = `${fechaSeleccionada} ${horaSeleccionada}`;

        try {
            const response = await fetch(`${API_URL}/${activeReservationTutor}/reservas`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ estudiante, fecha, modalidad })
            });

            if (!response.ok) {
                throw new Error('No se pudo completar la reserva.');
            }

            const data = await response.json();
            alert(data.message);
            closeReservationModal();
        } catch (error) {
            alert(error.message || 'Error al crear la reserva.');
        }
    }

    function setupSwapForm() {
        const swapForm = document.getElementById('swapForm');
        if (!swapForm) return;

        swapForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(swapForm);
            const payload = {
                nombre: formData.get('swapNombre')?.trim(),
                materiaOfreces: formData.get('swapOfreces'),
                materiaSolicitas: formData.get('swapSolicitas'),
                descripcion: formData.get('swapDescripcion')?.trim()
            };

            if (!payload.nombre || !payload.materiaOfreces || !payload.materiaSolicitas) {
                alert('Completa todos los campos obligatorios.');
                return;
            }

            try {
                const response = await fetch(SWAP_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error('No se pudo registrar tu intercambio.');
                }

                await response.json();
                alert('¡Intercambio registrado! Te avisaremos cuando encontremos a tu match.');
                swapForm.reset();
            } catch (error) {
                alert(error.message || 'Error al registrar el intercambio.');
            }
        });
    }

    function showStatusMessage(message, type = 'info') {
        const container = document.getElementById('tutoresContainer');
        if (!container) return;

        const icon = type === 'error'
            ? '<i class="fas fa-triangle-exclamation"></i>'
            : '<i class="fas fa-circle-notch fa-spin"></i>';

        container.innerHTML = `
            <div class="no-results status-message ${type}">
                ${icon}
                <h3>${message}</h3>
            </div>
        `;
    }
});
