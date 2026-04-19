-- Schema Baseline - Dados Públicos BR
-- Tabelas para baseline estatístico

-- Tabela de contratos (raw data)
CREATE TABLE IF NOT EXISTS contracts (
    id SERIAL PRIMARY KEY,
    orgao_id TEXT,
    data DATE,
    fornecedor TEXT,
    valor NUMERIC,
    descricao TEXT,
    fonte TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de baseline (resultado agregado)
CREATE TABLE IF NOT EXISTS baselines (
    id SERIAL PRIMARY KEY,
    orgao_id TEXT NOT NULL,
    periodo TEXT DEFAULT '12m',
    contratos_mes_media NUMERIC,
    contratos_mes_mediana NUMERIC,
    fornecedores_unicos INTEGER,
    concentracao_top1 NUMERIC,
    concentracao_top3 NUMERIC,
    valor_mediano NUMERIC,
    valor_maximo NUMERIC,
    gerado_em TIMESTAMP DEFAULT NOW()
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_contracts_orgao ON contracts(orgao_id);
CREATE INDEX IF NOT EXISTS idx_baselines_orgao ON baselines(orgao_id);

-- View para comparar orgao vs baseline
CREATE OR REPLACE VIEW comparacao_baseline AS
SELECT 
    b.orgao_id,
    b.contratos_mes_media as baseline_media,
    b.concentracao_top1 as baseline_concentracao,
    b.fornecedores_unicos as baseline_fornecedores,
    b.valor_mediano as baseline_valor_mediano
FROM baselines b
WHERE b.gerado_em = (
    SELECT MAX(gerado_em) FROM baselines WHERE orgao_id = b.orgao_id
);
