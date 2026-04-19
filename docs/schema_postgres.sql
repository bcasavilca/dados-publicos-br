-- Schema PostgreSQL - Dados Públicos BR v3.0
-- Infraestrutura de busca com PostgreSQL + Meilisearch

-- Tabela de fontes de dados
CREATE TABLE fontes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    url VARCHAR(500),
    tipo VARCHAR(50), -- 'api', 'csv', 'portal'
    confiabilidade INTEGER DEFAULT 5, -- 1-10
    ultima_coleta TIMESTAMP,
    status VARCHAR(50) DEFAULT 'ativo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela raw (dados brutos)
CREATE TABLE raw_data (
    id SERIAL PRIMARY KEY,
    fonte_id INTEGER REFERENCES fontes(id),
    tipo VARCHAR(100), -- 'dataset', 'portal', 'documento'
    payload_json JSONB NOT NULL,
    hash VARCHAR(64), -- para evitar duplicatas
    coletado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela documents (dados normalizados)
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    raw_id INTEGER REFERENCES raw_data(id),
    
    -- Campos normalizados
    titulo VARCHAR(500),
    descricao TEXT,
    orgao VARCHAR(255),
    estado VARCHAR(2), -- UF: BA, SP, CE
    tipo VARCHAR(100),
    categoria VARCHAR(100),
    url VARCHAR(1000),
    formato VARCHAR(50), -- CSV, JSON, API, XLS
    
    -- Metadados
    fonte VARCHAR(100),
    fonte_nome VARCHAR(255),
    fonte_url VARCHAR(500),
    atualizado_em TIMESTAMP,
    score_base FLOAT DEFAULT 0.5,
    
    -- Busca
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('portuguese', 
            coalesce(titulo, '') || ' ' || 
            coalesce(descricao, '') || ' ' ||
            coalesce(orgao, '')
        )
    ) STORED,
    
    -- Controle
    indexed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_documents_search ON documents USING GIN(search_vector);
CREATE INDEX idx_documents_estado ON documents(estado);
CREATE INDEX idx_documents_tipo ON documents(tipo);
CREATE INDEX idx_documents_fonte ON documents(fonte);
CREATE INDEX idx_raw_data_fonte ON raw_data(fonte_id);

-- Tabela de jobs (controle de ingestão)
CREATE TABLE ingest_jobs (
    id SERIAL PRIMARY KEY,
    fonte_id INTEGER REFERENCES fontes(id),
    tipo VARCHAR(50), -- 'dadosgov', 'ibge', 'tse', 'manual'
    status VARCHAR(50) DEFAULT 'pendente', -- pendente, rodando, sucesso, erro
    registros_coletados INTEGER DEFAULT 0,
    registros_novos INTEGER DEFAULT 0,
    erro_msg TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

-- Tabela de métricas
CREATE TABLE search_metrics (
    id SERIAL PRIMARY KEY,
    query VARCHAR(500),
    resultados INTEGER,
    tempo_ms INTEGER,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- View para dados não indexados
CREATE VIEW documents_nao_indexados AS
SELECT * FROM documents WHERE indexed = FALSE;

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Inserir fontes padrão
INSERT INTO fontes (nome, url, tipo, confiabilidade) VALUES
('dados.gov.br', 'https://dados.gov.br', 'api', 10),
('IBGE', 'https://servicodados.ibge.gov.br', 'api', 10),
('TSE', 'https://dadosabertos.tse.jus.br', 'api', 9),
('Portal Transparência', 'https://portaldatransparencia.gov.br', 'api', 10),
('Portais CSV Manual', NULL, 'csv', 8);
