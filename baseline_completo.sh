#!/bin/bash
# Baseline Estatístico Completo - SP 2024

cat > baseline_completo.py << 'EOF'
import os
import psycopg2
import numpy as np

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=" * 80)
print("BASELINE ESTATÍSTICO COMPLETO - São Paulo 2024")
print("=" * 80)

# Buscar todos os valores
cur.execute("SELECT valor FROM sp_contratos")
valores = [row[0] for row in cur.fetchall()]

valores_array = np.array(valores)

print("\n📊 DISTRIBUIÇÃO DE VALORES")
print("-" * 80)
print(f"Total de contratos: {len(valores):,}")
print(f"Valor mínimo: R$ {np.min(valores_array):,.2f}")
print(f"Valor máximo: R$ {np.max(valores_array):,.2f}")
print(f"Média: R$ {np.mean(valores_array):,.2f}")
print(f"Mediana (P50): R$ {np.percentile(valores_array, 50):,.2f}")
print(f"P90: R$ {np.percentile(valores_array, 90):,.2f}")
print(f"P95: R$ {np.percentile(valores_array, 95):,.2f}")
print(f"P99: R$ {np.percentile(valores_array, 99):,.2f}")

print("\n📈 CONCENTRAÇÃO DE FORNECEDORES")
print("-" * 80)

# Top fornecedores
cur.execute("""
    SELECT fornecedor, COUNT(*) as qtd
    FROM sp_contratos
    GROUP BY fornecedor
    ORDER BY qtd DESC
""")

fornecedores = cur.fetchall()
total = len(valores)

# Top 1
if len(fornecedores) >= 1:
    top1 = fornecedores[0]
    print(f"Top 1: {top1[0][:40]}... ({top1[1]} contratos, {(top1[1]/total)*100:.2f}%)")

# Top 3
if len(fornecedores) >= 3:
    top3_qtd = sum(f[1] for f in fornecedores[:3])
    print(f"Top 3: {top3_qtd} contratos ({(top3_qtd/total)*100:.2f}%)")

# Top 10
if len(fornecedores) >= 10:
    top10_qtd = sum(f[1] for f in fornecedores[:10])
    print(f"Top 10: {top10_qtd} contratos ({(top10_qtd/total)*100:.2f}%)")

print(f"Fornecedores únicos: {len(fornecedores):,}")

print("\n💰 CONCENTRAÇÃO FINANCEIRA (CRÍTICO)")
print("-" * 80)

# Top por valor
cur.execute("""
    SELECT fornecedor, SUM(valor) as total
    FROM sp_contratos
    GROUP BY fornecedor
    ORDER BY total DESC
""")

forn_por_valor = cur.fetchall()
total_valor = np.sum(valores_array)

# Top 1 financeiro
if len(forn_por_valor) >= 1:
    top1_val = forn_por_valor[0]
    print(f"Top 1 (valor): {top1_val[0][:40]}... (R$ {top1_val[1]:,.2f}, {(top1_val[1]/total_valor)*100:.2f}%)")

# Top 3 financeiro
if len(forn_por_valor) >= 3:
    top3_val = sum(f[1] for f in forn_por_valor[:3])
    print(f"Top 3 (valor): R$ {top3_val:,.2f} ({(top3_val/total_valor)*100:.2f}%)")

# Top 10 financeiro
if len(forn_por_valor) >= 10:
    top10_val = sum(f[1] for f in forn_por_valor[:10])
    print(f"Top 10 (valor): R$ {top10_val:,.2f} ({(top10_val/total_valor)*100:.2f}%)")

print(f"\nValor total do sistema: R$ {total_valor:,.2f}")

print("\n" + "=" * 80)
print("🎯 THRESHOLDS RECOMENDADOS PARA MOTOR V2.1")
print("=" * 80)
print(f"Threshold de VALOR ANÔMALO: > R$ {np.percentile(valores_array, 99):,.2f} (P99)")
print(f"Threshold de CONCENTRAÇÃO: > {(top3_qtd/total)*100:.1f}% (3× top3 atual)")
print(f"Threshold de FORNECEDOR: > {int(np.percentile([f[1] for f in fornecedores], 90))} contratos (P90)")
print("=" * 80)

conn.close()
print("\n✅ Baseline completo gerado!")
EOF

python baseline_completo.py
