# 📊 Dados Públicos BR v3.0 - Search Engine Real

**Motor de busca de dados públicos brasileiros** - Portais locais + Dados.gov.br

🌐 **Live Demo:** https://dados-publicos-br.vercel.app  
📡 **API:** https://dados-publicos-br.onrender.com

---

## ✨ O que é?

Um **"Google dos dados públicos brasileiros"** que une:
- 🏛️ **30+ portais** de transparência municipais/estaduais
- 📊 **Datasets do dados.gov.br** (API federal em tempo real)
- 🔍 Busca unificada com ranking por relevância

---

## 🎯 Características v3.0

### Backend (API Híbrida)
- ✅ **Busca unificada**: Portais locais + Dados.gov.br
- ✅ **Ranking inteligente**: Score 0-100 por relevância
- ✅ **Dados em tempo real**: Integração CKAN dados.gov.br
- ✅ **CORS habilitado**: Para frontend Vercel
- ✅ **Healthcheck**: /health para monitoramento

### Frontend v2
- ✅ Design tipo Google Dataset Search
- ✅ Cards ricos com score visual
- ✅ Filtros por tipo, qualidade, formato
- ✅ Preview de detalhes
- ✅ Mobile-first

---

## 📊 Dados Disponíveis

| Fonte | Quantidade | Tipo |
|-------|-----------|------|
| Portais Locais | 31 | CSV/JSON/API |
| Dados.gov.br | ∞ (API) | Datasets federais |
| **Total** | **31+** | **Misto** |

---

## 🚀 URLs de Produção

### Frontend (Vercel)
```
https://dados-publicos-br.vercel.app
```

### API (Render)
```
https://dados-publicos-br.onrender.com
```

### Endpoints
```
GET /buscar?q=termo          # Busca híbrida
GET /datasets?q=termo        # Apenas dados.gov.br
GET /catalogo                # Portais locais
GET /health                  # Status
```

---

## 📡 Exemplo de Uso

### Buscar por "saude"
```bash
curl "https://dados-publicos-br.onrender.com/buscar?q=saude"
```

**Resposta:**
```json
{
  "busca": "saude",
  "total_resultados": 15,
  "total_portais": 3,
  "total_datasets": 12,
  "resultados": [
    {"tipo": "dataset", "titulo": "Vacinacao COVID-19", "score": 87},
    {"tipo": "portal", "titulo": "Fortaleza Dados Abertos", "score": 50}
  ]
}
```

---

## 🗂️ Estrutura do Projeto

```
dados-publicos-br/
├── 📊 data/
│   └── catalogos.csv              # 31 portais locais
├── 🐍 scripts/
│   ├── api_hibrida.py           # API v3.0 (produção)
│   ├── dadosgov_crawler.py      # Crawler dados.gov.br
│   └── api_simple.py            # Fallback simples
├── 🎨 frontend/
│   └── v2/                      # Buscador moderno
│       ├── index.html
│       ├── style.css
│       └── app.js
├── requirements.txt             # Python deps
├── Procfile                     # Render config
└── runtime.txt                  # Python 3.11
```

---

## 🚀 Deploy

### Backend (Render)
1. Conecte repo em [render.com](https://render.com)
2. Procfile detectado automaticamente
3. Deploy!

### Frontend (Vercel)
```bash
cd frontend/v2
npx vercel
```

---

## 📝 Changelog

### v3.0 (Atual)
- ✅ Integração dados.gov.br em tempo real
- ✅ Busca híbrida (portais + datasets)
- ✅ Score de relevância
- ✅ Deploy produção

### v2.0
- ✅ Frontend moderno
- ✅ Filtros funcionais
- ✅ Cards responsivos

### v1.0
- ✅ Catálogo de portais
- ✅ Busca básica

---

## 👤 Autor

Criado por [@bcasavilca](https://github.com/bcasavilca)

**Status:** 🟢 Online | v3.0 | Produção

⭐ Star no repo se for útil!
