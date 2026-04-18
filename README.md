# 🔍 Dados Públicos BR v3.0

**Motor de busca de dados públicos brasileiros** - Já em produção!

🌐 **Acesse agora:** https://dados-publicos-br.vercel.app  
📡 **API:** https://dados-publicos-br.onrender.com

---

## 📌 Status do Projeto (19/04/2025)

### ✅ Já Funcionando

| Feature | Status | Detalhes |
|---------|--------|----------|
| **Frontend** | 🟢 Online | Design tipo Google Dataset Search |
| **Backend** | 🟢 Online | API REST com busca em tempo real |
| **Buscador** | 🟢 Funcionando | Busca por texto em todos os portais |
| **Filtros** | 🟢 Funcionando | Por tipo, qualidade, formato, score |
| **Score** | 🟢 Visual | Barra de 0-100 em cada resultado |
| **Preview** | 🟢 Modal | Clique em cards para ver detalhes |
| **Analytics** | 🟢 Console | Tracking de buscas e cliques |

---

## 📊 Dados Disponíveis

### Portais Locais
- **40+ portais** catalogados
- **9 estados** do Nordeste
- **Capitais:** Fortaleza, Natal, Recife, Salvador, São Luís, Teresina, Aracaju, João Pessoa, Maceió
- **Cidades médias:** Sobral, Mossoró, Campina Grande, Caruaru, Feira de Santana, Imperatriz, etc.
- **Fontes:** Dados Abertos + Transparência + TCMs

### Dados.gov.br (Em desenvolvimento)
- Integração via API CKAN
- Busca em tempo real de datasets federais
- Score de relevância

---

## 🚀 O Que Já Conseguimos

### 1. Busca Funcional
```
Buscar: "natal"
→ Retorna: Portal da Transparência de Natal, Dados Abertos de Natal, TCM-RN, etc.
```

### 2. Filtros Reais
- ✅ Por tipo (Portal/Dataset)
- ✅ Por qualidade (Alta/Média/Baixa)
- ✅ Por formato (CSV/JSON/API)
- ✅ Por score mínimo (0-100)

### 3. Cards Informativos
Cada resultado mostra:
- 📍 Localização (UF/Cidade)
- 📄 Formato disponível
- ⭐ Score de relevância
- 🔗 Link direto para o portal
- 🏷️ Qualidade da fonte

### 4. Deploy Completo
- ✅ Frontend no Vercel (CDN global)
- ✅ Backend no Render (API REST)
- ✅ Domínio próprio configurado
- ✅ CORS habilitado
- ✅ SSL/HTTPS em todos os serviços

---

## 🛠️ Arquitetura Técnica

```
Frontend (Vercel)
    ↓ HTTP
Backend (Render)
    ↓ CSV Local + API dados.gov.br
Dados
```

**Tecnologias:**
- Frontend: HTML/CSS/JS vanilla
- Backend: Python + Flask
- Deploy: Vercel + Render
- Versionamento: Git + GitHub

---

## 📈 Próximos Passos (Roadmap)

### Fase 3 (Em andamento)
- [ ] Integração completa dados.gov.br
- [ ] Cache de resultados
- [ ] Preview de datasets

### Fase 4 (Futuro)
- [ ] Indexação em SQLite (busca mais rápida)
- [ ] Ranking inteligente (TF-IDF)
- [ ] Analytics de uso real
- [ ] Expansão para Sudeste/Sul/Norte

---

## 👤 Sobre

Criado por: **Bruno Casavilca** (@bcasavilca)  
Data de início: Abril/2025  
Status: **🟢 Online e evoluindo**

---

## 🤝 Como Usar

### Web
1. Acesse: https://dados-publicos-br.vercel.app
2. Digite um termo (ex: "ce", "natal", "saude")
3. Explore os resultados
4. Clique em "Acessar" para ir ao portal

### API
```bash
# Buscar portais
GET https://dados-publicos-br.onrender.com/buscar?q=ce

# Ver status
GET https://dados-publicos-br.onrender.com/health
```

---

**Última atualização:** 19/04/2025  
**Versão:** v3.0  
**Status:** 🟢 Produção ativa

⭐ Star no repo se for útil!
