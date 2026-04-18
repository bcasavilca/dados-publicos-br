# 🔍 Dados Públicos BR v3.1

**Motor de busca de dados públicos brasileiros** - 86 portais catalogados!

🌐 **Acesse:** https://dados-publicos-br.vercel.app  
📡 **API:** https://dados-publicos-br.onrender.com

---

## 📊 Cobertura Nacional (86 Portais)

| Região | Portais | Principais Estados |
|--------|---------|-------------------|
| 🌵 **Nordeste** | 45+ | CE, RN, PB, PE, BA, SE, MA, PI, AL |
| 🏙️ **Sudeste** | 15+ | SP, MG, RJ |
| 🌲 **Sul** | 10+ | PR, SC, RS |
| ⭐ **Centro-Oeste** | 8+ | GO, MT, MS, DF |
| 🌳 **Norte** | 8+ | PA, AM, AC, RO, RR, AP, TO |

---

## 🎯 Funcionalidades

### ✅ Busca Híbrida
- Portais de transparência municipais/estaduais
- Dados Abertos (CSV, JSON, API)
- Score de relevância (0-100)

### ✅ Modo Exploração
- Navegação por estado
- Filtros por categoria
- Ranking de qualidade

### ✅ API de Inteligência
- `/buscar?q=termo` - Busca em portais
- `/anomalias` - Detecção de padrões
- `/eventos` - Dados normalizados
- `/fornecedores` - Análise de fornecedores

---

## 📡 Endpoints

```
GET /buscar?q=saude           # Busca por termo
GET /anomalias                # Anomalias detectadas
GET /eventos?q=termo          # Eventos financeiros
GET /fornecedores             # Análise de fornecedores
GET /catalogo                 # Lista todos os portais
GET /health                   # Status da API
```

---

## 🛠️ Tecnologia

- **Frontend:** HTML/CSS/JS vanilla (Vercel)
- **Backend:** Python + Flask (Render)
- **Dados:** CSV (86 portais catalogados)
- **Deploy:** Git + GitHub

---

## 👤 Autor

**Bruno Casavilca** (@bcasavilca)

**Status:** 🟢 Online | v3.1 | 86 portais | Cobertura nacional

---

⭐ Star no repo se for útil!
