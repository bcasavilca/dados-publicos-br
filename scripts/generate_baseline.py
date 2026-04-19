#!/usr/bin/env python3
"""
Generate Baseline - Calcula baseline estatistico de orgaos
Estrutura: raw data -> calculo -> baseline
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import psycopg2
import pandas as pd
from collections import Counter

# PostgreSQL config (Railway)
DB_CONFIG = {
    'host': os.getenv('PGHOST', 'localhost'),
    'port': os.getenv('PGPORT', '5432'),
    'database': os.getenv('PGDATABASE', 'railway'),
    'user': os.getenv('PGUSER', 'postgres'),
    'password': os.getenv('PGPASSWORD', 'postgres')
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def criar_tabela_baselines():
    """Cria tabela de baselines se nao existir"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS baselines (
            id SERIAL PRIMARY KEY,
            orgao_id TEXT,
            periodo TEXT,
            contratos_mes_media NUMERIC,
            contratos_mes_mediana NUMERIC,
            fornecedores_unicos INTEGER,
            concentracao_top1 NUMERIC,
            concentracao_top3 NUMERIC,
            valor_mediano NUMERIC,
            valor_maximo NUMERIC,
            gerado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Tabela 'baselines' criada/verificada")

def get_data(orgao_id):
    """Busca dados de contratos do orgao"""
    conn = get_db_connection()
    
    # Buscar da tabela documents (onde estao os portais)
    df = pd.read_sql(
        "SELECT * FROM documents WHERE orgao ILIKE %s",
        conn,
        params=(f'%{orgao_id}%',)
    )
    
    conn.close()
    return df

def calculate_baseline(df):
    """Calcula metricas de baseline"""
    if df.empty:
        return None
    
    # Simular dados temporais (no CSV nao temos data real)
    # Usar distribuicao por fonte como proxy
    
    total_registros = len(df)
    
    # 1. "Contratos" por fonte (simulando meses)
    registros_por_fonte = df.groupby('fonte').size()
    media = registros_por_fonte.mean()
    mediana = registros_por_fonte.median()
    
    # 2. Fornecedores unicos (usando titulo como proxy)
    fornecedores_unicos = df['titulo'].nunique()
    
    # 3. Concentracao
    contagem = df['titulo'].value_counts()
    top1 = contagem.iloc[0] / total_registros if len(contagem) > 0 else 0
    top3 = contagem.iloc[:3].sum() / total_registros if len(contagem) > 3 else top1
    
    # 4. Valores (simulado - no CSV nao temos valores reais)
    # Usar length de descricao como proxy
    df['valor_proxy'] = df['descricao'].str.len()
    valor_mediano = df['valor_proxy'].median()
    valor_maximo = df['valor_proxy'].max()
    
    return {
        'contratos_mes_media': float(media),
        'contratos_mes_mediana': float(mediana),
        'fornecedores_unicos': int(fornecedores_unicos),
        'concentracao_top1': float(top1),
        'concentracao_top3': float(top3),
        'valor_mediano': float(valor_mediano),
        'valor_maximo': float(valor_maximo),
    }

def save_baseline(orgao_id, metrics):
    """Salva baseline no banco"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO baselines (
            orgao_id, periodo,
            contratos_mes_media, contratos_mes_mediana,
            fornecedores_unicos, concentracao_top1, concentracao_top3,
            valor_mediano, valor_maximo
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        orgao_id, '12m',
        metrics['contratos_mes_media'],
        metrics['contratos_mes_mediana'],
        metrics['fornecedores_unicos'],
        metrics['concentracao_top1'],
        metrics['concentracao_top3'],
        metrics['valor_mediano'],
        metrics['valor_maximo']
    ))
    
    conn.commit()
    cur.close()
    conn.close()

def run(orgao_id):
    """Executa pipeline completo"""
    print(f"Gerando baseline para: {orgao_id}")
    print("-" * 60)
    
    criar_tabela_baselines()
    
    df = get_data(orgao_id)
    print(f"Registros encontrados: {len(df)}")
    
    if df.empty:
        print("ERRO: Sem dados para orgao")
        return
    
    baseline = calculate_baseline(df)
    if not baseline:
        print("ERRO: Nao foi possivel calcular baseline")
        return
    
    save_baseline(orgao_id, baseline)
    
    print(f"\nBaseline gerado com sucesso!")
    print(f"  Media contratos: {baseline['contratos_mes_media']:.2f}")
    print(f"  Fornecedores unicos: {baseline['fornecedores_unicos']}")
    print(f"  Concentracao top1: {baseline['concentracao_top1']:.2%}")
    print(f"  Valor mediano: {baseline['valor_mediano']:.2f}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python generate_baseline.py <orgao_id>")
        print("Exemplo: python generate_baseline.py Fortaleza")
        sys.exit(1)
    
    run(sys.argv[1])
