// Configuracao da API
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000' 
    : 'https://dados-publicos-br-catalogo.onrender.com/api';

// Cache de dados
let allData = [];
let filteredData = [];

// Inicializacao
document.addEventListener('DOMContentLoaded', () => {
    carregarDados();
    
    // Enter no input dispara busca
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') buscar();
    });
});

// Carregar todos os dados
async function carregarDados() {
    mostrarLoading(true);
    
    try {
        const response = await fetch(`${API_URL}/catalogo`);
        const data = await response.json();
        
        allData = data.resultados || [];
        filteredData = [...allData];
        
        atualizarEstatisticas();
        renderizarResultados(filteredData);
        
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
        mostrarErro('Erro ao carregar dados. Verifique se a API está rodando.');
    } finally {
        mostrarLoading(false);
    }
}

// Busca por termo
async function buscar() {
    const termo = document.getElementById('searchInput').value.trim();
    
    if (!termo) {
        filteredData = [...allData];
        renderizarResultados(filteredData);
        return;
    }
    
    mostrarLoading(true);
    
    try {
        const response = await fetch(`${API_URL}/buscar?q=${encodeURIComponent(termo)}`);
        const data = await response.json();
        
        filteredData = data.resultados || [];
        
        // Aplicar filtros visuais tambem
        filtrar();
        
    } catch (error) {
        console.error('Erro na busca:', error);
        // Fallback: busca local
        buscaLocal(termo);
    } finally {
        mostrarLoading(false);
    }
}

// Busca local (fallback)
function buscaLocal(termo) {
    const termoLower = termo.toLowerCase();
    
    filteredData = allData.filter(item => {
        return Object.values(item).some(val => 
            String(val).toLowerCase().includes(termoLower)
        );
    });
    
    filtrar();
}

// Filtrar por qualidade, categoria, esfera
function filtrar() {
    const qualidade = document.getElementById('filterQualidade').value;
    const categoria = document.getElementById('filterCategoria').value;
    const esfera = document.getElementById('filterEsfera').value;
    
    let resultados = [...filteredData];
    
    if (qualidade) {
        resultados = resultados.filter(item => item.Qualidade === qualidade);
    }
    
    if (categoria) {
        resultados = resultados.filter(item => 
            item.Categoria.toLowerCase() === categoria.toLowerCase()
        );
    }
    
    if (esfera) {
        resultados = resultados.filter(item => item.Esfera === esfera);
    }
    
    renderizarResultados(resultados);
}

// Renderizar cards
function renderizarResultados(dados) {
    const grid = document.getElementById('resultsGrid');
    const noResults = document.getElementById('noResults');
    
    if (dados.length === 0) {
        grid.innerHTML = '';
        noResults.style.display = 'block';
        return;
    }
    
    noResults.style.display = 'none';
    
    grid.innerHTML = dados.map(item => criarCard(item)).join('');
}

// Criar HTML do card
function criarCard(item) {
    const qualidadeClass = item.Qualidade.toLowerCase();
    const uf = item.UF || 'BR';
    
    return `
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    ${item.Titulo}
                </div>
                <div class="card-badges">
                    <span class="badge badge-uf">${uf}</span>
                    <span class="badge badge-qualidade badge-${qualidadeClass}">
                        ${item.Qualidade}
                    </span>
                </div>
            </div>
            
            <div class="card-body">
                <div class="card-meta">
                    <span class="meta-item">🏛️ ${item.Esfera}</span>
                    <span class="meta-item">🏛️ ${item.Poder}</span>
                    <span class="meta-item">🏷️ ${item.Categoria}</span>
                </div>
                
                <div class="card-type">
                    📡 ${item.TipoAcesso} | 📄 ${item.Formato}
                </div>
                
                <div class="card-update">
                    🕐 Atualização: ${item.Atualizacao}
                </div>
            </div>
            
            <div class="card-actions">
                <a href="${item.URL}" target="_blank" class="btn btn-primary">
                    Acessar Portal →
                </a>
            </div>
        </div>
    `;
}

// Atualizar estatisticas
function atualizarEstatisticas() {
    document.getElementById('statTotal').textContent = allData.length;
    
    const ufs = new Set(allData.map(item => item.UF));
    document.getElementById('statUFs').textContent = ufs.size;
    
    const altaQualidade = allData.filter(item => item.Qualidade === 'Alta').length;
    document.getElementById('statAlta').textContent = altaQualidade;
}

// Mostrar/ocultar loading
function mostrarLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

// Mostrar erro
function mostrarErro(mensagem) {
    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = `
        <div class="error-message">
            ⚠️ ${mensagem}
        </div>
    `;
}

// Modal API
function mostrarAPI() {
    document.getElementById('apiModal').style.display = 'flex';
}

function fecharAPI() {
    document.getElementById('apiModal').style.display = 'none';
}

// Fechar modal ao clicar fora
window.onclick = function(event) {
    const modal = document.getElementById('apiModal');
    if (event.target === modal) {
        fecharAPI();
    }
}
