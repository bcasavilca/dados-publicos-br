-- ESTRUTURA EMPRESARIAL V1.0
-- CNPJ, sócios e relacionamentos ocultos

-- 1. TABELA DE EMPRESAS
DROP TABLE IF EXISTS empresas CASCADE;
CREATE TABLE empresas (
    cnpj TEXT PRIMARY KEY,
    razao_social TEXT NOT NULL,
    nome_fantasia TEXT,
    data_abertura DATE,
    cnae_principal TEXT,
    cnae_secundario TEXT,
    porte TEXT, -- ME, EPP, DEMO, etc
    natureza_juridica TEXT,
    situacao_cadastral TEXT,
    data_situacao_cadastral DATE,
    capital_social NUMERIC(15, 2),
    endereco_uf TEXT,
    endereco_municipio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_empresas_razao ON empresas USING gin (razao_social gin_trgm_ops);
CREATE INDEX idx_empresas_cnae ON empresas(cnae_principal);
CREATE INDEX idx_empresas_data ON empresas(data_abertura);

-- 2. TABELA DE SÓCIOS
DROP TABLE IF EXISTS socios CASCADE;
CREATE TABLE socios (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    documento TEXT, -- CPF (hash opcional por LGPD)
    tipo TEXT CHECK (tipo IN ('PF', 'PJ')) DEFAULT 'PF',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_socios_nome ON socios USING gin (nome gin_trgm_ops);
CREATE INDEX idx_socios_doc ON socios(documento) WHERE documento IS NOT NULL;

-- 3. TABELA DE VÍNCULO EMPRESA-SÓCIO
DROP TABLE IF EXISTS empresa_socio CASCADE;
CREATE TABLE empresa_socio (
    cnpj TEXT,
    socio_id INT,
    percentual NUMERIC(5, 2),
    data_entrada DATE,
    data_saida DATE,
    PRIMARY KEY (cnpj, socio_id),
    FOREIGN KEY (cnpj) REFERENCES empresas(cnpj) ON DELETE CASCADE,
    FOREIGN KEY (socio_id) REFERENCES socios(id) ON DELETE CASCADE
);

CREATE INDEX idx_emp_socio_cnpj ON empresa_socio(cnpj);
CREATE INDEX idx_emp_socio_socio ON empresa_socio(socio_id);

-- 4. TABELA DE MATCHING FORNECEDOR → CNPJ (CRÍTICA)
DROP TABLE IF EXISTS fornecedor_cnpj CASCADE;
CREATE TABLE fornecedor_cnpj (
    id SERIAL PRIMARY KEY,
    fornecedor TEXT NOT NULL, -- Nome como aparece no contrato (sujo)
    cnpj TEXT,
    razao_social_match TEXT, -- Razão social da empresa matched
    score_match NUMERIC(5, 2), -- 0-100, similaridade fuzzy
    status TEXT DEFAULT 'PENDENTE', -- PENDENTE, CONFIRMADO, REVISAR
    metodo TEXT, -- FUZZY, EXATO, MANUAL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cnpj) REFERENCES empresas(cnpj) ON DELETE SET NULL
);

CREATE INDEX idx_fornecedor_cnpj_forn ON fornecedor_cnpj(fornecedor);
CREATE INDEX idx_fornecedor_cnpj_cnpj ON fornecedor_cnpj(cnpj);
CREATE INDEX idx_fornecedor_cnpj_score ON fornecedor_cnpj(score_match);
CREATE INDEX idx_fornecedor_cnpj_status ON fornecedor_cnpj(status);

-- 5. VIEW DE RELACIONAMENTOS SÓCIETÁRIOS
DROP VIEW IF EXISTS vw_relacionamentos_societarios CASCADE;
CREATE VIEW vw_relacionamentos_societarios AS
SELECT
    e1.cnpj AS cnpj_a,
    e1.razao_social AS empresa_a,
    e2.cnpj AS cnpj_b,
    e2.razao_social AS empresa_b,
    s.nome AS socio_nome,
    s.documento AS socio_doc,
    es1.percentual AS percentual_a,
    es2.percentual AS percentual_b,
    1 AS socios_compartilhados,
    -- Score de relacionamento
    CASE
        WHEN es1.percentual >= 50 AND es2.percentual >= 50 THEN 'CONTROLE_MUTUO'
        WHEN es1.percentual >= 50 OR es2.percentual >= 50 THEN 'CONTROLE_UNILATERAL'
        WHEN es1.percentual >= 20 AND es2.percentual >= 20 THEN 'INFLUENCIA_FORTE'
        ELSE 'SOCIEDADE_SIMPLES'
    END AS tipo_relacionamento
FROM empresa_socio es1
JOIN empresa_socio es2 ON es1.socio_id = es2.socio_id AND es1.cnpj < es2.cnpj
JOIN socios s ON s.id = es1.socio_id
JOIN empresas e1 ON e1.cnpj = es1.cnpj
JOIN empresas e2 ON e2.cnpj = es2.cnpj;

-- 6. VIEW DE GRUPOS ECONÔMICOS (CLIQUES DE SÓCIOS)
DROP MATERIALIZED VIEW IF EXISTS vw_grupos_economicos CASCADE;
CREATE MATERIALIZED VIEW vw_grupos_economicos AS
WITH RECURSIVE cadeia AS (
    -- Início: empresas com sócios
    SELECT 
        es1.cnpj,
        es1.socio_id,
        ARRAY[es1.cnpj] AS cadeia_cnpjs,
        ARRAY[es1.socio_id] AS cadeia_socios,
        1 AS nivel
    FROM empresa_socio es1
    
    UNION
    
    -- Recursão: expandir para outras empresas do mesmo sócio
    SELECT
        es2.cnpj,
        es2.socio_id,
        c.cadeia_cnpjs || es2.cnpj,
        c.cadeia_socios || es2.socio_id,
        c.nivel + 1
    FROM cadeia c
    JOIN empresa_socio es2 ON es2.socio_id = c.socio_id
    WHERE NOT es2.cnpj = ANY(c.cadeia_cnpjs)
      AND c.nivel < 5  -- Limitar profundidade
),
grupos AS (
    SELECT
        cadeia_cnpjs,
        array_agg(DISTINCT socio_id) AS socios,
        array_agg(DISTINCT cnpj) AS empresas
    FROM cadeia
    GROUP BY cadeia_cnpjs
)
SELECT
    row_number() OVER () AS grupo_id,
    empresas,
    socios,
    array_length(empresas, 1) AS tamanho
FROM grupos
WHERE array_length(empresas, 1) >= 2
ORDER BY tamanho DESC;

CREATE INDEX idx_grupos_economicos ON vw_grupos_economicos(grupo_id);

-- 7. FUNÇÃO DE SIMILARIDADE (PostgreSQL)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Função para calcular score de similaridade
CREATE OR REPLACE FUNCTION similaridade_nomes(nome1 TEXT, nome2 TEXT)
RETURNS NUMERIC AS $$
BEGIN
    -- Normalização básica
    nome1 := lower(regexp_replace(nome1, '[^a-z0-9]', '', 'g'));
    nome2 := lower(regexp_replace(nome2, '[^a-z0-9]', '', 'g'));
    
    -- Trigram similarity (0-1)
    RETURN similarity(nome1, nome2) * 100;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 8. PROCEDURE DE MATCHING AUTOMÁTICO
CREATE OR REPLACE PROCEDURE match_fornecedores_cnpj(
    min_score NUMERIC DEFAULT 85.0
)
LANGUAGE plpgsql AS $$
DECLARE
    fornec_rec RECORD;
    melhor_match RECORD;
BEGIN
    FOR fornec_rec IN 
        SELECT DISTINCT fornecedor 
        FROM sp_contratos
        WHERE fornecedor NOT IN (SELECT fornecedor FROM fornecedor_cnpj WHERE status = 'CONFIRMADO')
    LOOP
        -- Buscar melhor match
        SELECT 
            cnpj,
            razao_social,
            similaridade_nomes(fornec_rec.fornecedor, razao_social) AS score
        INTO melhor_match
        FROM empresas
        WHERE similaridade_nomes(fornec_rec.fornecedor, razao_social) >= min_score
        ORDER BY similaridade_nomes(fornec_rec.fornecedor, razao_social) DESC
        LIMIT 1;
        
        IF melhor_match IS NOT NULL THEN
            INSERT INTO fornecedor_cnpj (fornecedor, cnpj, razao_social_match, score_match, status, metodo)
            VALUES (
                fornec_rec.fornecedor, 
                melhor_match.cnpj, 
                melhor_match.razao_social,
                melhor_match.score,
                CASE WHEN melhor_match.score >= 95 THEN 'CONFIRMADO' ELSE 'REVISAR' END,
                'FUZZY'
            )
            ON CONFLICT (fornecedor) DO UPDATE SET
                cnpj = EXCLUDED.cnpj,
                razao_social_match = EXCLUDED.razao_social_match,
                score_match = EXCLUDED.score_match,
                status = CASE WHEN EXCLUDED.score_match >= 95 THEN 'CONFIRMADO' ELSE fornecedor_cnpj.status END,
                updated_at = CURRENT_TIMESTAMP;
        ELSE
            -- Sem match - criar registro pendente
            INSERT INTO fornecedor_cnpj (fornecedor, status)
            VALUES (fornec_rec.fornecedor, 'PENDENTE')
            ON CONFLICT DO NOTHING;
        END IF;
    END LOOP;
END;
$$;

-- 9. VIEW DE ALERTAS ESTRUTURAIS
DROP VIEW IF EXISTS vw_alertas_estruturais CASCADE;
CREATE VIEW vw_alertas_estruturais AS
SELECT
    fc.fornecedor,
    fc.cnpj,
    e.razao_social,
    e.data_abertura,
    -- Alerta 1: Empresa nova com contrato grande
    CASE 
        WHEN c.valor > 500000 AND (CURRENT_DATE - e.data_abertura) < 365 
        THEN 'EMPRESA_NOVA_VALOR_ALTO'
        ELSE NULL
    END AS alerta_novidade,
    -- Alerta 2: Sócio com múltiplas empresas
    (SELECT COUNT(DISTINCT es2.cnpj) 
     FROM empresa_socio es1
     JOIN empresa_socio es2 ON es1.socio_id = es2.socio_id
     WHERE es1.cnpj = fc.cnpj AND es2.cnpj <> fc.cnpj
    ) AS qtd_empresas_socio,
    -- Alerta 3: CNAE incompatível (exemplo: empresa de TI fazendo obra)
    e.cnae_principal,
    c.categoria_final AS categoria_contrato,
    CASE
        WHEN e.cnae_principal LIKE '62%' AND c.categoria_final = 'OBRAS' THEN 'CNAE_INCOMPATIVEL'
        WHEN e.cnae_principal LIKE '47%' AND c.categoria_final = 'TECNOLOGIA' THEN 'CNAE_INCOMPATIVEL'
        ELSE NULL
    END AS alerta_cnae
FROM fornecedor_cnpj fc
JOIN empresas e ON fc.cnpj = e.cnpj
JOIN sp_contratos c ON fc.fornecedor = c.fornecedor
WHERE fc.status = 'CONFIRMADO';

-- 10. COMENTÁRIOS E DOCUMENTAÇÃO
COMMENT ON TABLE empresas IS 'Dados cadastrais de empresas (fonte: Receita Federal)';
COMMENT ON TABLE socios IS 'Sócios identificados nas empresas';
COMMENT ON TABLE fornecedor_cnpj IS 'Matching entre nome em contrato e CNPJ real';
COMMENT ON COLUMN fornecedor_cnpj.score_match IS 'Similaridade 0-100. >90 auto, 80-90 revisar, <80 manual';
