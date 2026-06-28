// JavaScript específico para la página de foros conectado al backend Node.js
document.addEventListener('DOMContentLoaded', () => {
    const API_URL = '/api/foros';

    let postsData = [];
    let filteredPosts = [];
    let currentView = 'list';
    let activePostId = null;

    initForosPage();

    async function initForosPage() {
        setupEventListeners();
        setupModals();
        await loadPosts();
    }

    async function loadPosts() {
        try {
            showStatusMessage('Cargando foros...', 'loading');
            const response = await fetch(API_URL);
            if (!response.ok) {
                throw new Error('No se pudieron cargar los foros.');
            }
            postsData = await response.json();
            filteredPosts = [...postsData];
            renderPosts(filteredPosts);
            updateResultsCount();
        } catch (error) {
            console.error(error);
            showStatusMessage(error.message || 'Error inesperado al cargar los foros.', 'error');
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
        const tipoFilter = document.getElementById('tipoFilter');
        const ordenFilter = document.getElementById('ordenFilter');

        if (nivelFilter) {
            nivelFilter.addEventListener('change', applyFilters);
        }
        if (materiaFilter) {
            materiaFilter.addEventListener('change', applyFilters);
        }
        if (tipoFilter) {
            tipoFilter.addEventListener('change', applyFilters);
        }
        if (ordenFilter) {
            ordenFilter.addEventListener('change', applyFilters);
        }

        // Categorías
        const categoryItems = document.querySelectorAll('.category-item');
        categoryItems.forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                const nivel = this.dataset.nivel;
                const materia = this.dataset.materia;
                
                if (nivel) {
                    document.getElementById('nivelFilter').value = nivel;
                }
                if (materia) {
                    document.getElementById('materiaFilter').value = materia;
                }
                
                applyFilters();
            });
        });

        // Cambio de vista
        const viewBtns = document.querySelectorAll('.view-btn');
        viewBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                currentView = this.dataset.view;
                updateViewButtons();
                renderPosts(filteredPosts);
            });
        });

        // Botón nuevo post
        const btnNuevoPost = document.querySelector('.btn-nuevo-post');
        if (btnNuevoPost) {
            btnNuevoPost.addEventListener('click', showNewPostModal);
        }

    }

    function handleSearch() {
        const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
        
        filteredPosts = postsData.filter(post => 
            post.titulo.toLowerCase().includes(searchTerm) ||
            post.contenido.toLowerCase().includes(searchTerm) ||
            post.tags.some(tag => tag.toLowerCase().includes(searchTerm)) ||
            post.autor.toLowerCase().includes(searchTerm)
        );
        
        applyFilters();
    }

    function applyFilters() {
        if (!postsData.length) {
            return;
        }

        let filtered = [...postsData];

        // Filtro de búsqueda
        const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
        if (searchTerm) {
            filtered = filtered.filter(post => 
                post.titulo.toLowerCase().includes(searchTerm) ||
                post.contenido.toLowerCase().includes(searchTerm) ||
                post.tags.some(tag => tag.toLowerCase().includes(searchTerm)) ||
                post.autor.toLowerCase().includes(searchTerm)
            );
        }

        // Filtro de nivel
        const nivelFilter = document.getElementById('nivelFilter').value;
        if (nivelFilter) {
            filtered = filtered.filter(post => post.nivel === nivelFilter);
        }

        // Filtro de materia
        const materiaFilter = document.getElementById('materiaFilter').value;
        if (materiaFilter) {
            filtered = filtered.filter(post => post.materia === materiaFilter);
        }

        // Filtro de tipo
        const tipoFilter = document.getElementById('tipoFilter').value;
        if (tipoFilter) {
            filtered = filtered.filter(post => post.tipo === tipoFilter);
        }

        // Ordenamiento
        const ordenFilter = document.getElementById('ordenFilter').value;
        switch (ordenFilter) {
            case 'reciente':
                filtered.sort((a, b) => new Date(b.fecha) - new Date(a.fecha));
                break;
            case 'popular':
                filtered.sort((a, b) => b.votos - a.votos);
                break;
            case 'respuestas':
                filtered.sort((a, b) => b.respuestas - a.respuestas);
                break;
            case 'votos':
                filtered.sort((a, b) => b.votos - a.votos);
                break;
        }

        filteredPosts = filtered;
        renderPosts(filteredPosts);
        updateResultsCount();
    }

    function renderPosts(posts) {
        const container = document.getElementById('postsContainer');
        if (!container) return;

        if (posts.length === 0) {
            container.innerHTML = `
                <div class="no-results status-message info">
                    <i class="fas fa-search"></i>
                    <h3>No se encontraron posts</h3>
                    <p>Intenta ajustar tus filtros de búsqueda</p>
                </div>
            `;
            return;
        }

        const postsHTML = posts.map(post => createPostCard(post)).join('');
        container.innerHTML = postsHTML;
        
        // Agregar clase de vista
        container.className = `posts-container ${currentView === 'grid' ? 'grid-view' : ''}`;
        
        // Agregar event listeners
        setupPostEventListeners();
    }

    function createPostCard(post) {
        const tagsHTML = post.tags.map(tag => 
            `<span class="post-tag">${tag}</span>`
        ).join('');

        const resueltoBadge = post.resuelto ? '<span class="post-type-badge resuelto">✓ Resuelto</span>' : '';

        return `
            <div class="post-card ${post.tipo}" data-id="${post.id}">
                <div class="post-header">
                    <div class="post-author-avatar">
                        ${post.autor.charAt(0)}
                    </div>
                    <div class="post-meta">
                        <div class="post-author">${post.autor}</div>
                        <div class="post-date">${formatDate(post.fecha)}</div>
                    </div>
                    <div class="post-type-badge ${post.tipo}">${post.tipo}</div>
                    ${resueltoBadge}
                </div>
                
                <div class="post-content">
                    <h3 class="post-title">${post.titulo}</h3>
                    <p class="post-preview">${post.contenido.substring(0, 150)}${post.contenido.length > 150 ? '...' : ''}</p>
                    <div class="post-tags">${tagsHTML}</div>
                </div>
                
                <div class="post-footer">
                    <div class="post-stats">
                        <div class="post-stat">
                            <i class="fas fa-thumbs-up"></i>
                            <span>${post.votos}</span>
                        </div>
                        <div class="post-stat">
                            <i class="fas fa-comments"></i>
                            <span>${post.respuestas}</span>
                        </div>
                        <div class="post-stat">
                            <i class="fas fa-eye"></i>
                            <span>${post.vistas}</span>
                        </div>
                    </div>
                    
                    <div class="post-actions">
                        <button class="btn-action btn-vote" data-id="${post.id}">
                            <i class="fas fa-thumbs-up"></i>
                        </button>
                        <button class="btn-action btn-responder" data-id="${post.id}">
                            Responder
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    function setupPostEventListeners() {
        // Botones de votar
        document.querySelectorAll('.btn-vote').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const postId = this.dataset.id;
                votePost(postId);
            });
        });

        // Botones de responder
        document.querySelectorAll('.btn-responder').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const postId = this.dataset.id;
                showPostModal(postId);
            });
        });

        // Click en post para ver completo
        document.querySelectorAll('.post-card').forEach(card => {
            card.addEventListener('click', function() {
                const postId = this.dataset.id;
                showPostModal(postId);
            });
        });
    }

    async function votePost(postId) {
        const post = postsData.find(p => p.id === postId);
        if (!post) return;

        try {
            const response = await fetch(`${API_URL}/${postId}/vote`, { method: 'POST' });
            if (!response.ok) throw new Error();
            const data = await response.json();
            post.votos = data.votos;
            renderPosts(filteredPosts);
        } catch (error) {
            alert('No se pudo registrar tu voto.');
        }
    }

    async function showPostModal(postId) {
        const post = await fetchPost(postId);
        if (!post) return;

        activePostId = postId;

        const modal = document.getElementById('postModal');
        document.getElementById('postModalTitle').textContent = post.titulo;

        const postContent = `
            <div class="post-header">
                <div class="post-author-avatar">
                    ${post.autor.charAt(0)}
                </div>
                <div class="post-meta">
                    <div class="post-author">${post.autor}</div>
                    <div class="post-date">${formatDate(post.fecha)}</div>
                </div>
                <div class="post-type-badge ${post.tipo}">${post.tipo}</div>
            </div>
            <div class="post-content">
                <p>${post.contenido}</p>
                <div class="post-tags">
                    ${post.tags.map(tag => `<span class="post-tag">${tag}</span>`).join('')}
                </div>
            </div>
        `;

        document.getElementById('postModalContent').innerHTML = postContent;
        renderResponses(post.responses);
        modal.classList.add('is-visible');
    }

    async function fetchPost(postId) {
        const cached = postsData.find(p => p.id === postId);
        if (cached && cached.responses) {
            return cached;
        }

        try {
            const response = await fetch(`${API_URL}/${postId}`);
            if (!response.ok) throw new Error();
            const post = await response.json();

            const index = postsData.findIndex(p => p.id === postId);
            if (index >= 0) {
                postsData[index] = post;
            } else {
                postsData.push(post);
            }

            return post;
        } catch (error) {
            alert('No se pudo cargar el post.');
            return null;
        }
    }

    function renderResponses(responses = []) {
        const container = document.getElementById('postModalResponses');
        if (!container) return;

        if (!responses.length) {
            container.innerHTML = '<p class="no-responses">Aún no hay respuestas. ¡Sé el primero en comentar!</p>';
            return;
        }

        container.innerHTML = responses.map(respuesta => `
            <div class="response-item">
                <div class="response-header">
                    <div class="response-author-avatar">${respuesta.autor.charAt(0)}</div>
                    <div class="response-author">${respuesta.autor}</div>
                    <div class="response-date">${formatDate(respuesta.fecha)}</div>
                </div>
                <div class="response-text">${respuesta.texto}</div>
            </div>
        `).join('');
    }

    function showNewPostModal() {
        const modal = document.getElementById('newPostModal');
        modal.classList.add('is-visible');
    }

    function setupModals() {
        const newPostModal = document.getElementById('newPostModal');
        const postModal = document.getElementById('postModal');
        const newPostForm = document.getElementById('newPostForm');
        const newPostClose = newPostModal.querySelector('.close-modal');
        const newPostCancel = newPostModal.querySelector('.btn-cancel');
        const postClose = postModal.querySelector('.close-modal');
        const addResponseBtn = postModal.querySelector('.btn-add-response');

        const closeNewPost = () => { newPostModal.classList.remove('is-visible'); };
        const closePost = () => { postModal.classList.remove('is-visible'); };

        [newPostModal, postModal].forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('is-visible');
                }
            });
        });

        newPostClose.addEventListener('click', closeNewPost);
        newPostCancel.addEventListener('click', closeNewPost);
        postClose.addEventListener('click', closePost);

        if (newPostForm) {
            newPostForm.addEventListener('submit', async (event) => {
                event.preventDefault();

                const formData = new FormData(newPostForm);
                const payload = {
                    titulo: formData.get('postTitulo')?.trim(),
                    contenido: formData.get('postContenido')?.trim(),
                    autor: 'Usuario Nine Lives Edu',
                    nivel: formData.get('postNivel'),
                    materia: formData.get('postMateria'),
                    tipo: formData.get('postTipo'),
                    tags: formData.get('postTags')
                        ? formData.get('postTags').split(',').map(tag => tag.trim()).filter(Boolean)
                        : []
                };

                if (!payload.titulo || !payload.contenido) {
                    alert('Completa el título y contenido del post.');
                    return;
                }

                try {
                    const response = await fetch(API_URL, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    if (!response.ok) throw new Error('No se pudo crear el post.');

                    const newPost = await response.json();
                    postsData.unshift(newPost);
                    filteredPosts = [...postsData];
                    renderPosts(filteredPosts);
                    updateResultsCount();
                    alert('¡Post publicado correctamente!');
                    newPostForm.reset();
                    closeNewPost();
                } catch (error) {
                    alert(error.message || 'Error al crear el post.');
                }
            });
        }

        if (addResponseBtn) {
            addResponseBtn.addEventListener('click', async () => {
                const responseText = document.getElementById('responseText').value.trim();
                if (!responseText) {
                    alert('Escribe tu respuesta antes de enviarla.');
                    return;
                }

                if (!activePostId) {
                    alert('Selecciona un post antes de responder.');
                    return;
                }

                try {
                    const response = await fetch(`${API_URL}/${activePostId}/respuestas`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            autor: 'Usuario Nine Lives Edu',
                            texto: responseText
                        })
                    });

                    if (!response.ok) {
                        throw new Error('No se pudo enviar la respuesta.');
                    }

                    const nuevaRespuesta = await response.json();
                    const post = postsData.find(p => p.id === activePostId);
                    if (post) {
                        post.responses = post.responses || [];
                        post.responses.push(nuevaRespuesta);
                        post.respuestas = post.responses.length;
                        renderResponses(post.responses);
                        renderPosts(filteredPosts);
                    }

                    document.getElementById('responseText').value = '';
                    alert('¡Respuesta publicada!');
                } catch (error) {
                    alert(error.message || 'Error al publicar la respuesta.');
                }
            });
        }
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
            countElement.textContent = `Mostrando ${filteredPosts.length} posts`;
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

    function showStatusMessage(message, type = 'info') {
        const container = document.getElementById('postsContainer');
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
