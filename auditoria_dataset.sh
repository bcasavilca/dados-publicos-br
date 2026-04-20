#!/bin/bash
# Auditoria completa do dataset SP

cat > auditoria.py << 'PYEND'
import os
import psycopg2
import re
from collections import Counter

print("=" * 80)
print("AUDITORIA DO DATASET SP 2024")
print("Analise completa de qualidade dos dados")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# ============================================================
# 1. OVERVIEW GERAL
# ============================================================
print("\n[1/5] OVERVIEW GERAL")
print("-" * 80)

cur.execute("SELECT COUNT(*) FROM sp_contratos")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT fornecedor) FROM sp_contratos")
fornecedores = cur.fetchone()[0]

cur.execute("SELECT SUM(valor) FROM sp_contratos")
valor_total = cur.fetchone()[0]

print(f"Total de contratos: {total:,}")
print(f"Fornecedores unicos: {fornecedores:,}")
print(f"Valor total: R$ {valor_total:,.2f}")
print(f"Valor medio por contrato: R$ {valor_total/total:,.2f}")

# ============================================================
# 2. ANALISE DE DATAS (coluna data_assinatura)
# ============================================================
print("\n[2/5] ANALISE DE DATAS")
print("-" * 80)

# Amostra de datas
print("\nAmostra de 10 datas (primeiros registros):")
cur.execute("SELECT data_assinatura FROM sp_contratos LIMIT 10")
for i, (data,) in enumerate(cur.fetchall(), 1):
    print(f"  {i}. '{data}'")

# Contagem por categoria
print("\nCategorizacao de datas:")

categorias = {
    'null': 0,
    'vazio': 0,
    'dd/mm/yyyy': 0,
    'yyyy-mm-dd': 0,
    'outro_formato': 0,
    'invalido': 0
}

cur.execute("SELECT data_assinatura FROM sp_contratos")
for (data,) in cur.fetchall():
    if data is None:
        categorias['null'] += 1
    elif data == '':
        categorias['vazio'] += 1
    elif re.match(r'^\d{2}/\d{2}/\d{4}$', data):
        categorias['dd/mm/yyyy'] += 1
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', data):
        categorias['yyyy-mm-dd'] += 1
    elif len(data) > 5:
        categorias['outro_formato'] += 1
    else:
        categorias['invalido'] += 1

for cat, qtd in categorias.items():
    pct = (qtd / total) * 100
    barra = '█' * int(pct / 2)
    print(f"  {cat:<15}: {qtd:>6,} ({pct:>5.1f}%) {barra}")

# ============================================================
# 3. ANALISE DE FORNECEDORES
# ============================================================
print("\n[3/5] ANALISE DE FORNECEDORES")
print("-" * 80)

cur.execute("""
    SELECT fornecedor, COUNT(*) as qtd
    FROM sp_contratos
    GROUP BY fornecedor
    ORDER BY qtd DESC
    LIMIT 10
""")

print("\nTop 10 fornecedores:")
total_top10 = 0
for forn, qtd in cur.fetchall():
    pct = (qtd / total) * 100
    total_top10 += qtd
    print(f"  {forn[:40]:<40} {qtd:>6} ({pct:>5.2f}%)")

print(f"\nTop 10 representam: {total_top10:,} contratos ({total_top10/total*100:.1f}%)")

# Distribuicao de concentracao
print("\nDistribuicao de concentracao:")
cur.execute("""
    SELECT COUNT(*) as qtd
    FROM sp_contratos
    GROUP BY fornecedor
""")

distribuicao = Counter([row[0] for row in cur.fetchall()])
print(f"  Fornecedores com 1 contrato: {distribuicao[1]:,}")
print(f"  Fornecedores com 2-5: {sum(v for k, v in distribuicao.items() if 2 <= k <= 5):,}")
print(f"  Fornecedores com 6-20: {sum(v for k, v in distribuicao.items() if 6 <= k <= 20):,}")
print(f"  Fornecedores com 21+: {sum(v for k, v in distribuicao.items() if k > 20):,}")

# ============================================================
# 4. ANALISE DE VALORES
# ============================================================
print("\n[4/5] ANALISE DE VALORES")
print("-" * 80)

cur.execute("""
    SELECT 
        MIN(valor), MAX(valor), AVG(valor),
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor),
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY valor),
        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY valor)
    FROM sp_contratos
""")

minimo, maximo, media, p50, p90, p99 = cur.fetchone()

print(f"\nEstatisticas de valor:")
print(f"  Minimo: R$ {minimo:,.2f}")
print(f"  Maximo: R$ {maximo:,.2f}")
print(f"  Media: R$ {media:,.2f}")
print(f"  Mediana (P50): R$ {p50:,.2f}")
print(f"  P90: R$ {p90:,.2f}")
print(f"  P99: R$ {p99:,.2f}")

# Distribuicao
print(f"\nDistribuicao:")
cur.execute("SELECT COUNT(*) FROM sp_contratos WHERE valor < 100000")
abaixo_100k = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM sp_contratos WHERE valor BETWEEN 100000 AND 1000000")
entre_100k_1m = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM sp_contratos WHERE valor > 1000000")
acima_1m = cur.fetchone()[0]

print(f"  Abaixo R$ 100k: {abaixo_100k:,} ({abaixo_100k/total*100:.1f}%)")
print(f"  R$ 100k - 1M: {entre_100k_1m:,} ({entre_100k_1m/total*100:.1f}%)")
print(f"  Acima R$ 1M: {acima_1m:,} ({acima_1m/total*100:.1f}%)")

# ============================================================
# 5. DIAGNOSTICO FINAL
# ============================================================
print("\n[5/5] DIAGNOSTICO FINAL")
print("-" * 80)

print("\n📊 QUALIDADE GERAL:")

# Score de qualidade
qualidade = 100

# Penalidade por falta de data
pct_sem_data = (categorias['null'] + categorias['vazio'] + categorias['invalido']) / total
if pct_sem_data > 0.5:
    qualidade -= 30
    print("  ❌ -30pts: Mais de 50% sem data confiavel")
elif pct_sem_data > 0.2:
    qualidade -= 15
    print("  ⚠️  -15pts: 20-50% sem data")

# Penalidade por concentracao extrema
pct_top1 = distribuicao[max(distribuicao.keys())] / total
if pct_top1 > 0.5:
    qualidade -= 20
    print("  ❌ -20pts: Concentracao extrema (possivel problema de dados)")

# Penalidade por valores
if minimo <= 0:
    qualidade -= 10
    print("  ⚠️  -10pts: Valores zero ou negativos detectados")

print(f"\n🏆 SCORE DE QUALIDADE: {qualidade}/100")

if qualidade >= 80:
    print("   ✅ EXCELENTE: Dataset pronto para analise temporal")
elif qualidade >= 60:
    print("   ⚠️  REGULAR: Requer limpeza antes de analise temporal")
    print("   💡 RECOMENDACAO: Implementar 'data recovery layer'")
elif qualidade >= 40:
    print("   ❌ FRACO: Dataset comprometido para analise temporal")
    print("   🔧 RECOMENDACAO: Focar em baseline estatico por enquanto")
else:
    print("   🚨 CRITICO: Dataset necessita revisao completa")

print("\n" + "=" * 80)
print("✓ Auditoria concluida!")
print("=" * 80)

conn.close()
PYEND

python auditoria.py
