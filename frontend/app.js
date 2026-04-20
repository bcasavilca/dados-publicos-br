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
        // CORRECAO: usar /buscar?q= em vez de /catalogo
        const response = await fetch(`${API_URL}/buscar?q=`);
        const data = await response.json();

        allData = data.portais || [];
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

        filteredData = data.portais || [];

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
    const qualidade = document.getElementById('filterQualidade')?.value;
    const categoria = document.getElementById('filterCategoria')?.value;
    const esfera = document.getElementById('filterEsfera')?.value;

    let resultados = [...filteredData];

    if (qualidade) {
        resultados = resultados.filter(item => item.Qualidade === qualidade);
    }

    if (categoria) {
        resultados = resultados.filter(item =>
            item.Categoria?.toLowerCase() === categoria.toLowerCase()
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
    const qualidadeClass = item
