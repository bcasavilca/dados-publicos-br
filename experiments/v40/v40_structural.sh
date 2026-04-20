#!/bin/bash
# v4.0 - Structural Network System (Nivel 3 + Nivel 4)

cat > v40_structural.py << 'ENDOFFILE'
import os
import psycopg2
import math
import networkx as nx
from collections import defaultdict
from networkx.algorithms.community import louvain_communities

print("=" * 100)
print("v4.0 - STRUCTURAL NETWORK SYSTEM (N3 + N4)")
print("Categorizacao + Rede + Clusters")
print("=" * 100)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# 1. LOAD DATA
print("\n[1/4] Carregando dados...")

cur.execute("""
    SELECT fornecedor, orgao, objeto, COUNT(*)
    FROM sp_contratos
    WHERE data_assinatura IS NOT NULL
    GROUP BY fornecedor, orgao, objeto
""")

rows = cur.fetchall()
print(f"Registros carregados: {len(rows)}")

# 2. NIVEL 3 - CATEGORIZACAO
print("\n[2/4] Classificando categorias...")

def classify(obj):
    obj = (obj or "").lower()
    if any(x in obj for x in ["obra", "constru", "paviment", "engenharia", "reforma"]):
        return "INFRA"
    if any(x in obj for x in ["software", "ti", "sistema", "tecnologia", "informatica", "licenca"]):
        return "TI"
    if any(x in obj for x in ["evento", "show", "cultural", "producao", "artistica", "festival"]):
        return "EVENTOS"
    if any(x in obj for x in ["saude", "hospital", "medic", "clinica", "farmacia", "vacina"]):
        return "SAUDE"
    if any(x in obj for x in ["alimento", "merenda", "refeicao", "nutricao", "restaurante"]):
        return "ALIMENTACAO"
    if any(x in obj for x in ["transporte", "veiculo", "onibus", "combustivel", "locacao"]):
        return "TRANSPORTE"
    return "SERVICOS"

forn_cat = defaultdict(lambda: defaultdict(int))
org_cat = defaultdict(lambda: defaultdict(int))

for f, o, obj, c in rows:
    cat = classify(obj)
    forn_cat[f][cat] += c
    org_cat[o][cat] += c

print(f"Fornecedores categorizados: {len(forn_cat)}")

# 3. NIVEL 4 - REDE FORNECEDOR <-> ORGAO
print("\n[3/4] Construindo redes...")

# Grafo bipartido fornecedor-orao
B = nx.Graph()

for f, o, obj, c in rows:
    if B.has_edge(f, o):
        B[f][o]["weight"] += c
    else:
        B.add_edge(f, o, weight=c)

# Projecao fornecedor-fornecedor (co-ocorrencia no mesmo orgao)
F = nx.Graph()

org_to_forn = defaultdict(set)
for f, o, obj, c in rows:
    org_to_forn[o].add(f)

for org, forn_list in org_to_forn.items():
    forn_list = list(forn_list)
    for i in range(len(forn_list)):
        for j in range(i + 1, len(forn_list)):
            a, b = forn_list[i], forn_list[j]
            if F.has_edge(a, b):
                F[a][b]["weight"] += 1
            else:
                F.add_edge(a, b, weight=1)

print(f"Rede fornecedor-fornecedor: {F.number_of_nodes()} nodes, {F.number_of_edges()} edges")

# Clusters com Louvain
if F.number_of_edges() > 0:
    clusters = louvain_communities(F, weight="weight", seed=42)
    node_cluster = {}
    for cid, nodes in enumerate(clusters):
        for n in nodes:
            node_cluster[n] = cid
    print(f"Clusters encontrados: {len(clusters)}")
else:
    node_cluster = {}
    print("Aviso: Grafo vazio, sem clusters")

# 4. SCORING ESTRUTURAL
print("\n[4/4] Calculando score estrutural...")

casos = []

for f in forn_cat:
    total = sum(forn_cat[f].values())
    if total == 0:
        continue

    # Concentracao por categoria
    cats = forn_cat[f]
    max_cat = max(cats.values()) / total
    cat_dominante = max(cats, key=cats.get)

    # Rede
    degree = F.degree(f) if f in F else 0
    cluster = node_cluster.get(f, -1)

    # Centralidade simples (normalizada)
    max_degree = max(dict(F.degree()).values()) if F.number_of_nodes() > 0 else 1
    centrality = degree / (max_degree + 10) if max_degree > 0 else 0

    # Score estrutural
    structural = (0.4 * max_cat) + (0.3 * centrality) + (0.3 * (1 if degree > 0 else 0))

    # Bonus de cluster
    cluster_bonus = 1.15 if cluster >= 0 else 1.0

    score = structural * cluster_bonus

    if score > 0.5:
        casos.append({
            "forn": f,
            "score": score,
            "cat": cat_dominante,
            "cat_conc": max_cat,
            "deg": degree,
            "cluster": cluster,
            "total": total
        })

# RESULTADO
casos.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 100)
print("RANKING v4.0 - STRUCTURAL NETWORK SYSTEM")
print("=" * 100)
print(f"{'#':<4} {'Fornecedor':<38} {'Cat':<10} {'Score':<7} {'Conc%':<6} {'Deg':<4} {'Clus':<5}")
print("-" * 100)

for i, c in enumerate(casos[:25], 1):
    nivel = "🔴" if c["score"] > 0.85 else "🟡" if c["score"] > 0.7 else "⚡"
    print(f"{i:<4} {c['forn'][:36]:<38} {c['cat']:<10} {c['score']:<7.3f} {c['cat_conc']*100:<6.1f} {c['deg']:<4} {c['cluster']:<5} {nivel}")

print("\n" + "=" * 100)
altos = len([c for c in casos if c["score"] > 0.85])
medios = len([c for c in casos if 0.7 < c["score"] <= 0.85])
atencao = len([c for c in casos if 0.5 < c["score"] <= 0.7])

print(f"🔴 ALTO (>0.85):     {altos:3d}")
print(f"🟡 MEDIO (0.70-0.85): {medios:3d}")
print(f"⚡ ATENCAO (0.50-0.70): {atencao:3d}")
print(f"\nTotal casos: {len(casos)}")

# Estatisticas por categoria
print("\nPor categoria:")
cat_stats = defaultdict(int)
for c in casos:
    cat_stats[c["cat"]] += 1
for cat in sorted(cat_stats.keys()):
    print(f"  {cat:<12}: {cat_stats[cat]} casos")

conn.close()
print("=" * 100)
print("✓ v4.0 Structural Network System concluido!")
ENDOFFILE

python v40_structural.py
