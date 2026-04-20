#!/bin/bash
# v3.3 - Grafo Nao-Destilado (Manter informacao, usar pesos)

cat > v33_nao_destilado.py << 'ENDOFFILE'
import os
import psycopg2
import math
import networkx as nx
from networkx.algorithms.community import louvain_communities
from collections import defaultdict

print("=" * 80)
print("v3.3 - GRAFO NAO-DESTILADO")
print("Manter dados, usar pesos continuos, detectar por contraste")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 1. Carregar TODAS as co-ocorrencias (sem filtro de peso)
print("\n[1/4] Carregando grafo completo...")
cur.execute("""
    SELECT node_a, node_b, weight 
    FROM graph_edges 
    WHERE relation_type = 'co_occurrence_temporal'
    -- SEM filtro de peso minimo!
""")

edges_raw = cur.fetchall()
print(f"Arestas brutas: {len(edges_raw)}")

# 2. Construir grafo com pesos (sem filtrar)
G = nx.Graph()
for a, b, w in edges_raw:
    if G.has_edge(a, b):
        G[a][b]["weight"] += w
    else:
        G.add_edge(a, b, weight=w)

print(f"Grafo: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# 3. Calcular PMI para todas as arestas (enriquecer, nao filtrar)
print("\n[2/4] Calculando PMI (enriquecimento)...")

# Frequencias marginais
forn_conexoes = defaultdict(int)
for a, b, w in edges_raw:
    forn_conexoes[a] += w
    forn_conexoes[b] += w

total_conexoes = sum(forn_conexoes.values()) / 2

# Enriquecer arestas com PMI
for a, b, data in G.edges(data=True):
    w = data['weight']
    
    # P(A), P(B), P(AB)
    P_A = forn_conexoes[a] / total_conexoes if total_conexoes > 0 else 0
    P_B = forn_conexoes[b] / total_conexoes if total_conexoes > 0 else 0
    P_AB = w / total_conexoes if total_conexoes > 0 else 0
    
    # PMI (pode ser negativo, mas usamos para enriquecer)
    if P_AB > 0 and P_A * P_B > 0:
        pmi = math.log2(P_AB / (P_A * P_B))
    else:
        pmi = 0
    
    # Peso final: original + PMI normalizado (sem filtrar!)
    peso_enriquecido = w * (1 + max(0, pmi) / 10)  # Boost por PMI, nao filtro
    G[a][b]['weight_enriched'] = peso_enriquecido

print(f"✓ Arestas enriquecidas com PMI")

# 4. Clusterizacao com grafo completo
print("\n[3/4] Clusterizacao (grafo completo)...")

communities = louvain_communities(G, weight="weight_enriched", seed=42)
print(f"Clusters detectados: {len(communities)}")

# Mapear fornecedores para clusters
fornecedor_cluster = {}
cluster_fornecedores = {}

for cid, nodes in enumerate(communities):
    cluster_fornecedores[cid] = nodes
    for node in nodes:
        fornecedor_cluster[node] = cid

print(f"Fornecedores em clusters: {len(fornecedor_cluster)}")

# 5. Carregar dados de contratos
print("\n[4/4] Calculando contraste por cluster...")

cur.execute("""
    SELECT fornecedor, COUNT(*) as qtd, SUM(valor) as val
    FROM sp_contratos
    GROUP BY fornecedor
""")

fornecedor_stats = {f: (q, v) for f, q, v in cur.fetchall()}

# 6. Detectar anomalias por CONTRASTE interno ao cluster
print("\n" + "=" * 80)
print("ANOMALIAS POR CONTRASTE EM CLUSTER")
print("=" * 80)

casos = []

for cid, fornecedores in cluster_fornecedores.items():
    if len(fornecedores) < 3:  # Ignorar clusters muito pequenos
        continue
    
    # Calcular estatisticas do cluster
    stats_cluster = []
    for f in fornecedores:
        if f in fornecedor_stats:
            q, v = fornecedor_stats[f]
            stats_cluster.append((f, q, v))
    
    if len(stats_cluster) < 3:
        continue
    
    # Calcular mediana e desvio do cluster
    contratos_list = [s[1] for s in stats_cluster]
    contratos_list.sort()
    mediana = contratos_list[len(contratos_list)//2]
    media = sum(contratos_list) / len(contratos_list)
    
    # Detectar outliers (contraste interno)
    for f, q, v in stats_cluster:
        # Z-score de contratos no cluster
        if media > 0:
            z_score = (q - media) / (media * 0.5 + 1)  # Desvio relativo
        else:
            z_score = 0
        
        # Score baseado em contraste
        if z_score > 1.5:  # Significativamente acima da media do cluster
            score = min(0.5 + (z_score - 1.5) * 0.2, 1.0)
            
            # Boost para dominio absoluto no cluster
            dominio_cluster = q / sum(contratos_list) if sum(contratos_list) > 0 else 0
            if dominio_cluster > 0.4:
                score += 0.15
            
            casos.append({
                'forn': f,
                'cluster': cid,
                'cluster_size': len(fornecedores),
                'contratos': q,
                'media_cluster': media,
                'z_score': z_score,
                'dominio_cluster': dominio_cluster,
                'score': min(score, 1.0)
            })

# Ordenar por score
casos.sort(key=lambda x: x['score'], reverse=True)

# Exibir resultados
print(f"\n{'#':<4} {'Fornecedor':<35} {'Cluster':<8} {'Contr':>6} {'MediaClu':>8} {'Z':>5} {'Dom%':>6} {'Score':>6} {'Nivel':<8}")
print("-" * 95)

for i, c in enumerate(casos[:20], 1):
    if c['score'] >= 0.70:
        nivel = "🔴 ALTO"
    elif c['score'] >= 0.50:
        nivel = "🟡 MEDIO"
    elif c['score'] >= 0.35:
        nivel = "⚡ ATENCAO"
    else:
        nivel = "🟢 BAIXO"
    
    print(f"{i:<4} {c['forn'][:33]:<35} {c['cluster']:<8} {c['contratos']:>6} {c['media_cluster']:>8.1f} {c['z_score']:>5.2f} {c['dominio_cluster']*100:>5.1f}% {c['score']:>6.3f} {nivel:<8}")

# Estatisticas
print("\n" + "=" * 80)
altos = len([c for c in casos if c['score'] >= 0.70])
medios = len([c for c in casos if 0.50 <= c['score'] < 0.70])
atencao = len([c for c in casos if 0.35 <= c['score'] < 0.50])

print(f"🔴 Alto Risco (>=0.70): {altos}")
print(f"🟡 Medio Risco (0.50-0.70): {medios}")
print(f"⚡ Atencao (0.35-0.50): {atencao}")
print(f"🟢 Baixo (<0.35): {len(casos) - altos - medios - atencao}")
print(f"\nTotal casos: {len(casos)}")

if altos > 0:
    print(f"\n✅ SUCESSO: {altos} casos ALTO detectados!")
    print("Sistema agora detecta anomalias por CONTRASTE.")
elif len(casos) > 100:
    print(f"\n⚠️ {len(casos)} casos, mas nenhum ALTO")
    print("Ajustar threshold de z-score ou dominio.")
else:
    print(f"\n⚠️ Poucos casos ({len(casos)}). Verificar dados.")

conn.close()
print("\n" + "=" * 80)
print("✓ v3.3 Nao-Destilado concluido!")
print("=" * 80)
ENDOFFILE

python v33_nao_destilado.py
