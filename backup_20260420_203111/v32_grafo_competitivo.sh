#!/bin/bash
# v3.2 - Grafo Hibrido Competitivo (PMI + Competicao + Anti-coexistencia)

cat > v32_competitivo.py << 'ENDOFFILE'
import os
import psycopg2
import math
import networkx as nx
from networkx.algorithms.community import louvain_communities
from collections import defaultdict, Counter

print("=" * 80)
print("v3.2 - GRAFO HIBRIDO COMPETITIVO")
print("Peso = 0.5*PMI + 0.3*Competicao + 0.2*Anti-coexistencia")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 1. Coletar dados brutos de co-ocorrencia
print("\n[1/5] Coletando dados de contexto...")
cur.execute("""
    SELECT orgao, SUBSTRING(data_assinatura FROM 4 FOR 2) as mes,
           COUNT(DISTINCT fornecedor) as num_fornecedores,
           COUNT(*) as num_contratos
    FROM sp_contratos
    WHERE data_assinatura IS NOT NULL
    GROUP BY orgao, mes
""")

contextos = cur.fetchall()
print(f"Contextos (orgao + mes): {len(contextos)}")

# Calcular raridade de cada contexto
raridade_contexto = {}
for org, mes, num_forn, num_contr in contextos:
    chave = f"{org}__{mes}"
    # Contextos com poucos fornecedores sao mais raros/competitivos
    raridade_contexto[chave] = 1.0 / math.log(1 + num_forn) if num_forn > 0 else 0

# 2. Coletar co-ocorrencias detalhadas
print("\n[2/5] Calculando PMI e pesos competitivos...")

cur.execute("""
    SELECT 
        a.fornecedor as forn_a,
        b.fornecedor as forn_b,
        a.orgao,
        SUBSTRING(a.data_assinatura FROM 4 FOR 2) as mes,
        COUNT(*) as coocorrencias
    FROM sp_contratos a
    JOIN sp_contratos b ON a.orgao = b.orgao 
        AND SUBSTRING(a.data_assinatura FROM 4 FOR 2) = SUBSTRING(b.data_assinatura FROM 4 FOR 2)
    WHERE a.fornecedor < b.fornecedor
      AND a.data_assinatura IS NOT NULL
    GROUP BY a.fornecedor, b.fornecedor, a.orgao, SUBSTRING(a.data_assinatura FROM 4 FOR 2)
    HAVING COUNT(*) >= 2
""")

raw_edges = cur.fetchall()
print(f"Co-ocorrencias brutas: {len(raw_edges)}")

# Calcular frequencias marginais
fornecedor_contextos = defaultdict(set)
contexto_fornecedores = defaultdict(set)

for forn_a, forn_b, org, mes, cooc in raw_edges:
    chave = f"{org}__{mes}"
    fornecedor_contextos[forn_a].add(chave)
    fornecedor_contextos[forn_b].add(chave)
    contexto_fornecedores[chave].add(forn_a)
    contexto_fornecedores[chave].add(forn_b)

# Calcular PMI e pesos competitivos
print("\n[3/5] Calculando pesos hibridos...")

edges_ponderados = []
for forn_a, forn_b, org, mes, cooc in raw_edges:
    chave = f"{org}__{mes}"
    
    # P(A) - frequencia marginal de A
    contexts_a = len(fornecedor_contextos[forn_a])
    contexts_b = len(fornecedor_contextos[forn_b])
    contexts_total = len(contexto_fornecedores)
    
    if contexts_a > 0 and contexts_b > 0 and contexts_total > 0:
        P_A = contexts_a / contexts_total
        P_B = contexts_b / contexts_total
        P_AB = cooc / contexts_total
        
        # PMI (Pointwise Mutual Information)
        if P_AB > 0 and P_A * P_B > 0:
            pmi = math.log(P_AB / (P_A * P_B))
        else:
            pmi = 0
    else:
        pmi = 0
    
    # Competicao - contexto com muitos fornecedores = mais competitivo
    num_forn_no_contexto = len(contexto_fornecedores.get(chave, []))
    pressao_competitiva = math.log(1 + num_forn_no_contexto) / 5  # Normalizar
    
    # Anti-coexistencia - raridade do contexto
    anti_coexist = raridade_contexto.get(chave, 0)
    
    # Peso hibrido final
    peso = (
        0.5 * max(0, pmi) +           # PMI (associação inesperada)
        0.3 * pressao_competitiva +    # Competicao
        0.2 * anti_coexist             # Anti-coexistencia (raridade)
    )
    
    edges_ponderados.append((forn_a, forn_b, peso, pmi, pressao_competitiva, anti_coexist))

print(f"Edges calculados: {len(edges_ponderados)}")

# 4. Construir grafo e filtrar
print("\n[4/5] Construindo grafo competitivo...")

# Calcular threshold adaptativo
pesos = [e[2] for e in edges_ponderados]
peso_medio = sum(pesos) / len(pesos) if pesos else 0
peso_std = (sum((w - peso_medio)**2 for w in pesos) / len(pesos))**0.5 if pesos else 1
threshold = peso_medio + 0.5 * peso_std  # Um pouco acima da media

print(f"Peso medio: {peso_medio:.3f}, Desvio: {peso_std:.3f}")
print(f"Threshold: {threshold:.3f}")

G = nx.Graph()
for forn_a, forn_b, peso, pmi, comp, anti in edges_ponderados:
    if peso >= threshold:
        if G.has_edge(forn_a, forn_b):
            G[forn_a][forn_b]["weight"] += peso
        else:
            G.add_edge(forn_a, forn_b, weight=peso, pmi=pmi, comp=comp, anti=anti)

print(f"Grafo apos filtro: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# 5. Detectar comunidades
print("\n[5/5] Detectando comunidades competitivas...")

if G.number_of_edges() > 0:
    communities = louvain_communities(G, weight="weight", seed=42)
    print(f"Clusters competitivos: {len(communities)}")
    
    # Mapear fornecedores para clusters
    fornecedor_cluster = {}
    cluster_fornecedores = {}
    
    for cid, nodes in enumerate(communities):
        if len(nodes) >= 5:  # Minimo 5 fornecedores
            cluster_fornecedores[cid] = nodes
            for node in nodes:
                fornecedor_cluster[node] = cid
    
    print(f"Clusters validos (>=5): {len(cluster_fornecedores)}")
    
    # 6. Calcular metricas por cluster
    cur.execute("SELECT fornecedor, COUNT(*), SUM(valor) FROM sp_contratos GROUP BY fornecedor")
    fornecedor_stats = {f: (q, v) for f, q, v in cur.fetchall()}
    
    # Analisar dominio em cada cluster
    print("\n" + "=" * 80)
    print("ANALISE DE DOMINIO POR CLUSTER COMPETITIVO")
    print("=" * 80)
    
    casos = []
    
    for cid, fornecedores in cluster_fornecedores.items():
        total_contratos_cluster = sum(fornecedor_stats.get(f, (0, 0))[0] for f in fornecedores)
        
        if total_contratos_cluster == 0:
            continue
        
        print(f"\nCluster {cid}: {len(fornecedores)} fornecedores")
        
        # Calcular dominio de cada fornecedor no cluster
        dominios = []
        for forn in fornecedores:
            contratos = fornecedor_stats.get(forn, (0, 0))[0]
            if contratos > 0:
                dominio = contratos / total_contratos_cluster
                dominios.append((forn, dominio, contratos))
        
        dominios.sort(key=lambda x: x[1], reverse=True)
        
        # Top 3 do cluster
        for i, (forn, dom, contr) in enumerate(dominios[:3], 1):
            score = dom
            if len(fornecedores) <= 10 and dom > 0.3:
                score += 0.15  # Boost para dominio em cluster pequeno
            if dom > 0.4:
                casos.append({
                    'forn': forn,
                    'cluster': cid,
                    'dominio': dom,
                    'cluster_size': len(fornecedores),
                    'score': min(score, 1.0)
                })
            
            nivel = "🔴" if dom >= 0.40 else "🟡" if dom >= 0.25 else "⚡"
            print(f"  {i}. {forn[:35]:<37} {dom*100:>5.1f}% {contr:>5} contratos {nivel}")
    
    # Resultados finais
    print("\n" + "=" * 80)
    print("CASOS DE ALTO RISCO")
    print("=" * 80)
    
    casos.sort(key=lambda x: x['score'], reverse=True)
    
    altos = [c for c in casos if c['score'] >= 0.50]
    
    if altos:
        print(f"\n{len(altos)} casos de ALTO risco:")
        for i, c in enumerate(altos[:10], 1):
            print(f"{i:2d}. {c['forn'][:40]}")
            print(f"    Cluster {c['cluster']} ({c['cluster_size']} fornecedores)")
            print(f"    Dominio: {c['dominio']*100:.1f}% | Score: {c['score']:.3f}")
    else:
        print("\n⚠️ Nenhum caso ALTO detectado")
        print("   Sugestao: ajustar thresholds ou verificar densidade do grafo")
    
else:
    print("⚠️ Grafo vazio apos filtro - relaxar threshold")

conn.close()
print("\n" + "=" * 80)
print("✓ v3.2 concluido!")
print("=" * 80)
ENDOFFILE

python v32_competitivo.py
