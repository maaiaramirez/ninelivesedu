// JavaScript específico para la página de apuntes conectado al backend Node.js
document.addEventListener('DOMContentLoaded', () => {
    const API_URL = '/api/apuntes';
    let apuntesData = [];
    let filteredApuntes = [];
    let currentView = 'grid';
    let activeApunteId = null;

    initApuntesPage();

    async function initApuntesPage() {
        setupEventListeners();
        await loadApuntes();
    }

    async function loadApuntes() {
        try {
            showStatusMessage('Cargando apuntes...', 'loading');
            const response = await fetch(API_URL);
            if (!response.ok) {
                throw new Error('No se pudo cargar la biblioteca de apuntes.');
            }
            apuntesData = await response.json();
            filteredApuntes = [...apuntesData];
            renderApuntes(filteredApuntes);
            updateResultsCount();
        } catch (error) {
            console.error(error);
            showStatusMessage(error.message || 'Error inesperado al cargar los apuntes.', 'error');
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
        const ordenFilter = document.getElementById('ordenFilter');

        if (nivelFilter) {
            nivelFilter.addEventListener('change', applyFilters);
        }
        if (materiaFilter) {
            materiaFilter.addEventListener('change', applyFilters);
        }
        if (ordenFilter) {
            ordenFilter.addEventListener('change', applyFilters);
        }

        // Filtros adicionales
        const checkboxes = document.querySelectorAll('.checkbox-group input[type="checkbox"]');
        const radios = document.querySelectorAll('input[type="radio"]');
        
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', applyFilters);
        });
        
        radios.forEach(radio => {
            radio.addEventListener('change', applyFilters);
        });

        // Botón subir apuntes
        const btnSubirApuntes = document.querySelector('.btn-subir-apuntes');
        if (btnSubirApuntes) {
            btnSubirApuntes.addEventListener('click', showUploadModal);
        }

        // Cambio de vista
        const viewBtns = document.querySelectorAll('.view-btn');
        viewBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                currentView = this.dataset.view;
                updateViewButtons();
                renderApuntes(filteredApuntes);
            });
        });

        // Limpiar filtros
        const btnLimpiarFiltros = document.querySelector('.btn-limpiar-filtros');
        if (btnLimpiarFiltros) {
            btnLimpiarFiltros.addEventListener('click', clearFilters);
        }

        // Modal de subida
        setupUploadModal();
    }

    function handleSearch() {
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        
        filteredApuntes = apuntesData.filter(apunte => 
            apunte.titulo.toLowerCase().includes(searchTerm) ||
            apunte.materia.toLowerCase().includes(searchTerm) ||
            apunte.autor.toLowerCase().includes(searchTerm) ||
            apunte.descripcion.toLowerCase().includes(searchTerm)
        );
        
        applyFilters();
    }

    function applyFilters() {
        if (!apuntesData.length) {
            return;
        }

        let filtered = [...apuntesData];

        // Filtro de búsqueda
        const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
        if (searchTerm) {
            filtered = filtered.filter(apunte => 
                apunte.titulo.toLowerCase().includes(searchTerm) ||
                apunte.materia.toLowerCase().includes(searchTerm) ||
                apunte.autor.toLowerCase().includes(searchTerm) ||
                apunte.descripcion.toLowerCase().includes(searchTerm)
            );
        }

        // Filtro de nivel
        const nivelFilter = document.getElementById('nivelFilter').value;
        if (nivelFilter) {
            filtered = filtered.filter(apunte => apunte.nivel === nivelFilter);
        }

        // Filtro de materia
        const materiaFilter = document.getElementById('materiaFilter').value;
        if (materiaFilter) {
            filtered = filtered.filter(apunte => apunte.materia === materiaFilter);
        }

        // Filtro de tipo de archivo
        const tipoCheckboxes = document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked');
        if (tipoCheckboxes.length > 0) {
            const tiposSeleccionados = Array.from(tipoCheckboxes).map(cb => cb.value);
            filtered = filtered.filter(apunte => tiposSeleccionados.includes(apunte.tipo));
        }

        // Filtro de calificación
        const ratingRadio = document.querySelector('input[name="rating"]:checked');
        if (ratingRadio) {
            const minRating = parseFloat(ratingRadio.value);
            filtered = filtered.filter(apunte => apunte.rating >= minRating);
        }

        // Filtro de fecha
        const dateRadio = document.querySelector('input[name="date"]:checked');
        if (dateRadio) {
            const now = new Date();
            const filterDate = new Date();
            
            switch (dateRadio.value) {
                case 'week':
                    filterDate.setDate(now.getDate() - 7);
                    break;
                case 'month':
                    filterDate.setMonth(now.getMonth() - 1);
                    break;
                case 'year':
                    filterDate.setFullYear(now.getFullYear() - 1);
                    break;
            }
            
            filtered = filtered.filter(apunte => new Date(apunte.fecha) >= filterDate);
        }

        // Ordenamiento
        const ordenFilter = document.getElementById('ordenFilter').value;
        switch (ordenFilter) {
            case 'fecha':
                filtered.sort((a, b) => new Date(b.fecha) - new Date(a.fecha));
                break;
            case 'popularidad':
                filtered.sort((a, b) => b.descargas - a.descargas);
                break;
            case 'titulo':
                filtered.sort((a, b) => a.titulo.localeCompare(b.titulo));
                break;
            case 'autor':
                filtered.sort((a, b) => a.autor.localeCompare(b.autor));
                break;
        }

        filteredApuntes = filtered;
        renderApuntes(filteredApuntes);
        updateResultsCount();
    }

    function clearFilters() {
        // Limpiar búsqueda
        document.getElementById('searchInput').value = '';
        
        // Limpiar filtros principales
        document.getElementById('nivelFilter').value = '';
        document.getElementById('materiaFilter').value = '';
        document.getElementById('ordenFilter').value = 'fecha';
        
        // Limpiar checkboxes
        document.querySelectorAll('.checkbox-group input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        // Limpiar radios
        document.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.checked = false;
        });
        
        filteredApuntes = [...apuntesData];
        renderApuntes(filteredApuntes);
        updateResultsCount();
    }

    function renderApuntes(apuntes) {
        const container = document.getElementById('apuntesContainer');
        if (!container) return;

        if (apuntes.length === 0) {
            container.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <h3>No se encontraron apuntes</h3>
                    <p>Intenta ajustar tus filtros de búsqueda</p>
                </div>
            `;
            return;
        }

        const apuntesHTML = apuntes.map(apunte => createApunteCard(apunte)).join('');
        container.innerHTML = apuntesHTML;
        
        // Agregar clase de vista
        container.className = `apuntes-container ${currentView === 'list' ? 'list-view' : ''}`;
        
        // Agregar event listeners a los botones de descarga
        container.querySelectorAll('.btn-descargar').forEach(btn => {
            btn.addEventListener('click', function() {
                const apunteId = this.dataset.id;
                downloadApunte(apunteId);
            });
        });
    }

    function createApunteCard(apunte) {
        const stars = '⭐'.repeat(Math.floor(apunte.rating || 0)) + '☆'.repeat(5 - Math.floor(apunte.rating || 0));
        
        return `
            <div class="apunte-card ${currentView === 'list' ? 'list-view' : ''}">
                <div class="apunte-header">
                    <div class="apunte-icon">
                        <i class="${apunte.icono}"></i>
                    </div>
                    <div class="apunte-info">
                        <h3>${apunte.titulo}</h3>
                    <div class="apunte-meta">
                            <span><i class="fas fa-user"></i> ${apunte.autor}</span>
                            <span><i class="fas fa-calendar"></i> ${formatDate(apunte.fecha)}</span>
                        <span><i class="fas fa-download"></i> ${apunte.descargas}</span>
                        </div>
                    </div>
                </div>
                <div class="apunte-description">
                    ${apunte.descripcion}
                </div>
                <div class="apunte-footer">
                    <div class="apunte-rating">
                        <span class="stars">${stars}</span>
                        <span class="count">(${apunte.rating})</span>
                    </div>
                    <button class="btn-descargar" data-id="${apunte.id}">
                        <i class="fas fa-download"></i> Descargar
                    </button>
                </div>
            </div>
        `;
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
            countElement.textContent = `Mostrando ${filteredApuntes.length} apuntes`;
        }
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    function downloadApunte(apunteId) {
        const apunte = apuntesData.find(a => a.id === apunteId);
        if (!apunte) return;

        activeApunteId = apunteId;

        fetch(`${API_URL}/${apunteId}/descargas`, { method: 'POST' })
            .then(() => {
                apunte.descargas += 1;
                renderApuntes(filteredApuntes);
            })
            .catch(() => null);

        if (apunte.archivo && String(apunte.archivo).startsWith('/uploads/')) {
            window.open(`${API_URL}/${apunteId}/descargar`, '_blank');
            return;
        }

        alert('Este apunte no tiene archivo físico subido todavía.');
    }

    function showUploadModal() {
        const modal = document.getElementById('uploadModal');
        if (modal) {
            modal.classList.add('is-visible');
        }
    }

    function setupUploadModal() {
        const modal = document.getElementById('uploadModal');
        if (!modal) {
            return;
        }
        const closeBtn = modal.querySelector('.close-modal');
        const cancelBtn = modal.querySelector('.btn-cancel');
        const uploadForm = document.getElementById('uploadForm');

        // Cerrar modal
        function closeModal() {
            modal.classList.remove('is-visible');
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', closeModal);
        }

        // Cerrar al hacer clic fuera del modal
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Manejar envío del formulario
        if (uploadForm) {
            uploadForm.addEventListener('submit', async function(e) {
                e.preventDefault();

                const formData = buildApunteFormData();
                if (!formData) {
                    return;
                }

                try {
                    const response = await fetch(API_URL, {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        throw new Error('No se pudo subir el apunte.');
                    }

                    const created = await response.json();
                    apuntesData.unshift(created);
                    filteredApuntes = [...apuntesData];
                    renderApuntes(filteredApuntes);
                    updateResultsCount();
                    alert(`¡Apunte "${created.titulo}" subido exitosamente!`);
                    closeModal();
                    this.reset();
                    resetFileUploadArea();
                } catch (error) {
                    alert(error.message || 'Ocurrió un error al subir el apunte.');
                }
            });
        }

        // Manejar drag & drop para archivos
        const fileUploadArea = modal.querySelector('.file-upload-area');
        const fileInput = modal.querySelector('#apunteArchivo');

        if (fileUploadArea && fileInput) {
            fileUploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                this.style.borderColor = '#8b5cf6';
            });

            fileUploadArea.addEventListener('dragleave', function(e) {
                e.preventDefault();
                this.style.borderColor = '#e9ecef';
            });

            fileUploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                this.style.borderColor = '#e9ecef';
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    fileInput.files = files;
                    updateFileDisplay(files[0]);
                }
            });

            fileInput.addEventListener('change', function() {
                if (this.files.length > 0) {
                    updateFileDisplay(this.files[0]);
                }
            });
        }
    }

    function updateFileDisplay(file) {
        const fileUploadArea = document.querySelector('.file-upload-area');
        if (fileUploadArea) {
            fileUploadArea.innerHTML = `
                <i class="fas fa-file-${getFileIcon(file.type)}"></i>
                <p>${file.name}</p>
                <span class="file-types">${formatFileSize(file.size)}</span>
            `;
        }
    }

    function getFileIcon(fileType) {
        if (fileType.includes('pdf')) return 'pdf';
        if (fileType.includes('word') || fileType.includes('document')) return 'word';
        if (fileType.includes('powerpoint') || fileType.includes('presentation')) return 'powerpoint';
        if (fileType.includes('image')) return 'image';
        return 'alt';
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function resetFileUploadArea() {
        const fileUploadArea = document.querySelector('.file-upload-area');
        if (fileUploadArea) {
            fileUploadArea.innerHTML = `
                <i class="fas fa-cloud-upload-alt"></i>
                <p>Arrastra tu archivo aquí o haz clic para seleccionar</p>
                <span class="file-types">PDF, Word, PowerPoint, Imágenes</span>
            `;
        }
    }

    function buildApunteFormData() {
        const titulo = document.getElementById('apunteTitulo').value.trim();
        const materia = document.getElementById('apunteMateria').value;
        const nivel = document.getElementById('apunteNivel').value;
        const descripcion = document.getElementById('apunteDescripcion').value.trim();
        const autor = document.getElementById('apunteAutor')?.value?.trim();
        const archivoInput = document.getElementById('apunteArchivo');
        const selectedFile = archivoInput?.files?.[0];

        if (!titulo || !materia || !nivel) {
            alert('Por favor completa los campos obligatorios.');
            return null;
        }

        const extension = selectedFile ? getExtension(selectedFile.name) : 'pdf';

        const formData = new FormData();
        formData.append('titulo', titulo);
        formData.append('materia', materia);
        formData.append('nivel', nivel);
        formData.append('descripcion', descripcion);
        formData.append('tipo', extension);
        if (autor) {
            formData.append('autor', autor);
        }
        if (selectedFile) {
            formData.append('archivo', selectedFile);
        }

        return formData;
    }

    function getExtension(filename = '') {
        const parts = filename.split('.');
        return parts.length > 1 ? parts.pop().toLowerCase() : 'pdf';
    }

    function showStatusMessage(message, type = 'info') {
        const container = document.getElementById('apuntesContainer');
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
