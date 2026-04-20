import os
import psycopg2

print("=" * 70)
print("BASELINE TEMPORAL")
print("=" * 70)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Criar tabela
cur.execute("""
    CREATE TABLE IF NOT EXISTS baseline_temporal (
        mes TEXT, total_contratos INT, total_valor NUMERIC,
        fornecedores_unicos INT, concentracao_top1 NUMERIC
    )
""")

# Limpar testes
cur.execute("DELETE FROM baseline_temporal")

# Agrupar por mes
cur.execute("""
    SELECT SUBSTRING(data FROM 4 FOR 2) as mes,
           COUNT(*) as c, SUM(valor) as v,
           COUNT(DISTINCT fornecedor) as f
    FROM sp_contratos WHERE data != ''
    GROUP BY SUBSTRING(data FROM 4 FOR 2)
    ORDER BY mes
""")

meses = cur.fetchall()
print(f"Meses: {len(meses)}")

# Inserir
for mes, c, v, f in meses:
    # Top 1
    cur.execute("""
        SELECT COUNT(*) FROM sp_contratos 
        WHERE SUBSTRING(data FROM 4 FOR 2) = %s
        GROUP BY fornecedor ORDER BY COUNT(*) DESC LIMIT 1
    """, (mes,))
    top1 = cur.fetchone()
    conc = (top1[0]/c) if top1 else 0
    
    cur.execute("""
        INSERT INTO baseline_temporal VALUES (%s, %s, %s, %s, %s)
    """, (f"2024-{mes}", c, v, f, conc))

conn.commit()

# Analisar variacoes
cur.execute("SELECT * FROM baseline_temporal ORDER BY mes")
rows = cur.fetchall()

print(f"\n{'Mês':<8} {'Contratos':>10} {'Valor':>15} {'Top1%':>8}")
print("-" * 50)

for i, row in enumerate(rows):
    mes, c, v, f, top1 = row
    
    # Variacao vs anterior
    alerta = ""
    if i > 0:
        prev = rows[i-1]
        if c > prev[1] * 1.5:
            alerta += " SPIKE!"
    
    print(f"{mes:<8} {c:>10,} R${v/1e6:>12.1f}M {top1*100:>7.1f}%{alerta}")

print("\n" + "=" * 70)
print("Baseline temporal criado!")
print("=" * 70)

conn.close()
