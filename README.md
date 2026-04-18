# 📊 Dados Publicos BR v2.0

Catalogo unificado e motor de busca de dados publicos brasileiros.

## 🎯 Objetivo

Facilitar o acesso a dados publicos brasileiros atraves de:
- **Catalogo centralizado** de portais (dados abertos + transparencia)
- **API REST** para consulta programatica
- **Motor de busca** tipo Google
- **Ranking de qualidade** dos portais
- **Validacao automatica** de links

## 📊 Estatisticas Atuais

- **30+ portais** catalogados
- **26 estados/UFs** cobertos
- **Nordeste completo** (AL, BA, CE, MA, PB, PE, PI, RN, SE)
- **Sudeste parcial** (SP, MG, RJ)
- **Sul** (RS, SC, PR)
- **Centro-Oeste** (GO, DF)

## 📁 Estrutura

```
dados-publicos-br/
├── 📊 data/
│   └── catalogos.csv           # 30+ portais catalogados
├── 🐍 scripts/
│   ├── api.py                  # API REST completa
│   ├── classify.py             # Classificacao automatica
│   ├── detect_ckan.py          # Detector de portais CKAN
│   ├── validate.py             # Validador de links
│   └── scrapers/               # Scrapers especificos
├── ⚙️ .github/workflows/
│   └── validate.yml            # CI/CD
└── 📘 README.md
```

## 🏷️ Classificacao de Qualidade

| Nivel | Descricao | Criterios |
|-------|-----------|-----------|
| **Alta** | API REST ou download direto | JSON/CSV, CKAN, API documentada |
| **Media** | Download manual, formatos estruturados | XLS, ODS, API limitada |
| **Baixa** | Scraping necessario ou PDFs | HTML, PDF, acesso restrito |

## 🚀 Como Usar

### 1. Instalar dependencias

```bash
pip install flask pandas requests
```

### 2. Rodar API local

```bash
python scripts/api.py
```

### 3. Testar endpoints

```bash
# Lista todos os portais
curl http://localhost:5000/catalogo

# Busca tipo Google
curl "http://localhost:5000/buscar?q=saude"

# Melhores portais
curl http://localhost:5000/ranking

# Filtra por estado
curl http://localhost:5000/catalogo/uf/CE

# Estatisticas
curl http://localhost:5000/estatisticas
```

## 📡 Endpoints da API

### Consulta

| Endpoint | Descricao | Exemplo |
|----------|-----------|---------|
| `GET /` | Info da API | - |
| `GET /catalogo` | Lista todos | `/catalogo?uf=CE&qualidade=Alta` |
| `GET /catalogo/uf/{uf}` | Por estado | `/catalogo/uf/SP` |
| `GET /catalogo/qualidade/{nivel}` | Por qualidade | `/catalogo/qualidade/Alta` |
| `GET /catalogo/categoria/{cat}` | Por categoria | `/catalogo/categoria/Financas` |

### Busca & Analytics

| Endpoint | Descricao | Exemplo |
|----------|-----------|---------|
| `GET /buscar?q={termo}` | Busca livre | `/buscar?q=transparencia` |
| `GET /ranking` | Ranking por qualidade | - |
| `GET /estatisticas` | Dados agregados | - |
| `GET /estados` | Lista estados | - |

## 📊 Exemplos de Resposta

### Buscar

```json
{
  "busca": "saude",
  "total_resultados": 3,
  "resultados": [
    {
      "Titulo": "Portal da Transparencia Salvador",
      "UF": "BA",
      "Categoria": "Saude"
    }
  ]
}
```

### Ranking

```json
{
  "total_portais": 30,
  "ranking": {
    "alta": [...],
    "media": [...], 
    "baixa": [...]
  }
}
```

## 🤖 Automacao

### Detector CKAN

```bash
python scripts/detect_ckan.py
```

Detecta automaticamente portais que usam plataforma CKAN.

### Validador de Links

```bash
python scripts/validate.py
```

Verifica se todos os portais estao respondendo.

### GitHub Actions

Validacao automatica toda segunda-feira 9h.

## 📝 Contribuindo

Para adicionar novo portal, edite `data/catalogos.csv`:

```csv
Titulo,URL,Municipio,UF,Esfera,Poder,TipoFonte,TipoAcesso,Formato,Qualidade,Atualizacao,Categoria
```

**Categorias disponiveis:** Geral, Financas, Saude, Educacao, Transporte, Legislativo

## 🗺️ Cobertura Geografica

### Nordeste (Completo)
- ✅ Alagoas, Bahia, Ceara, Maranhao, Paraiba, Pernambuco, Piaui, Rio Grande do Norte, Sergipe

### Sudeste (Parcial)
- ✅ Sao Paulo (capital + estado)
- ✅ Minas Gerais (capital + estado)
- ✅ Rio de Janeiro (capital + estado)

### Sul
- ✅ Rio Grande do Sul
- ✅ Santa Catarina
- ✅ Parana

### Centro-Oeste
- ✅ Distrito Federal
- ✅ Goias

## 🎯 Proximos Passos

- [ ] Adicionar estados faltantes (AC, AM, AP, MS, MT, PA, RO, RR, TO)
- [ ] Criar scrapers automatizados
- [ ] Painel web (dashboard)
- [ ] Deploy em servidor (Render/Railway)
- [ ] Cache de respostas
- [ ] Rate limiting

## 🔥 Deploy

Para deploy em producao (Render/Railway):

```bash
# requirements.txt
flask==3.0.0
pandas==2.1.4
requests==2.31.0

# Procfile
web: python scripts/api.py
```

## 📜 Licenca

Dados publicos - Uso livre para fins jornalisticos, academicos e civic tech.

## 👤 Autor

Criado por @bcasavilca | Open Source | v2.0

---

**Status:** 🟢 Production Ready | 30+ portais | API v2.0 ativa

**Deploy:** [Seu-URL-aqui.com] (em breve)
