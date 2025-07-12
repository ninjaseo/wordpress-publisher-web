/**
 * WordPress Publisher Web Application
 * Modern JavaScript frontend with individual article management
 */

class WordPressPublisher {
    constructor() {
        this.currentProfile = null;
        this.articles = []; // Array of article objects with individual options
        this.selectedCategories = []; // Global categories
        this.selectedTags = []; // Global tags
        this.availableCategories = [];
        this.availableTags = [];
        this.currentTaxonomyType = null;
        this.selectedProfileName = null;
        this.currentArticleIndex = null; // For individual taxonomy selection
        
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadProfiles();
        await this.loadCurrentDirectory();
        await this.loadFiles();
        this.updateStatus('🟢 Aplicación cargada correctamente');
    }

    bindEvents() {
        // Profile management
        document.getElementById('manage-profiles-btn').addEventListener('click', () => this.openProfileModal());
        document.getElementById('profile-select').addEventListener('change', (e) => this.selectProfile(e.target.value));
        
        // Profile modal events
        document.getElementById('new-profile-btn').addEventListener('click', () => this.openProfileForm());
        document.getElementById('test-connection-btn').addEventListener('click', () => this.testConnection());
        document.getElementById('delete-profile-btn').addEventListener('click', () => this.deleteProfile());
        document.getElementById('profile-form').addEventListener('submit', (e) => this.saveProfile(e));

        // File management
        document.getElementById('change-directory-btn').addEventListener('click', () => this.changeDirectory());
        document.getElementById('refresh-files-btn').addEventListener('click', () => this.loadFiles());
        document.getElementById('select-all-btn').addEventListener('click', () => this.selectAllFiles());
        document.getElementById('deselect-all-btn').addEventListener('click', () => this.deselectAllFiles());

        // Global taxonomy management
        document.getElementById('select-categories-btn').addEventListener('click', () => this.openTaxonomyModal('categories'));
        document.getElementById('select-tags-btn').addEventListener('click', () => this.openTaxonomyModal('tags'));
        
        // Taxonomy modal events
        document.getElementById('taxonomy-search').addEventListener('input', (e) => this.filterTaxonomy(e.target.value));
        document.getElementById('add-taxonomy-btn').addEventListener('click', () => this.addNewTaxonomyItem());
        document.getElementById('select-all-taxonomy-btn').addEventListener('click', () => this.selectAllTaxonomy());
        document.getElementById('deselect-all-taxonomy-btn').addEventListener('click', () => this.deselectAllTaxonomy());
        document.getElementById('accept-taxonomy-btn').addEventListener('click', () => this.acceptTaxonomySelection());

        // Publication
        document.getElementById('publish-btn').addEventListener('click', () => this.publishArticles());

        // Modal close events
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target.id);
            }
        });
    }

    // API Methods
    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                }
            };

            if (data) {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(`/api${endpoint}`, options);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }

    async uploadFile(file, endpoint) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`/api${endpoint}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('File upload failed:', error);
            throw error;
        }
    }

    // Profile Management
    async loadProfiles() {
        try {
            const profiles = await this.apiCall('/profiles');
            this.populateProfileSelect(profiles);
        } catch (error) {
            this.showToast('Error cargando perfiles: ' + error.message, 'error');
        }
    }

    populateProfileSelect(profiles) {
        const select = document.getElementById('profile-select');
        select.innerHTML = '<option value="">Selecciona un perfil</option>';
        
        profiles.forEach(profile => {
            const option = document.createElement('option');
            option.value = profile.name;
            option.textContent = `${profile.name} (${profile.url})`;
            select.appendChild(option);
        });
    }

    async selectProfile(profileName) {
        if (!profileName) {
            this.currentProfile = null;
            this.hideProfileInfo();
            return;
        }

        try {
            this.showLoading('Cargando perfil...');
            const profile = await this.apiCall(`/profiles/${profileName}`);
            this.currentProfile = profile;
            this.selectedProfileName = profileName;
            this.showProfileInfo(profile);
            await this.loadTaxonomies();
            this.hideLoading();
        } catch (error) {
            this.hideLoading();
            this.showToast('Error cargando perfil: ' + error.message, 'error');
        }
    }

    showProfileInfo(profile) {
        const infoDiv = document.getElementById('profile-info');
        const detailsSpan = document.getElementById('profile-details-text');
        detailsSpan.textContent = `✅ Conectado a: ${profile.url} (Usuario: ${profile.username})`;
        infoDiv.style.display = 'block';
    }

    hideProfileInfo() {
        document.getElementById('profile-info').style.display = 'none';
    }

    // File Management with Article Grid
    async loadCurrentDirectory() {
        try {
            const response = await this.apiCall('/current-directory');
            document.getElementById('current-directory').textContent = `📁 Carpeta: ${response.directory}`;
        } catch (error) {
            console.error('Error loading directory:', error);
        }
    }

    async loadFiles() {
        try {
            this.showLoading('Cargando archivos...');
            const files = await this.apiCall('/files');
            this.articles = files.map(file => ({
                ...file,
                selected: false,
                status: 'draft', // default to draft
                featured_image: null,
                categories: [], // Individual categories for this article
                tags: [] // Individual tags for this article
            }));
            this.renderArticleTable();
            this.hideLoading();
        } catch (error) {
            this.hideLoading();
            this.showToast('Error cargando archivos: ' + error.message, 'error');
        }
    }

    renderArticleTable() {
        const container = document.getElementById('article-grid');
        container.innerHTML = '';

        if (this.articles.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No hay archivos .txt o .md en esta carpeta</p>';
            return;
        }

        // Create table structure
        const table = document.createElement('table');
        table.className = 'articles-table';
        
        // Table header
        const thead = document.createElement('thead');
        thead.innerHTML = `
            <tr>
                <th>✓</th>
                <th>📄 Archivo</th>
                <th>📊 Estado</th>
                <th>🖼️ Imagen</th>
                <th>🏷️ Categorías</th>
                <th>🔖 Etiquetas</th>
                <th>📏 Tamaño</th>
                <th>📅 Modificado</th>
            </tr>
        `;
        table.appendChild(thead);
        
        // Table body
        const tbody = document.createElement('tbody');
        this.articles.forEach((article, index) => {
            const row = this.createArticleRow(article, index);
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        
        container.appendChild(table);
    }

    createArticleRow(article, index) {
        const row = document.createElement('tr');
        row.className = `article-row ${article.selected ? 'selected' : ''}`;
        
        // Format individual categories and tags for display
        const categoriesDisplay = article.categories.length > 0 
            ? article.categories.map(id => {
                const cat = this.availableCategories.find(c => c.id === id);
                return cat ? cat.name : '';
            }).filter(name => name).join(', ') 
            : '';
            
        const tagsDisplay = article.tags.length > 0 
            ? article.tags.map(id => {
                const tag = this.availableTags.find(t => t.id === id);
                return tag ? tag.name : '';
            }).filter(name => name).join(', ') 
            : '';
        
        row.innerHTML = `
            <td>
                <input type="checkbox" class="article-checkbox" ${article.selected ? 'checked' : ''} 
                       onchange="app.toggleArticleSelection(${index})">
            </td>
            <td class="file-name">
                <div class="file-title">${article.name}</div>
            </td>
            <td>
                <select class="status-select compact" onchange="app.updateArticleStatus(${index}, this.value)">
                    <option value="draft" ${article.status === 'draft' ? 'selected' : ''}>🟡 Borrador</option>
                    <option value="publish" ${article.status === 'publish' ? 'selected' : ''}>🟢 Publicar</option>
                </select>
            </td>
            <td>
                <div class="image-upload compact">
                    <input type="file" accept="image/*" onchange="app.updateArticleImage(${index}, this)" 
                           id="file-${index}" style="display: none;">
                    <button type="button" onclick="document.getElementById('file-${index}').click()" 
                            class="btn-image ${article.featured_image ? 'has-image' : ''}">
                        ${article.featured_image ? '✅' : '📷'}
                    </button>
                </div>
            </td>
            <td>
                <div class="taxonomy-cell">
                    <span class="taxonomy-display">${categoriesDisplay || 'Ninguna'}</span>
                    <button type="button" onclick="app.openIndividualTaxonomyModal(${index}, 'categories')" 
                            class="btn-taxonomy">✏️</button>
                </div>
            </td>
            <td>
                <div class="taxonomy-cell">
                    <span class="taxonomy-display">${tagsDisplay || 'Ninguna'}</span>
                    <button type="button" onclick="app.openIndividualTaxonomyModal(${index}, 'tags')" 
                            class="btn-taxonomy">✏️</button>
                </div>
            </td>
            <td class="file-size">${this.formatFileSize(article.size)}</td>
            <td class="file-date">${this.formatDate(article.modified)}</td>
        `;

        return row;
    }

    toggleArticleSelection(index) {
        this.articles[index].selected = !this.articles[index].selected;
        this.renderArticleTable();
    }

    updateArticleStatus(index, status) {
        this.articles[index].status = status;
    }

    updateArticleImage(index, input) {
        const file = input.files[0];
        if (file) {
            this.articles[index].featured_image = file;
            this.renderArticleTable();
        }
    }

    selectAllFiles() {
        this.articles.forEach(article => article.selected = true);
        this.renderArticleTable();
    }

    deselectAllFiles() {
        this.articles.forEach(article => article.selected = false);
        this.renderArticleTable();
    }

    async changeDirectory() {
        try {
            const response = await this.apiCall('/change-directory', 'POST');
            if (response.success) {
                await this.loadCurrentDirectory();
                await this.loadFiles();
                this.showToast('Carpeta cambiada correctamente', 'success');
            }
        } catch (error) {
            this.showToast('Error cambiando carpeta: ' + error.message, 'error');
        }
    }

    // Taxonomy Management
    async loadTaxonomies() {
        if (!this.currentProfile) return;
        
        try {
            const [categories, tags] = await Promise.all([
                this.apiCall(`/categories/${this.selectedProfileName}`),
                this.apiCall(`/tags/${this.selectedProfileName}`)
            ]);
            
            this.availableCategories = categories;
            this.availableTags = tags;
        } catch (error) {
            this.showToast('Error cargando taxonomías: ' + error.message, 'error');
        }
    }

    openTaxonomyModal(type) {
        if (!this.currentProfile) {
            this.showToast('Selecciona un perfil primero', 'warning');
            return;
        }

        this.currentTaxonomyType = type;
        this.currentArticleIndex = null; // Global selection
        const modal = document.getElementById('taxonomy-modal');
        const title = document.getElementById('taxonomy-modal-title');
        
        title.innerHTML = type === 'categories' ? 
            '<i class="fas fa-tags"></i> Seleccionar Categorías (Global)' : 
            '<i class="fas fa-hashtag"></i> Seleccionar Etiquetas (Global)';
        
        this.populateTaxonomyModal(type);
        this.showModal('taxonomy-modal');
    }

    openIndividualTaxonomyModal(articleIndex, type) {
        if (!this.currentProfile) {
            this.showToast('Selecciona un perfil primero', 'warning');
            return;
        }

        this.currentTaxonomyType = type;
        this.currentArticleIndex = articleIndex; // Individual selection
        const modal = document.getElementById('taxonomy-modal');
        const title = document.getElementById('taxonomy-modal-title');
        const article = this.articles[articleIndex];
        
        title.innerHTML = type === 'categories' ? 
            `<i class="fas fa-tags"></i> Categorías para: ${article.name}` : 
            `<i class="fas fa-hashtag"></i> Etiquetas para: ${article.name}`;
        
        this.populateIndividualTaxonomyModal(type, articleIndex);
        this.showModal('taxonomy-modal');
    }

    populateTaxonomyModal(type) {
        const container = document.getElementById('taxonomy-items');
        const items = type === 'categories' ? this.availableCategories : this.availableTags;
        const selected = type === 'categories' ? this.selectedCategories : this.selectedTags;
        
        container.innerHTML = '';
        
        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'taxonomy-item';
            div.innerHTML = `
                <input type="checkbox" value="${item.id}" ${selected.includes(item.id) ? 'checked' : ''}>
                <span>${item.name}</span>
            `;
            container.appendChild(div);
        });
    }

    populateIndividualTaxonomyModal(type, articleIndex) {
        const container = document.getElementById('taxonomy-items');
        const items = type === 'categories' ? this.availableCategories : this.availableTags;
        const article = this.articles[articleIndex];
        const selected = type === 'categories' ? article.categories : article.tags;
        
        container.innerHTML = '';
        
        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'taxonomy-item';
            div.innerHTML = `
                <input type="checkbox" value="${item.id}" ${selected.includes(item.id) ? 'checked' : ''}>
                <span>${item.name}</span>
            `;
            container.appendChild(div);
        });
    }

    acceptTaxonomySelection() {
        const checkboxes = document.querySelectorAll('#taxonomy-items input[type="checkbox"]:checked');
        const selectedIds = Array.from(checkboxes).map(cb => parseInt(cb.value));
        const items = this.currentTaxonomyType === 'categories' ? this.availableCategories : this.availableTags;
        
        if (this.currentArticleIndex !== null) {
            // Individual article selection
            if (this.currentTaxonomyType === 'categories') {
                this.articles[this.currentArticleIndex].categories = selectedIds;
            } else {
                this.articles[this.currentArticleIndex].tags = selectedIds;
            }
            this.renderArticleTable(); // Refresh table to show updated values
        } else {
            // Global selection
            if (this.currentTaxonomyType === 'categories') {
                this.selectedCategories = selectedIds;
                this.updateTaxonomyDisplay('categories', selectedIds, items);
            } else {
                this.selectedTags = selectedIds;
                this.updateTaxonomyDisplay('tags', selectedIds, items);
            }
        }
        
        this.closeModal('taxonomy-modal');
    }

    updateTaxonomyDisplay(type, selectedIds, items) {
        const element = document.getElementById(`selected-${type}`);
        if (selectedIds.length === 0) {
            element.textContent = type === 'categories' ? 'Ninguna seleccionada' : 'Ninguna seleccionadas';
        } else {
            const names = selectedIds.map(id => {
                const item = items.find(i => i.id === id);
                return item ? item.name : '';
            }).filter(name => name);
            element.textContent = names.join(', ');
        }
    }

    // Publication
    async publishArticles() {
        const selectedArticles = this.articles.filter(article => article.selected);
        
        if (selectedArticles.length === 0) {
            this.showToast('Selecciona al menos un artículo', 'warning');
            return;
        }

        if (!this.currentProfile) {
            this.showToast('Selecciona un perfil de WordPress', 'warning');
            return;
        }

        try {
            this.showLoading('Publicando artículos...');
            
            const results = [];
            for (const article of selectedArticles) {
                try {
                    // Upload featured image if exists
                    let featuredMediaId = null;
                    if (article.featured_image) {
                        const imageResult = await this.uploadFile(article.featured_image, `/upload-image/${this.selectedProfileName}`);
                        featuredMediaId = imageResult.media_id;
                    }

                    // Use individual categories/tags if set, otherwise use global ones
                    const categories = article.categories.length > 0 ? article.categories : this.selectedCategories;
                    const tags = article.tags.length > 0 ? article.tags : this.selectedTags;
                    
                    // Publish article
                    const publishData = {
                        file_path: article.path,
                        status: article.status,
                        categories: categories,
                        tags: tags,
                        featured_media: featuredMediaId
                    };

                    const result = await this.apiCall(`/publish/${this.selectedProfileName}`, 'POST', publishData);
                    results.push({
                        filename: article.name,
                        success: true,
                        url: result.url,
                        status: article.status
                    });
                } catch (error) {
                    results.push({
                        filename: article.name,
                        success: false,
                        error: error.message
                    });
                }
            }

            this.hideLoading();
            this.showPublishResults(results);
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Error durante la publicación: ' + error.message, 'error');
        }
    }

    showPublishResults(results) {
        const modal = document.getElementById('results-modal');
        const content = document.getElementById('results-content');
        
        let html = '<div style="margin-bottom: 1rem;">';
        
        const successful = results.filter(r => r.success);
        const failed = results.filter(r => !r.success);
        
        if (successful.length > 0) {
            html += '<h3 style="color: #059669; margin-bottom: 1rem;">✅ Publicados correctamente:</h3>';
            successful.forEach(result => {
                html += `
                    <div style="padding: 0.75rem; margin-bottom: 0.5rem; background: #f0fdf4; border-left: 4px solid #10b981; border-radius: 0.5rem;">
                        <strong>${result.filename}</strong> - Estado: ${result.status === 'publish' ? '🟢 Publicado' : '🟡 Borrador'}<br>
                        <a href="${result.url}" target="_blank" style="color: #059669;">Ver artículo →</a>
                    </div>
                `;
            });
        }
        
        if (failed.length > 0) {
            html += '<h3 style="color: #dc2626; margin-bottom: 1rem; margin-top: 2rem;">❌ Errores:</h3>';
            failed.forEach(result => {
                html += `
                    <div style="padding: 0.75rem; margin-bottom: 0.5rem; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 0.5rem;">
                        <strong>${result.filename}</strong><br>
                        <span style="color: #dc2626;">${result.error}</span>
                    </div>
                `;
            });
        }
        
        html += '</div>';
        content.innerHTML = html;
        this.showModal('results-modal');
    }

    // Profile Modal Management
    openProfileModal() {
        this.loadProfilesForModal();
        this.showModal('profile-modal');
    }

    async loadProfilesForModal() {
        try {
            const profiles = await this.apiCall('/profiles');
            this.populateProfilesModal(profiles);
        } catch (error) {
            this.showToast('Error cargando perfiles: ' + error.message, 'error');
        }
    }

    populateProfilesModal(profiles) {
        const container = document.getElementById('profiles-container');
        container.innerHTML = '';

        if (profiles.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6b7280; padding: 2rem;">No hay perfiles configurados</p>';
            return;
        }

        profiles.forEach(profile => {
            const div = document.createElement('div');
            div.className = `profile-item ${profile.name === this.selectedProfileName ? 'selected' : ''}`;
            div.onclick = () => this.selectProfileInModal(profile.name, div);
            
            div.innerHTML = `
                <div class="profile-item-info">
                    <div class="profile-item-name">${profile.name}</div>
                    <div class="profile-item-details">${profile.url} (${profile.username})</div>
                </div>
            `;
            container.appendChild(div);
        });
    }

    selectProfileInModal(profileName, element) {
        // Remove previous selection
        document.querySelectorAll('.profile-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Add selection to clicked item
        element.classList.add('selected');
        this.selectedProfileName = profileName;
        
        // Enable buttons
        document.getElementById('test-connection-btn').disabled = false;
        document.getElementById('delete-profile-btn').disabled = false;
    }

    openProfileForm() {
        this.showModal('profile-form-modal');
    }

    async saveProfile(e) {
        e.preventDefault();
        
        const formData = {
            name: document.getElementById('profile-name').value,
            url: document.getElementById('profile-url').value,
            username: document.getElementById('profile-username').value,
            app_password: document.getElementById('profile-password').value
        };

        try {
            this.showLoading('Guardando perfil...');
            await this.apiCall('/profiles', 'POST', formData);
            this.hideLoading();
            this.closeModal('profile-form-modal');
            this.loadProfiles();
            this.loadProfilesForModal();
            this.showToast('Perfil guardado correctamente', 'success');
            
            // Clear form
            document.getElementById('profile-form').reset();
        } catch (error) {
            this.hideLoading();
            this.showToast('Error guardando perfil: ' + error.message, 'error');
        }
    }

    async testConnection() {
        if (!this.selectedProfileName) return;

        try {
            this.showLoading('Probando conexión...');
            await this.apiCall(`/test-connection/${this.selectedProfileName}`);
            this.hideLoading();
            this.showToast('✅ Conexión exitosa', 'success');
        } catch (error) {
            this.hideLoading();
            this.showToast('❌ Error de conexión: ' + error.message, 'error');
        }
    }

    async deleteProfile() {
        if (!this.selectedProfileName) return;

        if (!confirm(`¿Estás seguro de eliminar el perfil "${this.selectedProfileName}"?`)) {
            return;
        }

        try {
            this.showLoading('Eliminando perfil...');
            await this.apiCall(`/profiles/${this.selectedProfileName}`, 'DELETE');
            this.hideLoading();
            this.loadProfiles();
            this.loadProfilesForModal();
            this.showToast('Perfil eliminado correctamente', 'success');
            
            // Reset selection
            this.selectedProfileName = null;
            document.getElementById('test-connection-btn').disabled = true;
            document.getElementById('delete-profile-btn').disabled = true;
        } catch (error) {
            this.hideLoading();
            this.showToast('Error eliminando perfil: ' + error.message, 'error');
        }
    }

    // Utility Methods
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('es-ES', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    updateStatus(message) {
        document.getElementById('status-text').textContent = message;
    }

    showLoading(message = 'Cargando...') {
        document.getElementById('loading-text').textContent = message;
        document.getElementById('loading-overlay').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }

    showModal(modalId) {
        document.getElementById(modalId).classList.add('show');
    }

    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('show');
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    // Taxonomy search and filtering
    filterTaxonomy(searchTerm) {
        const items = document.querySelectorAll('#taxonomy-items .taxonomy-item');
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(searchTerm.toLowerCase()) ? 'flex' : 'none';
        });
    }

    selectAllTaxonomy() {
        const checkboxes = document.querySelectorAll('#taxonomy-items input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = true);
    }

    deselectAllTaxonomy() {
        const checkboxes = document.querySelectorAll('#taxonomy-items input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = false);
    }

    async addNewTaxonomyItem() {
        const input = document.getElementById('new-taxonomy-item');
        const name = input.value.trim();
        
        if (!name) {
            this.showToast('Ingresa un nombre para el nuevo elemento', 'warning');
            return;
        }

        try {
            const endpoint = this.currentTaxonomyType === 'categories' ? '/categories' : '/tags';
            await this.apiCall(`${endpoint}/${this.selectedProfileName}`, 'POST', { name });
            
            // Reload taxonomies
            await this.loadTaxonomies();
            this.populateTaxonomyModal(this.currentTaxonomyType);
            
            input.value = '';
            this.showToast(`${this.currentTaxonomyType === 'categories' ? 'Categoría' : 'Etiqueta'} agregada correctamente`, 'success');
        } catch (error) {
            this.showToast('Error agregando elemento: ' + error.message, 'error');
        }
    }
}

// Global functions for HTML event handlers
function closeModal(modalId) {
    app.closeModal(modalId);
}

// Initialize application
const app = new WordPressPublisher();