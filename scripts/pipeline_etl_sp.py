#!/usr/bin/env python3
"""
Pipeline ETL - SP Contratos para PostgreSQL
CSV (SP) -> Download -> Parse -> Clean -> Normalize -> PostgreSQL
"""

import os
import sys
import requests
import pandas as pd
import psycopg2
from io import StringIO
import re

# Configuracoes
CSV_URL = 'https://dados.prefeitura.sp.gov.br/dataset/6588aef7-20ff-4cec-b1e1-6c06520240c0/resource/fd48b7dd-c5f1-4352-963f-f1e5ebc6d61b/download/contratos.csv'

# PostgreSQL (Railway)
DB_CONFIG = {
    'host': os.getenv('PGHOST', 'localhost'),
    'port': os.getenv('PGPORT', '5432'),
    'database': os.getenv('PGDATABASE', 'railway'),
    'user': os.getenv('PGUSER', 'postgres'),
    'password': os.getenv('PGPASSWORD', 'postgres')
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def criar_tabela_contracts():
    """Cria tabela contracts se nao existir"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id SERIAL PRIMARY KEY,
            orgao_id TEXT,
            data DATE,
            fornecedor TEXT,
            fornecedor_id TEXT,
            valor NUMERIC,
            descricao TEXT,
            fonte TEXT DEFAULT 'SP_Contratos_2024',
            importado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Tabela 'contracts' verificada/criada")

# ---------------------------
# 1. DOWNLOAD
# ---------------------------
def download_csv(url):
    print("=" * 80)
    print("ETL PIPELINE - Contratos SP 2024")
    print("=" * 80)
    print(f"\n[1/5] Baixando CSV de:\n{url}")
    
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    r.encoding = 'utf-8-sig'  # Remove BOM
    
    print(f"✓ Download concluido: {len(r.text):,} caracteres")
    return r.text

# ---------------------------
# 2. PARSE
# ---------------------------
def parse_csv(text):
    print("\n[2/5] Parseando CSV...")
    
    # Pular 4 primeiras linhas (cabecalho com titulo)
    lines = text.split('\n')[4:]
    text_clean = '\n'.join(lines)
    
    df = pd.read_csv(
        StringIO(text_clean),
        sep=';',
        engine='python',
        on_bad_lines='skip'
    )
    
    print(f"✓ CSV parseado: {len(df)} registros")
    print(f"  Colunas: {list(df.columns)}")
    return df

# ---------------------------
# 3. CLEANING
# ---------------------------
def clean_value(value):
    """Limpa valor monetario: 'R$ 36.500,00' -> 36500.00"""
    if pd.isna(value):
        return None
    
    value_str = str(value)
    
    # Remove R$
    value_str = value_str.replace('R$', '')
    # Troca ponto de milhar (remove)
    value_str = value_str.replace('.', '')
    # Troca virgula decimal por ponto
    value_str = value_str.replace(',', '.')
    # Remove tudo que nao for numero ou ponto
    value_str = re.sub(r'[^0-9.]', '', value_str)
    
    try:
        return float(value_str) if value_str else None
    except:
        return None

def clean_date(date_str):
    """Converte dd/mm/yyyy para DATE"""
    if pd.isna(date_str):
        return None
    
    try:
        # Tenta parsear
        return pd.to_datetime(date_str, dayfirst=True, format='%d/%m/%Y').date()
    except:
        try:
            # Fallback para outros formatos
            return pd.to_datetime(date_str, dayfirst=True).date()
        except:
            return None

# ---------------------------
# 4. TRANSFORM
# ---------------------------
def transform(df):
    print("\n[3/5] Transformando dados...")
    
    # Mapeamento de colunas
    column_map = {
        'Nome do Orgao': 'orgao_id',
        'Data da Assinatura': 'data',
        'Fornecedor e Nome de Fantasia': 'fornecedor',
        'CNPJ/CPF': 'fornecedor_id',
        'Valor(R$)': 'valor',
        'Contrato': 'external_id'
    }
    
    # Renomear
    df = df.rename(columns=column_map)
    
    # Selecionar apenas colunas que existem
    cols_to_keep = [c for c in column_map.values() if c in df.columns]
    df = df[[c for c in cols_to_keep]]
    
    # Limpar valores
    if 'valor' in df.columns:
        print("  Limpando valores monetarios...")
        df['valor'] = df['valor'].apply(clean_value)
    
    if 'data' in df.columns:
        print("  Limpando datas...")
        df['data'] = df['data'].apply(clean_date)
    
    # Remover linhas sem dados essenciais
    df = df.dropna(subset=['data', 'valor', 'fornecedor'])
    
    print(f"✓ Transformacao concluida: {len(df)} registros validos")
    
    # Mostrar amostra
    print("\n  Amostra de dados:")
    print(df.head(3).to_string(index=False))
    
    return df

# ---------------------------
# 5. LOAD (POSTGRES)
# ---------------------------
def insert_db(df):
    print("\n[4/5] Inserindo no banco...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    inseridos = 0
    erros = 0
    
    for _, row in df.iterrows():
        try:
            cur.execute("""
                INSERT INTO contracts (
                    orgao_id, data, fornecedor,
                    fornecedor_id, valor, descricao
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                row.get('orgao_id'),
                row.get('data'),
                row.get('fornecedor'),
                row.get('fornecedor_id'),
                row.get('valor'),
                row.get('external_id')  # Guardamos external_id em descricao
            ))
            inseridos += 1
            
        except Exception as e:
            erros += 1
            if erros <= 5:  # Mostrar apenas primeiros erros
                print(f"    Erro na linha {_}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✓ Inseridos: {inseridos} registros")
    if erros > 0:
        print(f"  Erros: {erros} registros")

# ---------------------------
# 6. GERAR BASELINE
# ---------------------------
def gerar_baseline():
    print("\n[5/5] Gerando baseline...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Calcular metricas
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT fornecedor) as fornecedores_unicos,
            AVG(valor) as valor_medio,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor) as valor_mediano,
            MAX(valor) as valor_maximo
        FROM contracts
        WHERE fonte = 'SP_Contratos_2024'
    """)
    
    row = cur.fetchone()
    
    # Top fornecedores
    cur.execute("""
        SELECT fornecedor, COUNT(*) as qtd, SUM(valor) as total
        FROM contracts
        WHERE fonte = 'SP_Contratos_2024'
        GROUP BY fornecedor
        ORDER BY qtd DESC
        LIMIT 5
    """)
    
    top_fornecedores = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # Mostrar resultado
    print("\n" + "=" * 80)
    print("BASELINE GERADO")
    print("=" * 80)
    print(f"Orgao: Prefeitura de Sao Paulo")
    print(f"Periodo: 2024")
    print(f"Total de contratos: {row[0]:,}")
    print(f"Fornecedores unicos: {row[1]:,}")
    print(f"Valor medio: R$ {row[2]:,.2f}")
    print(f"Valor mediano: R$ {row[3]:,.2f}")
    print(f"Valor maximo: R$ {row[4]:,.2f}")
    print("\nTop 5 fornecedores:")
    for i, f in enumerate(top_fornecedores, 1):
        print(f"  {i}. {f[0][:50]}...")
        print(f"     {f[1]} contratos, R$ {f[2]:,.2f}")
    print("=" * 80)

# ---------------------------
# PIPELINE PRINCIPAL
# ---------------------------
def run():
    try:
        # 0. Preparar banco
        criar_tabela_contracts()
        
        # 1-4. ETL
        raw = download_csv(CSV_URL)
        df = parse_csv(raw)
        df = transform(df)
        insert_db(df)
        
        # 5. Baseline
        gerar_baseline()
        
        print("\n" + "=" * 80)
        print("✓ PIPELINE CONCLUIDO COM SUCESSO!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    run()
