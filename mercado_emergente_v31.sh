#!/bin/bash
# v3.1 Mercado Emergente - Clusters como Unidade de Analise

cat > mercado_v31.py << 'PYEND'
import os
import psycopg2
import networkx as nx
from networkx.algorithms.community import louvain_communities
from collections import defaultdict

print("=" * 80)
print("v3.1 - MERCADO EMERGENTE (Clusters como Unidade de Analise)")
print("Mudando de: fornecedor vs prefeitura")
print("Para: fornecedor vs mercado real (cluster)")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 1. Carregar grafo de co-ocorrencia
print("\n[1/5] Carregando grafo...")
cur.execute("""
    SELECT node_a, node_b, weight 
    FROM graph_edges 
    WHERE relation_type = 'co_occurrence_temporal'
    AND weight >= 5
""")

G = nx.Graph()
for a, b, w in cur.fetchall():
    if G.has_edge(a, b):
        G[a][b]["weight"] += w
    else:
        G.add_edge(a, b, weight=w)

print(f"✓ Grafo: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# 2. Detectar comunidades (mercados emergentes)
print("\n[2/5] Detectando comunidades (Louvain)...")

communities = louvain_communities(G, weight="weight", seed=42)

print(f"✓ {len(communities)} mercados emergentes detectados")

# Mapear fornecedor -> cluster
fornecedor_cluster = {}
cluster_fornecedores = defaultdict(set)

for cid, nodes in enumerate(communities):
    for node in nodes:
        fornecedor_cluster[node] = cid
        cluster_fornecedores[cid].add(node)

# 3. Calcular metricas por cluster
print("\n[3/5] Calculando metricas por mercado...")

# Coletar dados de contratos por fornecedor
cur.execute("""
    SELECT fornecedor, orgao, COUNT(*) as contratos, SUM(valor) as total_valor
    FROM sp_contratos
    GROUP BY fornecedor, orgao
""")

fornecedor_orgao = defaultdict(lambda: defaultdict(int))
fornecedor_total = defaultdict(int)

for forn, org, qtd, val in cur.fetchall():
    fornecedor_orgao[forn][org] = qtd
    fornecedor_total[forn] += qtd

# Calcular metricas por cluster
cluster_metricas = {}

for cid, fornecedores in cluster_fornecedores.items():
    total_contratos_cluster = sum(fornecedor_total.get(f, 0) for f in fornecedores)
    num_fornecedores = len(fornecedores)
    
    cluster_metricas[cid] = {
        'fornecedores': fornecedores,
        'total_contratos': total_contratos_cluster,
        'num_fornecedores': num_fornecedores,
        'contrato_por_fornecedor': total_contratos_cluster / num_fornecedores if num_fornecedores > 0 else 0
    }

print(f"✓ Metricas calculadas para {len(cluster_metricas)} mercados")

# 4. Calcular domínio e anomalias por fornecedor
print("\n[4/5] Calculando dominio relativo e anomalias...")

casos = []

for forn, cid in fornecedor_cluster.items():
    if forn not in fornecedor_total:
        continue
    
    contratos_forn = fornecedor_total[forn]
    cluster = cluster_metricas[cid]
    
    # Dominio relativo ao cluster (mercado real)
    if cluster['total_contratos'] > 0:
        dominio_cluster = contratos_forn / cluster['total_contratos']
    else:
        dominio_cluster = 0
    
    # Competicao no cluster
    competicao = cluster['num_fornecedores']
    
    # Concentracao: se cluster pequeno e dominio alto = suspeito
    concentracao = dominio_cluster * (1 / competicao if competicao > 0 else 0)
    
    # Score de anomalia
    score_base = dominio_cluster
    
    # Boost: fornecedor dominante em cluster pequeno
    if competicao <= 5 and dominio_cluster > 0.5:
        boost = 0.2
    elif competicao <= 10 and dominio_cluster > 0.4:
        boost = 0.1
    else:
        boost = 0
    
    score_final = min(score_base + boost, 1.0)
    
    # Apenas fornecedores com score significativo
    if score_final >= 0.30:
        casos.append({
            'forn': forn,
            'cluster_id': cid,
            'cluster_size': competicao,
            'dominio_cluster': dominio_cluster,
            'contratos': contratos_forn,
            'score': score_final,
            'mercado': f"Cluster-{cid} ({competicao} fornecedores)"
        })

# 5. Exibir resultados
print("\n" + "=" * 80)
print("CASOS INVESTIGAVEIS (Mercado Emergente)")
print("=" * 80)

# Ordenar por score
casos.sort(key=lambda x: x['score'], reverse=True)

print(f"\n{'#':<4} {'Fornecedor':<35} {'Mercado':<20} {'Dom%':>6} {'Score':>7} {'Nivel':<10}")
print("-" * 90)

for i, c in enumerate(casos[:20], 1):
    if c['score'] >= 0.70:
        nivel = "🔴 ALTO"
    elif c['score'] >= 0.50:
        nivel = "🟡 MEDIO"
    else:
        nivel = "⚡ ATENCAO"
    
    print(f"{i:<4} {c['forn'][:33]:<35} {c['mercado'][:18]:<20} {c['dominio_cluster']*100:>5.1f}% {c['score']:>7.3f} {nivel:<10}")

# Estatisticas
print("\n" + "=" * 80)
print("ESTATISTICAS")
print("=" * 80)

altos = len([c for c in casos if c['score'] >= 0.70])
medios = len([c for c in casos if 0.50 <= c['score'] < 0.70])
atencao = len([c for c in casos if 0.30 <= c['score'] < 0.50])

print(f"\n🔴 Alto risco (>=0.70): {altos}")
print(f"🟡 Medio risco (0.50-0.70): {medios}")
print(f"⚡ Atencao (0.30-0.50): {atencao}")
print(f"\nTotal casos gerados: {len(casos)}")
print(f"Reducao vs v3.0: {(1 - len(casos)/12069)*100:.1f}%" if len(casos) < 12069 else "N/A")

# Top clusters suspeitos
print("\n" + "=" * 80)
print("CLUSTERS COM MAIS ANOMALIAS")
print("=" * 80)

cluster_alertas = defaultdict(list)
for c in casos:
    if c['score'] >= 0.50:
        cluster_alertas[c['cluster_id']].append(c)

for cid, alertas in sorted(cluster_alertas.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
    cm = cluster_metricas[cid]
    print(f"\nCluster {cid}: {cm['num_fornecedores']} fornecedores, {cm['total_contratos']} contratos")
    print(f"  {len(alertas)} alertas: ", end="")
    for a in alertas[:3]:
        print(f"{a['forn'][:20]}... (score {a['score']:.2f})", end=" | ")
    print()

conn.close()

print("\n" + "=" * 80)
print("✓ v3.1 Mercado Emergente concluido!")
print("=" * 80)
print("\nUnidade de analise: mercado real (cluster), nao prefeitura global")
print("Domino calculado dentro do contexto competitivo real")
PYEND

python mercado_v31.py
