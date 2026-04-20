#!/usr/bin/env python3
"""
Pipeline ETL DEMO - Sem banco, apenas processamento
Mostra o fluxo completo do ETL
"""

import requests
import pandas as pd
from io import StringIO
import re

CSV_URL = 'https://dados.prefeitura.sp.gov.br/dataset/6588aef7-20ff-4cec-b1e1-6c06520240c0/resource/fd48b7dd-c5f1-4352-963f-f1e5ebc6d61b/download/contratos.csv'

def clean_value(value):
    """Limpa valor monetario"""
    if pd.isna(value):
        return None
    value_str = str(value)
    value_str = value_str.replace('R$', '').replace('.', '').replace(',', '.')
    value_str = re.sub(r'[^0-9.]', '', value_str)
    try:
        return float(value_str) if value_str else None
    except:
        return None

def main():
    print("=" * 80)
    print("PIPELINE ETL - DEMO (Sem banco)")
    print("=" * 80)
    
    # 1. Download
    print("\n[1/5] Baixando CSV...")
    r = requests.get(CSV_URL, timeout=120)
    print(f"Download: {len(r.text):,} caracteres")
    
    # 2. Parse
    print("\n[2/5] Parseando CSV...")
    lines = r.text.split('\n')[4:]  # Pular cabecalho
    df = pd.read_csv(StringIO('\n'.join(lines)), sep=';', engine='python')
    print(f"Registros: {len(df)}")
    
    # Debug: mostrar colunas reais
    print(f"Colunas reais: {list(df.columns)}")
    print("\n[3/5] Transformando...")
    df = df.rename(columns={
        'Nome do Orgao': 'orgao_id',
        'Data da Assinatura': 'data',
        'Fornecedor e Nome de Fantasia': 'fornecedor',
        'Valor(R$)': 'valor'
    })
    
    df['valor'] = df['valor'].apply(clean_value)
    df = df.dropna(subset=['valor', 'fornecedor'])
    print(f"Validos: {len(df)}")
    
    # 4. Baseline (calculo em memoria)
    print("\n[4/5] Calculando baseline...")
    
    total = len(df)
    fornecedores_unicos = df['fornecedor'].nunique()
    valor_medio = df['valor'].mean()
    valor_mediano = df['valor'].median()
    valor_max = df['valor'].max()
    
    # Concentracao top 1
    contagem = df['fornecedor'].value_counts()
    top1_pct = contagem.iloc[0] / total * 100 if len(contagem) > 0 else 0
    
    print("\n" + "=" * 80)
    print("BASELINE CALCULADO (DEMO)")
    print("=" * 80)
    print(f"Orgao: Prefeitura de Sao Paulo")
    print(f"Periodo: 2024")
    print(f"Total de contratos: {total:,}")
    print(f"Fornecedores unicos: {fornecedores_unicos:,}")
    print(f"Valor medio: R$ {valor_medio:,.2f}")
    print(f"Valor mediano: R$ {valor_mediano:,.2f}")
    print(f"Valor maximo: R$ {valor_max:,.2f}")
    print(f"Concentracao top1: {top1_pct:.1f}%")
    print("\nTop 5 fornecedores:")
    for i, (forn, qtd) in enumerate(contagem.head(5).items(), 1):
        total_forn = df[df['fornecedor'] == forn]['valor'].sum()
        print(f"  {i}. {forn[:40]}...")
        print(f"     {qtd} contratos, R$ {total_forn:,.2f}")
    print("=" * 80)
    
    print("\n[5/5] Pipeline concluido!")
    print("\nNota: Para persistir no banco, configure DATABASE_URL")

if __name__ == '__main__':
    main()
