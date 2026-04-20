#!/bin/bash
# Verificar valores no banco

psql $DATABASE_URL << 'EOF'
\echo '============================================================'
\echo 'ANALISE DE VALORES - SP Contratos'
\echo '============================================================'

\echo '\nTop 10 maiores contratos:'
SELECT fornecedor, valor, orgao 
FROM sp_contratos 
ORDER BY valor DESC 
LIMIT 10;

\echo '\nEstatísticas gerais:'
SELECT 
    COUNT(*) as total,
    MIN(valor) as minimo,
    MAX(valor) as maximo,
    AVG(valor) as media,
    SUM(valor) as total_gasto
FROM sp_contratos;

\echo '\nDistribuição por faixa:'
SELECT 
    CASE 
        WHEN valor < 100000 THEN 'Até R$ 100k'
        WHEN valor < 1000000 THEN 'R$ 100k - 1M'
        WHEN valor < 10000000 THEN 'R$ 1M - 10M'
        WHEN valor < 100000000 THEN 'R$ 10M - 100M'
        ELSE 'Acima R$ 100M'
    END as faixa,
    COUNT(*) as quantidade,
    SUM(valor) as total
FROM sp_contratos
GROUP BY 1
ORDER BY MIN(valor);

\echo '============================================================'
EOF
