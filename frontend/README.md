# Buscador Dados Públicos BR

Frontend do buscador de portais de dados públicos brasileiros.

## 🚀 Deploy

### Opção 1: Vercel (Recomendado)

```bash
cd frontend
npx vercel
```

### Opção 2: Netlify

Arraste a pasta `frontend` para o Netlify Drop.

### Opção 3: GitHub Pages

1. Ative GitHub Pages nas configurações do repo
2. Selecione pasta `/frontend`

## 🔧 Configuração

Edite `app.js` e altere `API_URL`:

```javascript
const API_URL = 'https://SEU-APP.onrender.com';
```

## 📱 Features

- ✅ Busca tipo Google
- ✅ Filtros por qualidade, categoria, esfera
- ✅ Cards responsivos
- ✅ Estatísticas em tempo real
- ✅ Design moderno (Inter, Tailwind-inspired)
- ✅ Mobile-first

## 🎨 Customização

Cores definidas em `style.css`:
- Primary: #2563eb (azul)
- Success: #10b981 (verde)
- Warning: #f59e0b (laranja)
- Danger: #ef4444 (vermelho)

---

**Nota:** Este frontend é estático e precisa da API rodando para funcionar.
