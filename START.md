# Guia Rápido - Infraestrutura de Busca v3.0

## 🚀 Iniciar tudo (Docker)

```bash
cd dados-publicos-br

# 1. Subir PostgreSQL + Meilisearch
docker-compose up -d

# 2. Criar banco
docker-compose exec postgres psql -U postgres -d dados_publicos -f /docker-entrypoint-initdb.d/01-schema.sql
```

## 📥 Ingestão de dados

```bash
# Ingestão automática (dados.gov.br)
python scripts/ingest.py dadosgov saude 100

# Ingestão manual (CSV de portais)
python scripts/ingest.py csv data/catalogos.csv
```

## 🔍 Indexar para busca

```bash
# Indexar documentos no Meilisearch
python scripts/indexador.py sync

# Buscar teste
python scripts/indexador.py buscar "saude bahia"
```

## 🌐 Iniciar API

```bash
# API de busca
python api_search.py

# Acesse: http://localhost:5000/search?q=termo
```

## 📊 URLs

| Serviço | URL | Descrição |
|---------|-----|-----------|
| PostgreSQL | `localhost:5432` | Banco de dados |
| Meilisearch | `localhost:7700` | Motor de busca |
| Adminer | `localhost:8080` | Painel PostgreSQL |
| API | `localhost:5000` | Busca via HTTP |

---

## ⚡ Comando único (tudo de uma vez)

```bash
# Subir infra + ingerir + indexar + iniciar API
./start.sh
```
