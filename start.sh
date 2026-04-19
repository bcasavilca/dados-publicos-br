#!/bin/bash
# Start completo - Dados Públicos BR v3.0

echo "=========================================="
echo "INICIANDO INFRAESTRUTURA v3.0"
echo "=========================================="

# 1. Docker
echo "→ Subindo PostgreSQL + Meilisearch..."
docker-compose up -d
sleep 5

# 2. Ingestão
echo "→ Ingerindo dados..."
python scripts/ingest.py dadosgov "" 200

# 3. Indexação
echo "→ Indexando no Meilisearch..."
python scripts/indexador.py sync

# 4. API
echo "→ Iniciando API..."
echo ""
echo "=========================================="
echo "PRONTO! Acesse: http://localhost:5000"
echo "=========================================="
python api_search.py
