# 🔄 Como Atualizar Dados Após Correções

Este guia explica como atualizar o sistema quando receber uma correção de URL.

---

## 📋 Passo a Passo

### 1. Receber Correção

Quando alguém reportar uma URL incorreta via:
- Issue no GitHub
- Pull Request
- Comentário em `CORRECOES_URLS.md`

Você receberá:
- Nome do portal
- URL atual (incorreta)
- URL correta
- Estado (UF)

---

### 2. Atualizar no CSV

Edite o arquivo `data/catalogos.csv`:

```bash
# Encontre a linha do portal
# Altere a URL antiga para a nova
# Salve o arquivo
```

Exemplo:
```csv
# Antes:
Portal da Transparencia Maceio,https://www.maceio.al.gov.br/transparencia/,...

# Depois:
Portal da Transparencia Maceio,https://www.transparencia.maceio.al.gov.br/transparencia/pages/homepage.faces,...
```

---

### 3. Atualizar no Banco de Dados (Railway)

Acesse o endpoint de correção:

```
https://web-production-64ea5.up.railway.app/corrigir-maceio
```

Ou atualize manualmente:

1. Acesse: https://railway.app/dashboard
2. Clique no serviço **"Postgres"**
3. Vá na aba **"Query"** (ou **"Connect"**)
4. Execute SQL:

```sql
UPDATE documents 
SET url = 'https://url-nova.gov.br'
WHERE titulo ILIKE '%nome-do-portal%'
  AND url = 'https://url-antiga.gov.br';
```

---

### 4. Commit e Push

```bash
git add data/catalogos.csv
git commit -m "fix: URL correta do portal [Nome]"
git push origin main
```

---

### 5. Atualizar GitHub Pages

O frontend no GitHub Pages atualiza automaticamente quando você faz push.

Aguarde 1-2 minutos e verifique:
```
https://bcasavilca.github.io/dados-publicos-br/
```

---

## ⚡ Comando Rápido (Atualização Completa)

Se precisar atualizar tudo de uma vez:

```bash
# 1. Reimportar CSV
https://web-production-64ea5.up.railway.app/importar-csv

# 2. Limpar banco e reimportar (cuidado!)
# Ou execute SQL no Railway:
TRUNCATE TABLE documents;
-- Depois acesse /importar-csv
```

---

## 📊 Verificar se Funcionou

1. Busque o portal no frontend: `https://bcasavilca.github.io/dados-publicos-br/`
2. Clique no link "Acessar"
3. Verifique se abre a página correta

---

## 🎯 Checklist

- [ ] URL corrigida no CSV (`data/catalogos.csv`)
- [ ] URL corrigida no banco (Railway)
- [ ] Commit enviado para GitHub
- [ ] Frontend atualizado (GitHub Pages)
- [ ] Testado e funcionando
- [ ] Issue fechada (se veio de issue)

---

## 📞 Precisa de Ajuda?

Abra uma issue no GitHub ou consulte a documentação em `docs/`.

---

*Última atualização: 19/04/2026*
