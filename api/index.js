const fs = require('fs');
const path = require('path');

// Carregar CSV de portais
let portais = [];
try {
  const csvPath = path.join(process.cwd(), 'data', 'catalogos.csv');
  const csvContent = fs.readFileSync(csvPath, 'utf-8');
  const lines = csvContent.split('\n');
  const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
  
  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim()) {
      const values = lines[i].split(',');
      const portal = {};
      headers.forEach((h, idx) => {
        portal[h] = values[idx] ? values[idx].trim().replace(/"/g, '') : '';
      });
      portais.push(portal);
    }
  }
} catch (e) {
  console.log('Erro ao carregar CSV:', e.message);
}

module.exports = (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json');
  
  const { url } = req;
  
  // Health check
  if (url === '/api/' || url === '/api') {
    return res.status(200).json({
      status: 'online',
      servico: 'Dados Publicos BR API',
      versao: '3.0-node',
      total_portais: portais.length
    });
  }
  
  // Busca
  if (url.startsWith('/api/buscar')) {
    const urlObj = new URL('http://localhost' + url);
    const termo = (urlObj.searchParams.get('q') || '').toLowerCase();
    
    const resultados = portais.filter(p => 
      Object.values(p).some(v => 
        String(v).toLowerCase().includes(termo)
      )
    );
    
    return res.status(200).json({
      termo: termo,
      total: resultados.length,
      portais: resultados.slice(0, 20)
    });
  }
  
  // 404
  return res.status(404).json({ error: 'Endpoint nao encontrado' });
};
