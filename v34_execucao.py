import os
import psycopg2
import math
import networkx as nx
from networkx.algorithms.community import louvain_communities
from collections import defaultdict

print("=" * 80)
print("v3.4 - BASELINE DINAMICO TEMPORAL (FINAL)")
print("=" * 80)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# 1. Grafo e clusters
print("\n[1/4] Grafo e clusters...")
cur.execute("SELECT node_a, node_b, weight FROM graph_edges WHERE relation_type='co_occurrence_temporal'")
edges_raw = cur.fetchall()

G = nx.Graph()
for a, b, w in edges_raw:
    if G.has_edge(a, b):
        G[a][b]["weight"] += w
    else:
        G.add_edge(a, b, weight=w)

communities = louvain_communities(G, weight="weight", seed=42)
print(f"Clusters: {len(communities)}")

fornecedor_cluster = {}
cluster_fornecedores = {}
for cid, nodes in enumerate(communities):
    cluster_fornecedores[cid] = nodes
    for node in nodes:
        fornecedor_cluster[node] = cid

# 2. Dados temporais
print("\n[2/4] Dados temporais...")
cur.execute("""SELECT fornecedor, orgao, SUBSTRING(data_assinatura FROM 4 FOR 2), COUNT(*) FROM sp_contratos WHERE data_assinatura IS NOT NULL GROUP BY fornecedor, orgao, SUBSTRING(data_assinatura FROM 4 FOR 2)""")

cluster_orgao_mes = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
fornecedor_dados = {}

for forn, org, mes, contr in cur.fetchall():
    if forn in fornecedor_cluster:
        cid = fornecedor_cluster[forn]
        cluster_orgao_mes[cid][org][mes][forn] = contr
        if forn not in fornecedor_dados:
            fornecedor_dados[forn] = {"total": 0, "por_mes": defaultdict(int)}
        fornecedor_dados[forn]["total"] += contr
        fornecedor_dados[forn]["por_mes"][mes] += contr

print(f"Fornecedores com dados: {len(fornecedor_dados)}")

# 3. Baseline temporal
print("\n[3/4] Baseline temporal...")
cluster_baselines = {}

for cid, orgaos in cluster_orgao_mes.items():
    fornecedor_dominancia = defaultdict(list)
    for org, meses in orgaos.items():
        for mes, fornecedores in meses.items():
            total = sum(fornecedores.values())
            if total == 0:
                continue
            for forn, contr in fornecedores.items():
                dominancia = contr / total
                fornecedor_dominancia[forn].append(dominancia)
    todas_dominancias = []
    estabilidade = {}
    for forn, doms in fornecedor_dominancia.items():
        if len(doms) >= 2:
            media = sum(doms) / len(doms)
            var = sum((d - media)**2 for d in doms) / len(doms)
            cv = (var ** 0.5) / media if media > 0 else 0
            todas_dominancias.extend(doms)
            estabilidade[forn] = {"media": media, "cv": cv, "num": len(doms)}
    if todas_dominancias:
        b_media = sum(todas_dominancias) / len(todas_dominancias)
        b_std = (sum((d - b_media)**2 for d in todas_dominancias) / len(todas_dominancias)) ** 0.5
    else:
        b_media, b_std = 0.1, 0.05
    cluster_baselines[cid] = {"media": b_media, "std": b_std, "fornecedores": estabilidade}

print(f"Baselines calculados para {len(cluster_baselines)} clusters")

# 4. Scores
print("\n[4/4] Calculando scores...")
casos = []

for cid, baseline in cluster_baselines.items():
    for forn, stats in baseline["fornecedores"].items():
        media_dom = stats["media"]
        cv = stats["cv"]
        num_meses = stats["num"]
        anomalia = (media_dom - baseline["media"]) / (baseline["std"] + 1e-6)
        if cv < 0.3 and num_meses >= 4:
            fator_est = 0.6
        elif cv < 0.5:
            fator_est = 0.8
        else:
            fator_est = 1.0
        variacao_temp = max(0, 1 - cv)
        if anomalia > 0:
            score = math.log(1 + max(0, anomalia)) * fator_est * (1 + variacao_temp * 0.3)
        else:
            score = 0
        if anomalia > 0.5:
            casos.append({
                "forn": forn, "cluster": cid, "dom": media_dom,
                "anom": anomalia, "cv": cv, "meses": num_meses,
                "total": fornecedor_dados.get(forn, {}).get("total", 0),
                "score": score
            })

casos.sort(key=lambda x: x["score"], reverse=True)

print("\n" + "=" * 100)
print("RANKING INVESTIGATIVO v3.4")
print("=" * 100)

for i, c in enumerate(casos[:20], 1):
    nivel = "🔴" if c["score"] >= 2.0 else "🟡" if c["score"] >= 1.0 else "⚡"
    print(f"{i:2d}. {c['forn'][:35]:<37} C{c['cluster']:<3} {c['total']:>5} {c['dom']*100:>5.1f}% {c['anom']:>5.2f} {c['cv']:>4.2f} {c['meses']:>3} {c['score']:>6.3f} {nivel}")

print("\n" + "=" * 100)
altos = len([c for c in casos if c["score"] >= 2.0])
medios = len([c for c in casos if 1.0 <= c["score"] < 2.0])
baixos = len([c for c in casos if 0.5 <= c["score"] < 1.0])
print(f"🔴 Alto (>=2.0): {altos} | 🟡 Medio (1.0-2.0): {medios} | ⚡ Baixo (0.5-1.0): {baixos} | Total: {len(casos)}")

if casos:
    scores = [c["score"] for c in casos]
    print(f"\nScore range: {min(scores):.3f} - {max(scores):.3f}")
    media_score = sum(scores) / len(scores)
    print(f"Score medio: {media_score:.3f}")

conn.close()
print("=" * 100)
print("✓ v3.4 Baseline Dinamico Temporal concluido!")
