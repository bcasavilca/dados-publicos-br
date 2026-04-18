// Configuracao da API
const API_URL = 'https://dados-publicos-br.onrender.com';

// Estado global
let state = {
    loading: false,
    activeTab: 'busca',
    anomalias: [],
    eventos: [],
    fornecedores: []
};

// Elementos DOM
const elements = {
    searchInput: document.getElementById('searchInput'),
    searchBtn: document.getElementById('searchBtn'),
    tabBusca: document.getElementById('tabBusca'),
    tabAnomalias: document.getElementById('tabAnomalias'),
    tabFornecedores: document.getElementById('tabFornecedores'),
    contentBusca: document.getElementById('contentBusca'),
    contentAnomalias: document.getElementById('contentAnomalias'),
    contentFornecedores: document.getElementById('contentFornecedores'),
    resultsGrid: document.getElementById('resultsGrid'),
    anomaliasList: document.getElementById('anomaliasList'),
    fornecedoresList: document.getElementById('fornecedoresList'),
    loadingState: document.getElementById('loadingState')
};

// Inicializacao
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadAnomalias();
    loadFornecedores();
});

function initEventListeners() {
    // Busca
    elements.searchBtn.addEventListener('click', handleSearch);
    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    
    // Tabs
    elements.tabBusca.addEventListener('click', () => switchTab('busca'));
    elements.tabAnomalias.addEventListener('click', () => switchTab('anomalias'));
    elements.tabFornecedores.addEventListener('click', () => switchTab('fornecedores'));
}

function switchTab(tab) {
    state.activeTab = tab;
    
    // Atualizar tabs
    elements.tabBusca.classList.toggle('active', tab === 'busca');
    elements.tabAnomalias.classList.toggle('active', tab === 'anomalias');
    elements.tabFornecedores.classList.toggle('active', tab === 'fornecedores');
    
    // Mostrar conteúdo
    elements.contentBusca.style.display = tab === 'busca' ? 'block' : 'none';
    elements.contentAnomalias.style.display = tab === 'anomalias' ? 'block' : 'none';
    elements.contentFornecedores.style.display = tab === 'fornecedores' ? 'block' : 'none';
}

async function handleSearch() {
    const term = elements.searchInput.value.trim();
    if (!term) return;
    
    state.loading = true;
    elements.loadingState.style.display = 'block';
    elements.resultsGrid.innerHTML = '';
    
    try {
        const response = await fetch(`${API_URL}/eventos?q=${encodeURIComponent(term)}`);
        const data = await response.json();
        
        renderEventos(data.eventos || []);
        
    } catch (error) {
        console.error('Erro:', error);
        elements.resultsGrid.innerHTML = '<p>Erro ao carregar dados</p>';
    } finally {
        state.loading = false;
        elements.loadingState.style.display = 'none';
    }
}

async function loadAnomalias() {
    try {
        const response = await fetch(`${API_URL}/anomalias`);
        const data = await response.json();
        
        renderAnomalias(data);
    } catch (error) {
        console.error('Erro ao carregar anomalias:', error);
        elements.anomaliasList.innerHTML = '<p>Erro ao carregar anomalias</p>';
    }
}

async function loadFornecedores() {
    try {
        const response = await fetch(`${API_URL}/fornecedores`);
        const data = await response.json();
        
        renderFornecedores(data);
    } catch (error) {
        console.error('Erro ao carregar fornecedores:', error);
        elements.fornecedoresList.innerHTML = '<p>Erro ao carregar fornecedores</p>';
    }
}

function renderEventos(eventos) {
    if (!eventos || eventos.length === 0) {
        elements.resultsGrid.innerHTML = `
            <div class="empty-state">
                <h3>Sistema de Inteligência Ativo</h3>
                <p>A API está pronta para receber dados normalizados.</p>
                <p>Alimente com dados de contratos, diárias, licitações para ver análises.</p>
            </div>
        `;
        return;
    }
    
    // Renderizar eventos...
}

function renderAnomalias(data) {
    if (!data.anomalias || data.anomalias.length === 0) {
        elements.anomaliasList.innerHTML = `
            <div class="info-box">
                <h4>🔍 Sistema de Detecção de Anomalias</h4>
                <p>O sistema detecta:</p>
                <ul>
                    <li><strong>Fornecedores frequentes</strong> - Empresas com muitos contratos</li>
                    <li><strong>Valores atípicos</strong> - Gastos acima da média</li>
                    <li><strong>Picos temporais</strong> - Concentrados em períodos específicos</li>
                </ul>
                <p class="note">Alimente com dados para ver anomalias detectadas.</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <span class="stat-value">${data.total_anomalias || 0}</span>
                    <span class="stat-label">Anomalias detectadas</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${data.por_tipo?.fornecedor_frequente || 0}</span>
                    <span class="stat-label">Fornecedores frequentes</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${data.por_tipo?.valor_atipico || 0}</span>
                    <span class="stat-label">Valores atípicos</span>
                </div>
            </div>
        `;
        return;
    }
    
    // Renderizar lista de anomalias...
}

function renderFornecedores(data) {
    if (!data.top_10 || data.top_10.length === 0) {
        elements.fornecedoresList.innerHTML = `
            <div class="info-box">
                <h4>🏢 Análise de Fornecedores</h4>
                <p>Quando houver dados, será mostrado:</p>
                <ul>
                    <li>Ranking por valor total</li>
                    <li>Quantidade de contratos</li>
                    <li>Presença em múltiplos órgãos</li>
                    <li>Concentração geográfica</li>
                </ul>
            </div>
        `;
        return;
    }
    
    // Renderizar fornecedores...
}
