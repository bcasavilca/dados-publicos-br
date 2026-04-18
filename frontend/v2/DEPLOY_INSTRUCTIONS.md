# 🚀 Deploy Frontend - Instruções

## URL do Backend (Já Funcionando):
```
https://dados-publicos-br.onrender.com
```

## Deploy Frontend (Vercel):

### Método 1: Dashboard (Mais Fácil)

1. Acesse: https://vercel.com
2. Clique em **"Add New..."** → **"Project"**
3. Importe do GitHub: `bcasavilca/dados-publicos-br`
4. Configure:
   - **Framework Preset:** Other
   - **Root Directory:** `frontend/v2`
   - **Build Command:** (deixe em branco)
   - **Output Directory:** `./`
5. Clique **Deploy**

### Método 2: CLI (Se tiver login)

```bash
npx vercel login
npx vercel --prod
# Selecione: frontend/v2
```

---

## ✅ Depois do Deploy:

Você terá duas URLs:
- **Backend:** https://dados-publicos-br.onrender.com
- **Frontend:** https://SEU-PROJETO.vercel.app

## 🧪 Teste:

1. Acesse o frontend
2. Busque por "saude"
3. Veja resultados (portais + datasets)
4. Clique em cards
5. Abra console (F12) → veja analytics

---

Pronto para lançar! 🎉
