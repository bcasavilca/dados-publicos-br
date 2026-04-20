import os
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=" * 80)
print("TOP 10 FORNECEDORES - SP 2024")
print("=" * 80)

cur.execute("""
    SELECT 
        fornecedor, 
        COUNT(*) as qtd_contratos,
        SUM(valor) as total_valor,
        AVG(valor) as media_valor
    FROM sp_contratos
    GROUP BY fornecedor
    ORDER BY COUNT(*) DESC
    LIMIT 10
""")

for i, row in enumerate(cur.fetchall(), 1):
    fornecedor = row[0][:50]
    qtd = row[1]
    total = row[2]
    media = row[3]
    print(f"\n{i}. {fornecedor}")
    print(f"   Contratos: {qtd:,}")
    print(f"   Total: R$ {total:,.2f}")
    print(f"   Média por contrato: R$ {media:,.2f}")

# Calcular concentração
cur.execute("SELECT COUNT(*) FROM sp_contratos")
total = cur.fetchone()[0]

# Top 1
cur.execute("""
    SELECT fornecedor, COUNT(*) FROM sp_contratos
    GROUP BY fornecedor ORDER BY COUNT(*) DESC LIMIT 1
""")
top1 = cur.fetchone()
print(f"\n{'='*80}")
print("CONCENTRAÇÃO:")
print(f"  Total de contratos: {total:,}")
print(f"  Top 1: {top1[0][:40]}... ({top1[1]} contratos)")
print(f"  Concentração: {(top1[1]/total)*100:.1f}%")
print(f"{'='*80}")

conn.close()
