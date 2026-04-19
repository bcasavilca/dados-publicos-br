/**
 * Dados Públicos BR - Frontend v2
 * Experiência tipo Google Dataset Search
 */

// Configuração
const API_URL = window.location.origin + '/api';

// Estado global
let state = {
    loading: false,
    results: [],
    filters: {
        tipo: ['portal', 'dataset'],
        qualidade: ['Alta', 'Media', 'Baixa'],
        formato: ['CSV', 'JSON', 'API', 'XLS'],
        scoreMin: 0
    },
    sortBy: 'score',
    searchTerm: ''
};

// Elementos DOM
const elements = {
    searchInput: document.getElementById('searchInput'),
    searchBtn: document.getElementById('searchBtn'),
    clearSearch: document.getElementById('clearSearch'),
    resultsGrid: document.getElementById('resultsGrid'),
    loadingState: document.getElementById('loadingState'),
    emptyState: document.getElementById('emptyState'),
    noResults: document.getElementById('noResults'),
    statsBar: document.getElementById('statsBar'),
    resultsCount: document.getElementById('resultsCount'),
    sortBy: document.getElementById('sortBy'),
    previewModal: document.getElementById('previewModal'),
    previewContent: document.getElementById('previewContent'),
    scoreRange: document.getElementById('scoreRange'),
    scoreValue: document.getElementById('scoreValue'),
    countPortais: document.getElementById('countPortais'),
    countDatasets: document.getElementById('countDatasets'),
    clearFilters: document.getElementById('clearFilters')
};

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    updateCounts();
});

// Event Listeners
function initEventListeners() {
    // Busca
    elements.searchBtn.addEventListener('click', handleSearch);
    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    elements.searchInput.addEventListener('input', toggleClearBtn);
    elements.clearSearch.addEventListener('click', clearSearch);
    
    // Filtros
    document.querySelectorAll('input[name="tipo"]').forEach(cb => {
        cb.addEventListener('change', updateTipoFilter);
    });
    document.querySelectorAll('input[name="qualidade"]').forEach(cb => {
        cb.addEventListener('change', updateQualidadeFilter);
    });
    document.querySelectorAll('input[name="formato"]').forEach(cb => {
        cb.addEventListener('change', updateFormatoFilter);
    });
    
    // Score range
    elements.scoreRange.addEventListener('input', (e) => {
        state.filters.scoreMin = parseInt(e.target.value);
        elements.scoreValue.textContent = e.target.value;
        applyFilters();
    });
    
    // Sort
    elements.sortBy.addEventListener('change', (e) => {
        state.sortBy = e.target.value;
        applyFilters();
    });
    
    // Limpar filtros
    elements.clearFilters.addEventListener('click', clearAllFilters);
}

// Toggle clear button
function toggleClearBtn() {
    elements.clearSearch.style.display = elements.searchInput.value ? 'flex' : 'none';
}

// Clear search
function clearSearch() {
    elements.searchInput.value = '';
    elements.clearSearch.style.display = 'none';
    resetView();
}

// Reset view
function resetView() {
    state.results = [];
    state.searchTerm = '';
    elements.resultsGrid.innerHTML = '';
    elements.loadingState.style.display = 'none';
    elements.noResults.style.display = 'none';
    elements.statsBar.style.display = 'none';
    elements.emptyState.style.display = 'block';
}

// Quick search
function quickSearch(term) {
    elements.searchInput.value = term;
    toggleClearBtn();
    handleSearch();
}

// Handle search
async function handleSearch() {
    const term = elements.searchInput.value.trim();
    if (!term) return;
    
    state.searchTerm = term.toLowerCase();
    state.loading = true;
    
    // UI Loading
    elements.emptyState.style.display = 'none';
    elements.noResults.style.display = 'none';
    elements.resultsGrid.innerHTML = '';
    elements.loadingState.style.display = 'block';
    elements.loadingState.innerHTML = `
        <div class="spinner-large"></div>
        <p>Buscando dados...</p>
        <p style="font-size: 0.875rem; color: var(--gray-400); margin-top: var(--space-2);"
            >Primeira busca pode levar 10-15s (servidor acordando)</p>
    `;
    elements.statsBar.style.display = 'none';
    
    // Timeout de 30 segundos
    const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Timeout')), 30000)
    );
    
    try {
        const fetchPromise = fetch(`${API_URL}/buscar?q=${encodeURIComponent(term)}`);
        const response = await Promise.race([fetchPromise, timeoutPromise]);
        
        if (!response.ok) throw new Error('HTTP ' + response.status);
        
        const data = await response.json();
        
        state.results = data.resultados || [];
        state.loading = false;
        
        // Analytics
        window.ANALYTICS.logSearch(term, state.results.length);
        
        elements.loadingState.style.display = 'none';
        
        if (state.results.length === 0) {
            elements.noResults.style.display = 'block';
        } else {
            updateCounts();
            applyFilters();
            elements.statsBar.style.display = 'flex';
        }
        
    } catch (error) {
        console.error('Erro na busca:', error);
        state.loading = false;
        elements.loadingState.style.display = 'none';
        elements.noResults.style.display = 'block';
        elements.noResults.innerHTML = `
            <div class="no-results-icon">😕</div>
            <h3>Erro na conexão</h3>
            <p>O servidor pode estar iniciando. Aguarde 10-15s e tente novamente.</p>
            <p style="font-size: 0.75rem; color: var(--gray-400); margin-top: var(--space-2);">
                Erro: ${error.message}
            </p>
            <button class="btn btn-secondary" onclick="handleSearch()" style="margin-top: var(--space-4);">
                Tentar novamente
            </button>
        `;
    }
}

// Update counts
function updateCounts() {
    const portais = state.results.filter(r => r.tipo === 'portal').length;
    const datasets = state.results.filter(r => r.tipo === 'dataset').length;
    
    elements.countPortais.textContent = portais;
    elements.countDatasets.textContent = datasets;
}

// Update filters
function updateTipoFilter() {
    const checked = Array.from(document.querySelectorAll('input[name="tipo"]:checked'))
        .map(cb => cb.value);
    state.filters.tipo = checked;
    applyFilters();
}

function updateQualidadeFilter() {
    const checked = Array.from(document.querySelectorAll('input[name="qualidade"]:checked'))
        .map(cb => cb.value);
    state.filters.qualidade = checked;
    applyFilters();
}

function updateFormatoFilter() {
    const checked = Array.from(document.querySelectorAll('input[name="formato"]:checked'))
        .map(cb => cb.value);
    state.filters.formato = checked;
    applyFilters();
}

// Apply filters
function applyFilters() {
    let filtered = state.results.filter(item => {
        // Tipo
        if (!state.filters.tipo.includes(item.tipo)) return false;
        
        // Qualidade
        const qualidade = item.qualidade || 'Media';
        if (!state.filters.qualidade.includes(qualidade)) return false;
        
        // Formato
        const formato = item.Formato || item.formato || 'Outro';
        const formatoMatch = state.filters.formato.some(f => 
            formato.toUpperCase().includes(f) || f === 'XLS' && formato.toUpperCase().includes('XLS')
        );
        if (!formatoMatch) return false;
        
        // Score
        const score = item.score || 0;
        if (score < state.filters.scoreMin) return false;
        
        return true;
    });
    
    // Sort
    filtered.sort((a, b) => {
        switch (state.sortBy) {
            case 'score':
                return (b.score || 0) - (a.score || 0);
            case 'qualidade':
                const qualidadeOrder = { 'Alta': 3, 'Media': 2, 'Baixa': 1 };
                return (qualidadeOrder[b.qualidade] || 0) - (qualidadeOrder[a.qualidade] || 0);
            case 'nome':
                return (a.Titulo || a.titulo || '').localeCompare(b.Titulo || b.titulo || '');
            default:
                return 0;
        }
    });
    
    renderResults(filtered);
    elements.resultsCount.textContent = filtered.length;
}

// Render results
function renderResults(results) {
    elements.resultsGrid.innerHTML = results.map(item => createCard(item)).join('');
}

// Create card HTML
function createCard(item) {
    const isDataset = item.tipo === 'dataset';
    const tipoClass = isDataset ? 'badge-dataset' : 'badge-portal';
    const tipoLabel = isDataset ? 'Dataset' : 'Portal';
    const titulo = item.Titulo || item.titulo || 'Sem título';
    const url = item.URL || item.url || '#';
    const qualidade = item.Qualidade || item.qualidade || 'Media';
    const formato = item.Formato || item.formato || 'Outro';
    const score = item.score || 0;
    const descricao = item.Descricao || item.descricao || '';
    const uf = item.UF || item.organizacao || 'Federal';
    
    const scoreClass = score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low';
    const qualidadeClass = `badge-qualidade-${qualidade.toLowerCase()}`;
    
    // Analytics tracking
    const analyticsClick = `window.ANALYTICS.logClick('${item.tipo}', '${titulo.replace(/'/g, "\\'")}', ${score});`;
    
    return `
        <div class="card" onclick="openPreview('${btoa(JSON.stringify(item))}')">
            <div class="card-header">
                <div class="card-badges">
                    <span class="badge ${tipoClass}">${tipoLabel}</span>
                    <span class="badge ${qualidadeClass}">${qualidade}</span>
                </div>
                <div class="card-title-section">
                    <h3 class="card-title">${escapeHtml(titulo)}</h3>
                    <div class="card-url">${escapeHtml(url)}</div>
                </div>
            </div>
            
            <div class="card-meta">
                <span class="meta-item">📍 ${uf}</span>
                <span class="meta-item">📄 ${formato}</span>
                ${isDataset ? `<span class="meta-item">🏢 ${item.organizacao || ''}</span>` : ''}
            </div>
            
            ${descricao ? `<p class="card-description">${escapeHtml(descricao.substring(0, 150))}${descricao.length > 150 ? '...' : ''}</p>` : ''}
            
            <div class="card-footer">
                <div class="card-actions">
                    <a href="${url}" target="_blank" class="btn btn-primary" onclick="event.stopPropagation()">
                        Acessar →
                    </a>
                    ${isDataset ? `<button class="btn btn-secondary" onclick="event.stopPropagation(); previewData('${url}')">
                        👁️ Preview
                    </button>` : ''}
                </div>
                
                <div class="score-display">
                    <div class="score-bar">
                        <div class="score-fill ${scoreClass}" style="width: ${score}%"></div>
                    </div>
                    <span class="score-value">${score}</span>
                </div>
            </div>
        </div>
    `;
}

// Escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Open preview modal
function openPreview(itemEncoded) {
    try {
        const item = JSON.parse(atob(itemEncoded));
        
        const isDataset = item.tipo === 'dataset';
        const titulo = item.Titulo || item.titulo;
        const descricao = item.Descricao || item.descricao || 'Sem descrição';
        
        elements.previewContent.innerHTML = `
            <div style="padding: var(--space-8);">
                <div style="display: flex; gap: var(--space-2); margin-bottom: var(--space-4);">
                    <span class="badge ${isDataset ? 'badge-dataset' : 'badge-portal'}">
                        ${isDataset ? 'Dataset' : 'Portal'}
                    </span>
                    <span class="badge badge-qualidade-${(item.qualidade || 'media').toLowerCase()}">
                        ${item.qualidade || 'Media'}
                    </span>
                </div>
                
                <h2 style="font-size: var(--text-2xl); font-weight: 700; margin-bottom: var(--space-4); color: var(--gray-900);">
                    ${escapeHtml(titulo)}
                </h2>
                
                <p style="font-size: var(--text-base); color: var(--gray-600); line-height: 1.7; margin-bottom: var(--space-6);">
                    ${escapeHtml(descricao)}
                </p>
                
                <div style="background: var(--gray-50); border-radius: var(--radius); padding: var(--space-4); margin-bottom: var(--space-6);">
                    <h4 style="font-size: var(--text-sm); font-weight: 600; color: var(--gray-700); margin-bottom: var(--space-3);">
                        Detalhes
                    </h4>
                    <div style="display: grid; gap: var(--space-2); font-size: var(--text-sm);">
                        <div><strong>URL:</strong> <a href="${item.url || item.URL}" target="_blank" style="color: var(--primary-500);">${escapeHtml(item.url || item.URL)}</a></div>
                        <div><strong>Formato:</strong> ${item.formato || item.Formato || 'N/A'}</div>
                        ${item.organizacao ? `<div><strong>Organização:</strong> ${item.organizacao}</div>` : ''}
                        <div><strong>Score:</strong> ${item.score || 0}/100</div>
                    </div>
                </div>
                
                <a href="${item.url || item.URL}" target="_blank" class="btn btn-primary btn-large" style="width: 100%;">
                    Acessar Fonte
                </a>
            </div>
        `;
        
        elements.previewModal.style.display = 'flex';
    } catch (e) {
        console.error('Erro ao abrir preview:', e);
    }
}

// Close preview
function closePreview() {
    elements.previewModal.style.display = 'none';
}

// Clear all filters
function clearAllFilters() {
    document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });
    elements.scoreRange.value = 0;
    elements.scoreValue.textContent = '0';
    
    state.filters = {
        tipo: ['portal', 'dataset'],
        qualidade: ['Alta', 'Media', 'Baixa'],
        formato: ['CSV', 'JSON', 'API', 'XLS'],
        scoreMin: 0
    };
    
    applyFilters();
}

// Clear all (para botão no no-results)
function clearAll() {
    clearAllFilters();
    clearSearch();
}

// Fechar modal ao clicar fora
window.onclick = function(event) {
    if (event.target === elements.previewModal) {
        closePreview();
    }
};

// Preview data (placeholder - requer backend)
async function previewData(url) {
    alert('Preview de dados em desenvolvimento.\n\nRequer download e parsing do dataset.');
}
