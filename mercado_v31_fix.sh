#!/bin/bash
# v3.1 FIX - Mercado Emergente Corrigido

cat > mercado_v31_fix.py << 'ENDOFFILE'
import os
import psycopg2
import networkx as nx
from networkx.algorithms.community import louvain_communities
from collections import defaultdict

print("=" * 80)
print("v3.1 FIX - MERCADO EMERGENTE")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 1. Carregar grafo
print("\n[1/4] Carregando grafo...")
cur.execute("SELECT node_a, node_b, weight FROM graph_edges WHERE relation_type='co_occurrence_temporal' AND weight >= 2")

G = nx.Graph()
for a, b, w in cur.fetchall():
    if G.has_edge(a, b):
        G[a][b]["weight"] += w
    else:
        G.add_edge(a, b, weight=w)

print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

# 2. Comunidades
print("\n[2/4] Comunidades...")
communities = louvain_communities(G, weight="weight", seed=42)
print(f"Mercados: {len(communities)}")

fornecedor_cluster = {}
cluster_forn = defaultdict(set)
for cid, nodes in enumerate(communities):
    for node in nodes:
        fornecedor_cluster[node] = cid
        cluster_forn[cid].add(node)

# 3. Metricas
print("\n[3/4] Metricas...")
cur.execute("SELECT fornecedor, COUNT(*) FROM sp_contratos GROUP BY fornecedor")
fornecedor_total = {f: q for f, q in cur.fetchall()}

cluster_metricas = {}
for cid, forns in cluster_forn.items():
    total = sum(fornecedor_total.get(f, 0) for f in forns)
    cluster_metricas[cid] = {'total': total, 'num': len(forns)}

# 4. Calcular dominio
print("\n[4/4] Calculando...")
casos = []

for forn, cid in fornecedor_cluster.items():
    if forn not in fornecedor_total:
        continue
    
    contratos = fornecedor_total[forn]
    cluster = cluster_metricas[cid]
    
    if cluster['total'] > 0:
        dominio = contratos / cluster['total']
    else:
        dominio = 0
    
    competicao = cluster['num']
    
    score = dominio
    if competicao <= 5 and dominio > 0.3:
        score += 0.15
    elif competicao <= 10 and dominio > 0.25:
        score += 0.10
    
    score = min(score, 1.0)
    
    if score >= 0.15:
        casos.append({'forn': forn, 'cluster': cid, 'dominio': dominio, 'score': score})

# Exibir
casos.sort(key=lambda x: x['score'], reverse=True)

print("\n" + "=" * 80)
print("TOP 15 CASOS")
print("=" * 80)

for i, c in enumerate(casos[:15], 1):
    nivel = "🔴" if c['score'] >= 0.50 else "🟡" if c['score'] >= 0.30 else "⚡"
    print(f"{i:2d}. {c['forn'][:35]:<37} C{c['cluster']:<3} {c['dominio']*100:>5.1f}% {c['score']:>6.3f} {nivel}")

print("\n" + "=" * 80)
altos = len([c for c in casos if c['score'] >= 0.50])
medios = len([c for c in casos if 0.30 <= c['score'] < 0.50])
print(f"🔴 Alto: {altos} | 🟡 Medio: {medios} | Total: {len(casos)}")

conn.close()
print("=" * 80)
ENDOFFILE

python mercado_v31_fix.py
