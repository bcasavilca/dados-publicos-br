#!/bin/bash
# v3.4 - Baseline Dinamico Temporal por Cluster
# Normalizacao final: comparacao contra comportamento esperado no tempo

cat > v34_baseline_temporal.py << 'ENDOFFILE'
import os
import psycopg2
import math
import networkx as nx
from networkx.algorithms.community import louvain_communities
from collections import defaultdict

print("=" * 80)
print("v3.4 - BASELINE DINAMICO TEMPORAL")
print("Comparacao contra comportamento esperado no tempo")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 1. Carregar grafo completo e clusterizar
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

# 2. Carregar dados temporais completos
print("\n[2/4] Dados temporais por cluster/mes...")
cur.execute("""
    SELECT fornecedor, orgao, SUBSTRING(data_assinatura FROM 4 FOR 2) as mes,
           COUNT(*) as contratos
    FROM sp_contratos 
    WHERE data_assinatura IS NOT NULL
    GROUP BY fornecedor, orgao, SUBSTRING(data_assinatura FROM 4 FOR 2)
""")

# Organizar por cluster, orgao, mes
cluster_orgao_mes = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
fornecedor_dados = {}

for forn, org, mes, contr in cur.fetchall():
    if forn in fornecedor_cluster:
        cid = fornecedor_cluster[forn]
        cluster_orgao_mes[cid][org][mes][forn] = contr
        if forn not in fornecedor_dados:
            fornecedor_dados[forn] = {'total': 0, 'por_mes': defaultdict(int)}
        fornecedor_dados[forn]['total'] += contr
        fornecedor_dados[forn]['por_mes'][mes] += contr

print(f"Fornecedores com dados temporais: {len(fornecedor_dados)}")

# 3. Calcular baseline temporal por cluster
print("\n[3/4] Calculando baseline temporal...")

cluster_baselines = {}

for cid, orgaos in cluster_orgao_mes.items():
    # Para cada cluster, calcular dominancia por fornecedor ao longo do tempo
    fornecedor_dominancia = defaultdict(list)
    
    for org, meses in orgaos.items():
        for mes, fornecedores in meses.items():
            total_no_contexto = sum(fornecedores.values())
            if total_no_contexto == 0:
                continue
            
            for forn, contr in fornecedores.items():
                dominancia = contr / total_no_contexto
                fornecedor_dominancia[forn].append({
                    'mes': mes,
                    'org': org,
                    'contratos': contr,
                    'dominancia': dominancia,
                    'total_contexto': total_no_contexto
                })
    
    # Calcular baseline de dominancia para o cluster
    todas_dominancias = []
    estabilidade_por_forn = {}
    
    for forn, historico in fornecedor_dominancia.items():
        if len(historico) >= 2:  # Precisa de pelo menos 2 meses
            dominancias = [h['dominancia'] for h in historico]
            media_dom = sum(dominancias) / len(dominancias)
            var_dom = sum((d - media_dom)**2 for d in dominancias) / len(dominancias)
            
            todas_dominancias.extend(dominancias)
            
            # Coeficiente de variacao (estabilidade)
            cv = (var_dom ** 0.5) / media_dom if media_dom > 0 else 0
            estabilidade_por_forn[forn] = {
                'media': media_dom,
                'var': var_dom,
                'cv': cv,
                'num_meses': len(historico),
                'historico': historico
            }
    
    if todas_dominancias:
        baseline_media = sum(todas_dominancias) / len(todas_dominancias)
        baseline_std = (sum((d - baseline_media)**2 for d in todas_dominancias) / len(todas_dominancias)) ** 0.5
    else:
        baseline_media = 0.1
        baseline_std = 0.05
    
    cluster_baselines[cid] = {
        'media': baseline_media,
        'std': baseline_std,
        'fornecedores': estabilidade_por_forn
    }
    
    print(f"  Cluster {cid}: baseline={baseline_media:.3f}, std={baseline_std:.3f}, {len(estabilidade_por_forn)} forns com historico")

# 4. Calcular score final com baseline temporal
print("\n[4/4] Calculando scores com baseline temporal...")

casos = []

for cid, baseline in cluster_baselines.items():
    for forn, stats in baseline['fornecedores'].items():
        media_dom = stats['media']
        num_meses = stats['num_meses']
        
        # Anomalia relativa ao baseline do cluster
        if baseline['std'] > 0:
            anomalia = (media_dom - baseline['media']) / baseline['std']
        else:
            anomalia = 0
        
        # Penalizacao por estabilidade excessiva (monopolio legitimo)
        cv = stats['cv']
        if cv < 0.3 and num_meses >= 4:
            # Muito estavel por muitos meses = provavelmente legitimo
            fator_estabilidade = 0.6
        elif cv < 0.5:
            fator_estabilidade = 0.8
        else:
            fator_estabilidade = 1.0
        
        # Variacao temporal (quanto mais abrupta, maior)
        variacao_temporal = max(0, 1 - cv)  # Baixa estabilidade = alta variacao
        
        # Score final SEM SATURACAO
        if anomalia > 0:
            score = math.log(1 + max(0, anomalia)) * fator_estabilidade * (1 + variacao_temporal * 0.3)
        else:
            score = 0
        
        # So incluir se anomalia significativa
        if anomalia > 1.5:
            casos.append({
                'forn': forn,
                'cluster': cid,
                'media_dominancia': media_dom,
                'baseline_cluster': baseline['media'],
                'anomalia': anomalia,
                'cv': cv,
                'fator_est': fator_estabilidade,
                'meses': num_meses,
                'total_contratos': fornecedor_dados.get(forn, {}).get('total', 0),
                'score': score
            })

# Ordenar por score
casos.sort(key=lambda x: x['score'], reverse=True)

# Exibir resultados
print("\n" + "=" * 100)
print("RANKING INVESTIGATIVO v3.4")
print("=" * 100)
print(f"{'#':<4} {'Fornecedor':<35} {'Clu':<4} {'Contr':<6} {'Dom%':<6} {'Anom':<6} {'CV':<5} {'Mes':<4} {'Score':<8} {'Nivel':<8}")
print("-" * 100)

for i, c in enumerate(casos[:20], 1):
    if c['score'] >= 2.0:
        nivel = "🔴 ALTO"
    elif c['score'] >= 1.0:
        nivel = "🟡 MED"
    elif c['score'] >= 0.5:
        nivel = "⚡ ATN"
    else:
        nivel = "🟢 BAIXO"
    
    print(f"{i:<4} {c['forn'][:33]:<35} {c['cluster']:<4} {c['total_contratos']:<6} "
          f"{c['media_dominancia']*100:<5.1f}% {c['anomalia']:<5.2f} {c['cv']:<4.2f} "
          f"{c['meses']:<4} {c['score']:<7.3f} {nivel:<8}")

# Estatisticas
print("\n" + "=" * 100)
altos = len([c for c in casos if c['score'] >= 2.0])
medios = len([c for c in casos if 1.0 <= c['score'] < 2.0])
atencao = len([c for c in casos if 0.5 <= c['score'] < 1.0])

print(f"🔴 Alto Risco (>=2.0):     {altos:3d} casos")
print(f"🟡 Medio Risco (1.0-2.0): {medios:3d} casos")
print(f"⚡ Atencao (0.5-1.0):     {atencao:3d} casos")
print(f"🟢 Baixo (<0.5):          {len(casos) - altos - medios - atencao:3d} casos")
print(f"\nTotal analisado: {len(casos)} fornecedores")

# Verificar se scores estao variados (nao saturados)
scores = [c['score'] for c in casos]
if scores:
    score_min = min(scores)
    score_max = max(scores)
    score_media = sum(scores) / len(scores)
    print(f"\nDistribuicao de scores: min={score_min:.3f}, max={score_max:.3f}, media={score_media:.3f}")
    
    if score_max < 3.0 and score_max > 1.5:
        print("✅ Scores bem distribuidos (sem saturacao)")
    elif score_max >= 3.0:
        print("⚠️ Scores muito altos - revisar formula")
    else:
        print("⚠️ Scores muito baixos - baseline muito rigido")

conn.close()
print("\n" + "=" * 100)
print("✓ v3.4 Baseline Dinamico Temporal concluido!")
print("=" * 100)
ENDOFFILE

python v34_baseline_temporal.py
