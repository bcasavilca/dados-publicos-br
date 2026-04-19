# Guia Railway - Deploy Dados Públicos BR v3.0

## 🚀 Passo a Passo

### 1. No Railway Dashboard

1. Acesse: https://railway.app/dashboard
2. Clique **"New Project"**
3. Escolha **"Deploy from GitHub repo"**
4. Selecione: `bcasavilca/dados-publicos-br`

### 2. Adicionar Serviços

Clique **"New"** → **"Database"** → **"Add PostgreSQL"**

Isso cria automaticamente:
- PostgreSQL com dados de conexão
- Variáveis de ambiente configuradas

### 3. Configurar Deploy

Na aba **"Settings"** do seu serviço:

**Build Command:** (deixar em branco - usa Dockerfile)

**Start Command:**
```
python api_search.py
```

**Port:** `5000`

### 4. Variáveis de Ambiente

Vá em **"Variables"** e adicione:

```
PORT=5000
MEILI_HOST=https://seu-meilisearch.railway.app
MEILI_MASTER_KEY=sua-chave-aqui
```

(Se usar Meilisearch no Railway, adicione como serviço também)

### 5. Deploy

Clique em **"Deploy"** e aguarde!

---

## 📊 URLs após deploy

| Endpoint | Descrição |
|----------|-----------|
| `/` | Status da API |
| `/search?q=termo` | Busca |
| `/search?q=termo&estado=BA` | Busca com filtro |

---

## ⚡ Importante

O Railway oferece:
- ✅ PostgreSQL gratuito (500MB)
- ✅ Deploy automático do GitHub
- ⚠️ Meilisearch precisa ser adicionado separadamente

Ou use versão simplificada sem Meilisearch (busca no PostgreSQL direto).
