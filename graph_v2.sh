#!/bin/bash
# Graph Engine v2 - Comunidades, PageRank, Triangulos

cat > graph_v2.py << 'PYEND'
import os
import psycopg2
import networkx as nx
from networkx.algorithms.community import louvain_communities
from itertools import combinations

print("=" * 80)
print("GRAPH ENGINE v2 - Comunidades, PageRank, Cartel")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 1. Criar tabela de resultados
print("\n[1/5] Preparando schema...")
cur.execute("DROP TABLE IF EXISTS graph_communities")
cur.execute("DROP TABLE IF EXISTS graph_pagerank")
cur.execute("DROP TABLE IF EXISTS graph_triangles")

cur.execute("""
    CREATE TABLE graph_communities (
        community_id INT,
        node TEXT,
        PRIMARY KEY (community_id, node)
    )
""")

cur.execute("""
    CREATE TABLE graph_pagerank (
        node TEXT PRIMARY KEY,
        score FLOAT
    )
""")

cur.execute("""
    CREATE TABLE graph_triangles (
        node_a TEXT,
        node_b TEXT,
        node_c TEXT,
        PRIMARY KEY (node_a, node_b, node_c)
    )
""")

conn.commit()
print("✓ Tabelas criadas")

# 2. Construir grafo NetworkX
print("\n[2/5] Construindo grafo...")

cur.execute("SELECT node_a, node_b, weight FROM graph_edges WHERE relation_type='co_occurrence'")

G = nx.Graph()
for a, b, w in cur.fetchall():
    if G.has_edge(a, b):
        G[a][b]["weight"] += w
    else:
        G.add_edge(a, b, weight=w)

print(f"✓ Grafo: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# 3. LOUVAIN - Comunidades
print("\n[3/5] Detectando comunidades (Louvain)...")

communities = louvain_communities(G, weight="weight", seed=42)

print(f"✓ {len(communities)} comunidades detectadas")

for comm_id, nodes in enumerate(communities):
    for node in nodes:
        cur.execute("INSERT INTO graph_communities VALUES (%s, %s)", (comm_id, node))

conn.commit()

# Mostrar top comunidades
print("\nTop comunidades:")
sizes = [(cid, len([n for c, n in cur.execute("SELECT * FROM graph_communities WHERE community_id=%s", (cid,))])) for cid in range(len(communities))]
for cid, size in sorted(sizes, key=lambda x: x[1], reverse=True)[:5]:
    print(f"  Comunidade {cid}: {size} fornecedores")

# 4. PAGERANK - Influencia
print("\n[4/5] Calculando PageRank...")

pagerank = nx.pagerank(G, weight="weight")

for node, score in pagerank.items():
    cur.execute("INSERT INTO graph_pagerank VALUES (%s, %s)", (node, score))

conn.commit()

print("\nTop 5 influentes (PageRank):")
cur.execute("SELECT node, score FROM graph_pagerank ORDER BY score DESC LIMIT 5")
for node, score in cur.fetchall():
    print(f"  {node[:40]:<42} {score:.6f}")

# 5. TRIANGULOS - Cartel potencial
print("\n[5/5] Detectando triangulos (cartel)...")

triangles = []
for node in G.nodes():
    neighbors = list(G.neighbors(node))
    for i in range(len(neighbors)):
        for j in range(i+1, len(neighbors)):
            a, b = neighbors[i], neighbors[j]
            if G.has_edge(a, b):
                # Ordenar para evitar duplicados
                trio = tuple(sorted([node, a, b]))
                if trio not in triangles:
                    triangles.append(trio)

print(f"✓ {len(triangles)} triangulos detectados")

for a, b, c in triangles[:20]:
    cur.execute("INSERT INTO graph_triangles VALUES (%s, %s, %s)", (a, b, c))

conn.commit()

if triangles:
    print("\nTop triangulos suspeitos:")
    for i, (a, b, c) in enumerate(triangles[:5], 1):
        print(f"  {i}. {a[:25]} + {b[:25]} + {c[:25]}")

# 6. CLUSTERING COEFFICIENT
print("\n" + "=" * 80)
print("ANALISE DE DENSIDADE")
print("=" * 80)

avg_clustering = nx.average_clustering(G, weight="weight")
print(f"\nCoeficiente medio de clustering: {avg_clustering:.3f}")

if avg_clustering > 0.6:
    print("🔴 ALTA DENSIDADE: Possivel estrutura de cartel")
elif avg_clustering > 0.3:
    print("🟡 DENSIDADE MODERADA: Grupos fechados detectados")
else:
    print("🟢 DENSIDADE BAIXA: Mercado fragmentado")

# Top nodes com alto clustering (suspeitos)
cur.execute("""
    SELECT node_a, COUNT(*) as triangles
    FROM (
        SELECT node_a FROM graph_triangles
        UNION ALL
        SELECT node_b FROM graph_triangles
        UNION ALL
        SELECT node_c FROM graph_triangles
    ) t
    GROUP BY node_a
    ORDER BY triangles DESC
    LIMIT 5
""")

print("\nFornecedores em mais triangulos:")
for node, count in cur.fetchall():
    print(f"  {node[:45]:<47} {count:>3} triangulos")

conn.close()

print("\n" + "=" * 80)
print("✓ Graph Engine v2 concluido!")
print("=" * 80)
print("\nTabelas criadas:")
print("  - graph_communities (comunidades Louvain)")
print("  - graph_pagerank (influencia)")
print("  - graph_triangles (possiveis carteis)")
PYEND

python graph_v2.py
