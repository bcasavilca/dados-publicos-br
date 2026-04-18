# 📊 Dados Públicos BR v2.2

**Buscador de portais de dados públicos brasileiros** - API + Frontend moderno

🌐 **Live Demo:** [dados-publicos-br.vercel.app](https://dados-publicos-br.vercel.app) *(em breve)*  
📡 **API:** [dados-publicos-br.onrender.com](https://dados-publicos-br.onrender.com) *(em breve)*

---

## ✨ O que é?

Um **"Google dos dados públicos brasileiros"** que cataloga:
- Portais de dados abertos (CKAN, APIs)
- Portais de transparência
- Fontes que precisam de scraping

---

## 🎯 Características

### Backend (API REST)
- ✅ **30+ portais** catalogados
- ✅ **26 estados** cobertos
- ✅ Busca tipo Google (`/buscar?q=termo`)
- ✅ Ranking por qualidade
- ✅ Cache + healthcheck
- ✅ Métricas em tempo real

### Frontend (Buscador)
- ✅ Design moderno (Inter font, glassmorphism)
- ✅ Filtros por qualidade, categoria, esfera
- ✅ Cards responsivos
- ✅ Estatísticas visuais
- ✅ Mobile-first

---

## 📊 Estatísticas

| Métrica | Valor |
|---------|-------|
| Portais | 30+ |
| Estados | 26 |
| Alta Qualidade | 14 (47%) |
| Nordeste | Completo (9 estados) |
| Sudeste | 3 estados |
| Sul | 3 estados |
| Centro-Oeste | 2 estados |

---

## 🚀 Quick Start

### Backend (API)

```bash
pip install -r requirements.txt
python scripts/api.py

# Acesse: http://localhost:5000
```

### Frontend (Buscador)

```bash
cd frontend
npx serve

# Acesse: http://localhost:3000
```

---

## 📡 Endpoints da API

### Busca
```bash
GET /buscar?q=saude          # Busca tipo Google
GET /catalogo                  # Lista todos
GET /ranking                   # Ranking qualidade
GET /estatisticas              # Métricas
```

### Filtros
```bash
GET /catalogo/uf/CE
GET /catalogo/qualidade/Alta
GET /catalogo/categoria/Financas
```

### Observabilidade
```bash
GET /health                    # Healthcheck
GET /metrics                   # Métricas
```

---

## 🗂️ Estrutura

```
dados-publicos-br/
├── 📊 data/
│   └── catalogos.csv            # 30+ portais
├── 🐍 scripts/
│   ├── api.py                   # API Flask v2.2
│   ├── classify.py              # Classificador
│   ├── detect_ckan.py           # Detector CKAN
│   └── validate.py              # Validador links
├── 🎨 frontend/
│   ├── index.html               # Buscador
│   ├── app.js                   # Lógica JS
│   ├── style.css                # Design system
│   └── package.json             # Vercel config
├── ⚙️ .github/
│   └── workflows/
│       └── validate.yml         # CI/CD
├── requirements.txt             # Python deps
├── Procfile                     # Render config
├── render.yaml                  # Deploy config
└── README.md                    # Este arquivo
```

---

## 🎨 Design System

### Cores Qualidade
- **Alta:** Verde (#059669) - API/CSV
- **Média:** Amarelo (#d97706) - Download
- **Baixa:** Vermelho (#dc2626) - Scraping

### Fonte
- **Inter** (Google Fonts)

---

## 🚀 Deploy

### Backend (Render)
1. Conecte repo em [render.com](https://render.com)
2. Configuração automática (`render.yaml`)
3. Deploy!

### Frontend (Vercel)
```bash
cd frontend
npx vercel
```

Ou use Netlify/GitHub Pages.

---

## 📝 Contribuindo

Para adicionar portal, edite `data/catalogos.csv`:

```csv
Titulo,URL,Municipio,UF,Esfera,Poder,TipoFonte,TipoAcesso,Formato,Qualidade,Atualizacao,Categoria
```

**Categorias:** Geral, Financas, Saude, Educacao, Transporte, Legislativo

---

## 🗺️ Cobertura

```
✅ Nordeste: AL, BA, CE, MA, PB, PE, PI, RN, SE
✅ Sudeste: SP, MG, RJ
✅ Sul: RS, SC, PR
✅ Centro-Oeste: GO, DF
❌ Norte: (em breve)
❌ Médio-Oeste: MS, MT (em breve)
```

---

## 🔮 Roadmap

- [ ] Adicionar Norte e Centro-Oeste
- [ ] Integrar datasets reais (dados.gov.br)
- [ ] Autocomplete na busca
- [ ] Dashboard com gráficos
- [ ] Scrapers automatizados
- [ ] Cache distribuído (Redis)

---

## 💡 Uso

### Exemplo: Buscar todos os portais de saúde

```javascript
fetch('https://api.dadospublicosbr.com/buscar?q=saude')
  .then(r => r.json())
  .then(data => console.log(data.resultados))
```

---

## 📜 Licença

Dados públicos - Uso livre para fins jornalísticos, acadêmicos e civic tech.

---

## 👤 Autor

Criado por [@bcasavilca](https://github.com/bcasavilca) | Open Source | v2.2

---

**Status:** 🟢 Production Ready | API v2.2 | Frontend v1.0

⭐ Star no repo se for útil!
