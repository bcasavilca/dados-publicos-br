# 📊 Dados Publicos BR

Catalogo unificado de dados publicos brasileiros.

## 🎯 Objetivo

Facilitar o acesso a dados publicos brasileiros, incluindo:
- **Dados abertos** (portais CKAN, APIs)
- **Transparencia** (portais da transparencia)
- **Fontes com scraping** necessario

## 📁 Estrutura do Projeto

```
dados-publicos-br/
├── data/
│   └── catalogos.csv           # Dataset principal
├── scripts/
│   ├── classify.py             # Classificacao automatica de URLs
│   ├── validate.py             # Validacao de links
│   ├── api.py                  # API REST
│   └── scrapers/               # Scrapers especificos
├── .github/
│   └── workflows/
│       └── validate.yml        # GitHub Actions
└── README.md
```

## 🏷️ Classificacao de Qualidade

| Nivel | Descricao | Exemplos |
|-------|-----------|----------|
| **Alta** | API REST ou download direto CSV/JSON | dados.al.gov.br |
| **Media** | Download manual, formatos estruturados | XLS, ODS |
| **Baixa** | Scraping necessario, PDFs | Portais de transparencia |

## 🚀 Como Usar

### 1. Instalar dependencias

```bash
pip install flask pandas requests
```

### 2. Rodar API local

```bash
python scripts/api.py
```

Acesse: http://localhost:5000/catalogo

### 3. Validar links

```bash
python scripts/validate.py
```

### 4. Classificar nova URL

```bash
python scripts/classify.py
```

## 📡 Endpoints da API

| Endpoint | Descricao | Exemplo |
|----------|-----------|---------|
| `/` | Info da API | - |
| `/catalogo` | Lista todos | - |
| `/catalogo/uf/{uf}` | Por estado | `/catalogo/uf/CE` |
| `/catalogo/qualidade/{nivel}` | Por qualidade | `/catalogo/qualidade/Alta` |
| `/estatisticas` | Estatisticas gerais | - |

## 📝 Contribuindo

Para adicionar novo portal:

1. Adicione linha em `data/catalogos.csv`
2. Execute `python scripts/validate.py` para verificar
3. Abra Pull Request

### Formato do CSV

```csv
Titulo,URL,Municipio,UF,Esfera,Poder,TipoFonte,TipoAcesso,Formato,Qualidade,Atualizacao
```

## 🔍 Fontes Principais (Nordeste)

| Portal | UF | Tipo | Qualidade |
|--------|-----|------|-----------|
| Alagoas em Dados | AL | Dados Abertos | Alta |
| Fortaleza Dados Abertos | CE | Dados Abertos | Alta |
| TCM-CE | CE | API | Alta |
| Recife Dados Abertos | PE | Dados Abertos | Alta |
| Transparencia Natal | RN | Scraping | Baixa |

## 🤖 Automacao

GitHub Actions verifica links automaticamente a cada push.

## 📜 Licenca

Dados publicos - Uso livre para fins jornalisticos e academicos.

## 👤 Autor

Criado por @bcasavilca

---

**Status:** 🟢 Em desenvolvimento ativo
