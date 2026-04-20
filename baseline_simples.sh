#!/bin/bash
# Baseline simples para Railway

cat > baseline_simples.py << 'EOF'
import os
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=" * 60)
print("BASELINE SP 2024 - SIMPLIFICADO")
print("=" * 60)

# Estatísticas básicas
cur.execute("""
    SELECT 
        COUNT(*),
        MIN(valor),
        MAX(valor),
        AVG(valor)
    FROM sp_contratos
""")
row = cur.fetchone()

print(f"\nTotal: {row[0]:,} contratos")
print(f"Mínimo: R$ {row[1]:,.2f}")
print(f"Máximo: R$ {row[2]:,.2f}")
print(f"Média: R$ {row[3]:,.2f}")

# Percentis via SQL
cur.execute("""
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY valor),
           percentile_cont(0.9) WITHIN GROUP (ORDER BY valor),
           percentile_cont(0.95) WITHIN GROUP (ORDER BY valor),
           percentile_cont(0.99) WITHIN GROUP (ORDER BY valor)
    FROM sp_contratos
""")
pct = cur.fetchone()

print(f"\nPercentis:")
print(f"P50 (mediana): R$ {pct[0]:,.2f}")
print(f"P90: R$ {pct[1]:,.2f}")
print(f"P95: R$ {pct[2]:,.2f}")
print(f"P99: R$ {pct[3]:,.2f}")

# Concentração
cur.execute("SELECT COUNT(*) FROM sp_contratos")
total = cur.fetchone()[0]

cur.execute("""
    SELECT fornecedor, COUNT(*)
    FROM sp_contratos
    GROUP BY fornecedor
    ORDER BY COUNT(*) DESC
    LIMIT 3
""")

top3 = cur.fetchall()
top3_total = sum(t[1] for t in top3)

print(f"\nConcentração:")
print(f"Top 1: {top3[0][1]} contratos ({(top3[0][1]/total)*100:.2f}%)")
print(f"Top 3: {top3_total} contratos ({(top3_total/total)*100:.2f}%)")

print(f"\n{'='*60}")
print("THRESHOLDS RECOMENDADOS:")
print(f"Valor anômalo: > R$ {pct[3]:,.2f} (P99)")
print(f"Concentração suspeita: > {(top3_total/total)*100*3:.1f}%")
print(f"{'='*60}")

conn.close()
print("\n✓ Baseline completo!")
EOF

python baseline_simples.py
