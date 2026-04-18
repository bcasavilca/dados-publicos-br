# 🚀 Deploy - Dados Públicos BR

## Backend (API)

### Render.com (Recomendado)

1. Acesse https://dashboard.render.com
2. Clique **New** → **Web Service**
3. Conecte com GitHub: `bcasavilca/dados-publicos-br`
4. Configuração:
   - **Name:** `dados-publicos-br`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `cd scripts && python api.py`
5. Clique **Create Web Service**

A API estará disponível em: `https://dados-publicos-br.onrender.com`

---

## Frontend (Vercel)

### Opção 1: CLI

```bash
# No diretório frontend/v2
npx vercel

# Quando perguntar o diretório, digite: ./frontend/v2
```

### Opção 2: Dashboard

1. Acesse https://vercel.com
2. **New Project** → Import from GitHub
3. Selecione: `bcasavilca/dados-publicos-br`
4. **Framework Preset:** Other
5. **Root Directory:** `frontend/v2`
6. **Build Command:** (deixe em branco - site estático)
7. **Output Directory:** `./`
8. Deploy

O frontend estará em: `https://dados-publicos-br.vercel.app`

---

## ⚠️ IMPORTANTE

Antes de deployar, edite o arquivo `frontend/v2/app.js`:

```javascript
// Linha 7 - Mude para URL do seu backend:
const API_URL = 'https://dados-publicos-br.onrender.com';
```

---

## URLs Esperadas

| Componente | URL |
|------------|-----|
| API | `https://dados-publicos-br.onrender.com` |
| Frontend | `https://dados-publicos-br.vercel.app` |
| Busca | `https://dados-publicos-br.vercel.app` |

---

## Testando

```bash
# Teste a API
curl https://dados-publicos-br.onrender.com/buscar?q=saude

# Teste o frontend
# Abra no navegador: https://dados-publicos-br.vercel.app
```

---

## Solução de Problemas

### CORS error no frontend
Adicione no `api.py`:
```python
from flask_cors import CORS
CORS(app)
```

### API não responde
Verifique se o backend está "Live" no Render Dashboard.

### Frontend não carrega
Verifique se o Root Directory está correto: `frontend/v2`

---

Pronto para lançar! 🚀
