#!/bin/bash
# Graph Engine v1 - Corrigido

cat > graph_v1_fix.py << 'PYEND'
import os
import psycopg2
from itertools import combinations

print("=" * 80)
print("GRAPH ENGINE v1")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Criar tabela
print("\n[1/3] Criando tabela...")
cur.execute("DROP TABLE IF EXISTS graph_edges")
cur.execute("""
    CREATE TABLE graph_edges (
        node_a TEXT,
        node_b TEXT,
        relation_type TEXT,
        weight INT DEFAULT 1,
        PRIMARY KEY (node_a, node_b, relation_type)
    )
""")
print("✓ Tabela criada")

# Co-ocorrencia
print("\n[2/3] Calculando co-ocorrencias...")
cur.execute("SELECT orgao, fornecedor, COUNT(*) FROM sp_contratos GROUP BY orgao, fornecedor")

org_forn = {}
for org, forn, qtd in cur.fetchall():
    if org not in org_forn:
        org_forn[org] = []
    org_forn[org].append((forn, qtd))

print(f"Orgaos: {len(org_forn)}")

edges = 0
for org, forns in org_forn.items():
    sig = [f for f, q in forns if q >= 5]
    if len(sig) >= 2:
        for a, b in combinations(sig, 2):
            peso_a = next(q for f, q in forns if f == a)
            peso_b = next(q for f, q in forns if f == b)
            
            # CORRECAO: Especificar colunas no ON CONFLICT
            try:
                cur.execute("""
                    INSERT INTO graph_edges (node_a, node_b, relation_type, weight)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (node_a, node_b, relation_type)
                    DO UPDATE SET weight = graph_edges.weight + EXCLUDED.weight
                """, (a, b, 'co_occurrence', min(peso_a, peso_b)))
                edges += 1
            except Exception as e:
                print(f"Erro ao inserir edge: {e}")
                continue

print(f"✓ Co-ocorrencias: {edges}")

# Supply
print("\n[3/3] Mapeando supply...")
cur.execute("SELECT fornecedor, orgao, COUNT(*) FROM sp_contratos GROUP BY fornecedor, orgao HAVING COUNT(*) >= 10")

for forn, org, qtd in cur.fetchall():
    try:
        cur.execute("""
            INSERT INTO graph_edges (node_a, node_b, relation_type, weight)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (node_a, node_b, relation_type)
            DO UPDATE SET weight = graph_edges.weight + EXCLUDED.weight
        """, (forn, org, 'supply', qtd))
    except Exception as e:
        print(f"Erro: {e}")

conn.commit()

# Analise
print("\n" + "=" * 80)
print("RESULTADOS")
print("=" * 80)

print("\nTop conectados (co-ocorrencia):")
cur.execute("SELECT node_a, SUM(weight) as w FROM graph_edges WHERE relation_type='co_occurrence' GROUP BY node_a ORDER BY w DESC LIMIT 5")
for node, w in cur.fetchall():
    print(f"  {node[:40]:<42} {w:>8}")

print("\nTop dominantes (orgaos diferentes):")
cur.execute("SELECT node_a, COUNT(DISTINCT node_b) as c, SUM(weight) as t FROM graph_edges WHERE relation_type='supply' GROUP BY node_a ORDER BY c DESC, t DESC LIMIT 5")
for node, c, t in cur.fetchall():
    print(f"  {node[:35]:<37} {c:>6} orgaos, {t:>6}")

cur.execute("SELECT COUNT(*) FROM graph_edges")
total = cur.fetchone()[0]

conn.close()

print("\n" + "=" * 80)
print(f"Total edges: {total:,}")
print("✓ Graph Engine v1 concluido!")
print("=" * 80)
PYEND

python graph_v1_fix.py
