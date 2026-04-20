#!/bin/bash
# Graph Engine v1 - Rede de Relacoes

cat > graph_v1.py << 'PYEND'
import os
import psycopg2
from itertools import combinations
from collections import Counter

print("=" * 80)
print("GRAPH ENGINE v1 - Rede de Relacoes")
print("Detectando estruturas ocultas nos contratos")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# ============================================================
# 1. Criar tabela de edges
# ============================================================
print("\n[1/5] Criando schema de grafo...")

cur.execute("""
    DROP TABLE IF EXISTS graph_edges
""")

cur.execute("""
    CREATE TABLE graph_edges (
        node_a TEXT,
        node_b TEXT,
        relation_type TEXT,
        weight INT DEFAULT 1,
        PRIMARY KEY (node_a, node_b, relation_type)
    )
""")

conn.commit()
print("✓ Tabela graph_edges criada")

# ============================================================
# 2. Co-ocorrencia de fornecedores (mesmo orgao)
# ============================================================
print("\n[2/5] Calculando co-ocorrencias...")

cur.execute("""
    SELECT orgao, fornecedor, COUNT(*) as qtd
    FROM sp_contratos
    GROUP BY orgao, fornecedor
    ORDER BY orgao, qtd DESC
""")

orgao_fornecedores = {}
for orgao, fornecedor, qtd in cur.fetchall():
    if orgao not in orgao_fornecedores:
        orgao_fornecedores[orgao] = []
    orgao_fornecedores[orgao].append((fornecedor, qtd))

print(f"Orgaos encontrados: {len(orgao_fornecedores)}")

# Gerar edges de co-ocorrencia
edges_coocorrencia = []
for orgao, fornecedores in orgao_fornecedores.items():
    # Pegar apenas fornecedores com +5 contratos nesse orgao (significativo)
    significativos = [f for f, q in fornecedores if q >= 5]
    
    if len(significativos) >= 2:
        for a, b in combinations(significativos, 2):
            # Peso = soma dos contratos de ambos
            peso_a = next(q for f, q in fornecedores if f == a)
            peso_b = next(q for f, q in fornecedores if f == b)
            peso = min(peso_a, peso_b)  # Menor determina forca da conexao
            
            edges_coocorrencia.append((a, b, 'co_occurrence', peso))

# Inserir edges
for node_a, node_b, rel_type, weight in edges_coocorrencia:
    cur.execute("""
        INSERT INTO graph_edges (node_a, node_b, relation_type, weight)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (node_a, node_b, relation_type)
        DO UPDATE SET weight = graph_edges.weight + EXCLUDED.weight
    """, (node_a, node_b, rel_type, weight))

conn.commit()
print(f"✓ Inseridas {len(edges_coocorrencia)} co-ocorrencias")

# ============================================================
# 3. Fornecedor -> Orgao (dominios)
# ============================================================
print("\n[3/5] Mapeando fornecedor -> orgao...")

cur.execute("""
    SELECT fornecedor, orgao, COUNT(*) as contratos
    FROM sp_contratos
    GROUP BY fornecedor, orgao
    HAVING COUNT(*) >= 10
    ORDER BY contratos DESC
""")

edges_supply = []
for fornecedor, orgao, contratos in cur.fetchall():
    edges_supply.append((fornecedor, orgao, 'supply', contratos))

for node_a, node_b, rel_type, weight in edges_supply:
    cur.execute("""
        INSERT INTO graph_edges (node_a, node_b, relation_type, weight)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (node_a, node_b, relation_type)
        DO UPDATE SET weight = graph_edges.weight + EXCLUDED.weight
    """, (node_a, node_b, rel_type, weight))

conn.commit()
print(f"✓ Inseridas {len(edges_supply)} relacoes supply")

# ============================================================
# 4. Analise de centralidade
# ============================================================
print("\n[4/5] Calculando centralidade...")

# Top nos mais conectados (co-ocorrencia)
cur.execute("""
    SELECT node_a, SUM(weight) as total_weight
    FROM graph_edges
    WHERE relation_type = 'co_occurrence'
    GROUP BY node_a
    ORDER BY total_weight DESC
    LIMIT 10
""")

print("\n🏆 Fornecedores mais conectados (co-ocorrencia):")
print(f"{'Fornecedor':<40} {'Conexoes':>10}")
print("-" * 55)

for node, weight in cur.fetchall():
    print(f"{node[:38]:<40} {weight:>10}")

# Top dominios (supply)
cur.execute("""
    SELECT node_a, COUNT(DISTINCT node_b) as orgaos_diferentes, SUM(weight) as total
    FROM graph_edges
    WHERE relation_type = 'supply'
    GROUP BY node_a
    ORDER BY orgaos_diferentes DESC, total DESC
    LIMIT 10
""")

print("\n🏛️  Fornecedores mais dominantes (orgaos diferentes):")
print(f"{'Fornecedor':<35} {'Orgaos':>8} {'Contratos':>10}")
print("-" * 60)

for node, orgaos, total in cur.fetchall():
    print(f"{node[:33]:<35} {orgaos:>8} {total:>10}")

# ============================================================
# 5. Detectar clusters (simplificado)
# ============================================================
print("\n[5/5] Detectando clusters...")

# Triangulos: A conectado com B, B conectado com C, A conectado com C
cur.execute("""
    SELECT DISTINCT 
        g1.node_a as a,
        g1.node_b as b,
        g2.node_b as c
    FROM graph_edges g1
    JOIN graph_edges g2 ON g1.node_b = g2.node_a
    JOIN graph_edges g3 ON g1.node_a = g3.node_a AND g2.node_b = g3.node_b
    WHERE g1.relation_type = 'co_occurrence'
      AND g2.relation_type = 'co_occurrence'
      AND g3.relation_type = 'co_occurrence'
      AND g1.node_a < g2.node_b
    LIMIT 20
""")

triangulos = cur.fetchall()

if triangulos:
    print(f"\n🔺 Clusters detectados (triangulos): {len(triangulos)}")
    print("\nExemplos de triangulos (possiveis conluios):")
    for i, (a, b, c) in enumerate(triangulos[:5], 1):
        print(f"  {i}. {a[:25]} + {b[:25]} + {c[:25]}")
else:
    print("\n⚠️  Nenhum triangulo forte detectado (pode ser bom!)")

# Resumo
cur.execute("SELECT COUNT(*) FROM graph_edges")
total_edges = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT node_a) FROM graph_edges")
nodes_unicos = cur.fetchone()[0]

conn.close()

print("\n" + "=" * 80)
print("RESUMO DO GRAFO")
print("=" * 80)
print(f"Total de edges: {total_edges:,}")
print(f"Nodes unicos: {nodes_unicos:,}")
print(f"Densidade: {total_edges / (nodes_unicos * (nodes_unicos - 1) / 2) * 100:.2f}%")

if total_edges > 1000:
    print("✅ Grafo denso - muitas conexoes detectadas")
else:
    print("⚡ Grafo esparo - mercado fragmentado")

print("=" * 80)
print("✓ Graph Engine v1 concluido!")
print("=" * 80)
PYEND

python graph_v1.py
