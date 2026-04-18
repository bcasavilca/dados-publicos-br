# Dados Públicos BR - Frontend v2

**Experiência tipo Google Dataset Search** para busca de dados públicos brasileiros.

## ✨ Features

### 🎯 UX de Busca
- **Autocomplete** com buscas rápidas
- **Loading state** com spinner
- **Empty state** explicativo
- **No results** com ações

### 📊 Cards de Resultado
Cada card mostra:
- 🏷️ Tipo (📊 Dataset / 🏛️ Portal)
- ⭐ Score (0-100) com barra visual
- 🏷️ Qualidade (Alta/Média/Baixa)
- 📄 Formato
- 📍 Localização/Organização
- 🖱️ Clique para preview

### 🔍 Filtros Reais (Funcionais)
- **Tipo:** Portais, Datasets
- **Qualidade:** Alta, Média, Baixa
- **Formato:** CSV, JSON, API, XLS/PDF
- **Score:** Range slider (0-100)

### 📋 Ordenação
- Por relevância (score)
- Por qualidade
- Por nome

### 🖼️ Preview Modal
Clique em qualquer card para ver detalhes completos.

---

## 🚀 Deploy

### Local
```bash
cd frontend/v2
python -m http.server 3000
# Acesse: http://localhost:3000
```

### Vercel (Recomendado)
```bash
cd frontend/v2
npx vercel
```

### Netlify
Arraste a pasta `v2` para o [Netlify Drop](https://app.netlify.com/drop).

---

## 🔧 Configuração

Edite `app.js` linha 7 para apontar sua API:

```javascript
const API_URL = 'https://dados-publicos-br.onrender.com';
```

---

## 📱 Design

- **Mobile-first** (responsive)
- **Inter** font (Google Fonts)
- **Design system** consistente
- **Acessibilidade** básica

---

## 🎯 Comparação: v1 vs v2

| Aspecto | v1 | v2 |
|---------|-----|-----|
| Cards | Simples | Rico em info |
| Filtros | Dropdowns | Checkboxes funcionais |
| Score | Não mostrava | Barra visual + número |
| Preview | Não tinha | Modal completo |
| UX | Catálogo | Descoberta |

---

## 🧠 Mentalidade

**v1:** "Lista de portais"
**v2:** "Motor de busca de dados"

---

Feito por [@bcasavilca](https://github.com/bcasavilca)
