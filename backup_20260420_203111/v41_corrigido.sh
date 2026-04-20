#!/bin/bash
# v4.1 - Correção Estrutural (Rede + Classificação + Score)

cat > v41_corrigido.py << 'ENDOFFILE'
import os
import psycopg2
import math
import networkx as nx
from collections import defaultdict
from networkx.algorithms.community import louvain_communities

print("=" * 100)
print("v4.1 - CORRECAO ESTRUTURAL")
print("Rede fornecedor-fornecedor + Classificação + Score variável")
print("=" * 100)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# 1. CARREGAR DADOS
print("\n[1/5] Carregando dados...")

cur.execute("""
    SELECT fornecedor, orgao, valor
    FROM sp_contratos
    WHERE data_assinatura IS NOT NULL
""")

rows = cur.fetchall()
print(f"Registros: {len(rows)}")

# 2. AGRUPAR POR FORNECEDOR E ORGAO
print("\n[2/5] Organizando dados...")

forn_org_val = defaultdict(lambda: defaultdict(float))
org_forn_set = defaultdict(set)

for f, o, v in rows:
    val = float(v) if v else 0
    forn_org_val[f][o] += val
    org_forn_set[o].add(f)

print(f"Fornecedores: {len(forn_org_val)}")
print(f"Orgaos: {len(org_forn_set)}")

# 3. CATEGORIZAR POR PADRAO DE ORGAO
print("\n[3/5] Categorizando...")

def classify_org(org_name):
    """Classifica orgao por tipo de gasto predominante"""
    org = (org_name or "").lower()
    
    # Saude
    if any(x in org for x in ["saude", "hospital", "vacina", "medic", "enferm", "ambulator", "maternidade"]):
        return "SAUDE"
    
    # Educacao
    if any(x in org for x in ["educ", "escola", "univers", "faculdade", "ensino", "creche", "biblioteca"]):
        return "EDUCACAO"
    
    # Infra/Obras
    if any(x in org for x in ["obra", "infra", "constru", "paviment", "predial", "reforma", "urban", "sanepar"]):
        return "INFRA"
    
    # TI/Tecnologia
    if any(x in org for x in ["tecno", "informatica", "digital", "software", "ti.", "inovacao"]):
        return "TI"
    
    # Eventos/Cultura
    if any(x in org for x in ["evento", "cultura", "turismo", "lazer", "esporte", "festa", "show"]):
        return "EVENTOS"
    
    # Social/Assistencia
    if any(x in org for x in ["social", "assistencia", "desenvolv", "habita", "bolsa", "renda", "familia"]):
        return "SOCIAL"
    
    # Seguranca
    if any(x in org for x in ["segur", "policia", "defesa", "guarda", "vigilancia", "bombeiro"]):
        return "SEGURANCA"
    
    # Transporte
    if any(x in org for x in ["transp", "mobilidade", "metro", "onibus", "veiculo", "transite"]):
        return "TRANSPORTE"
    
    # Meio Ambiente
    if any(x in org for x in ["meio ambiente", "sustentab", "verde", "ecologia", "limpeza urbana"]):
        return "MEIO_AMBIENTE"
    
    # Administrativo (default)
    return "ADMINISTRATIVO"

# Aplicar classificacao
forn_cat = defaultdict(lambda: defaultdict(float))
for f, orgs in forn_org_val.items():
    for o, val in orgs.items():
        cat = classify_org(o)
        forn_cat[f][cat] += val

# Contar distribuicao
from collections import Counter
cat_counts = Counter()
for cats in forn_cat.values():
    cat_counts[max(cats, key=cats.get)] += 1

print("Distribuicao por categoria:")
for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1])[:8]:
    print(f"  {cat}: {cnt}")

# 4. CONSTRUIR REDE FORNECEDOR-FORNECEDOR
print("\n[4/5] Construindo rede...")

# Rede: fornecedores conectados se atuam no mesmo orgao
F = nx.Graph()

for org, forn_set in org_forn_set.items():
    forn_list = list(forn_set)
    # Criar arestas entre todos os pares no mesmo orgao
    for i in range(len(forn_list)):
        for j in range(i + 1, len(forn_list)):
            a, b = forn_list[i], forn_list[j]
            # Peso = min(valor_a, valor_b) no orgao
            val_a = forn_org_val[a].get(org, 0)
            val_b = forn_org_val[b].get(org, 0)
            w = min(val_a, val_b) / 1000  # normalizar
            
            if F.has_edge(a, b):
                F[a][b]["weight"] += w
            else:
                F.add_edge(a, b, weight=w)

print(f"Rede: {F.number_of_nodes()} nodes, {F.number_of_edges()} edges")

# Clusters (comunidades de fornecedores)
node_cluster = {}
if F.number_of_edges() > 10:
    try:
        clusters = louvain_communities(F, weight="weight", seed=42)
        for cid, nodes in enumerate(clusters):
            for n in nodes:
                node_cluster[n] = cid
        print(f"Clusters: {len(clusters)}")
    except Exception as e:
        print(f"Clustering erro: {e}")
        # Fallback: componentes conectados
        for cid, comp in enumerate(nx.connected_components(F)):
            for n in comp:
                node_cluster[n] = cid
        print(f"Componentes: {len(set(node_cluster.values()))}")
else:
    print("Rede muito esparsa, sem clusters")

# 5. SCORING COM VARIABILIDADE
print("\n[5/5] Calculando scores...")

casos = []

for f in forn_cat:
    total = sum(forn_cat[f].values())
    if total < 5000:  # filtro minimo
        continue
    
    cats = forn_cat[f]
    num_cats = len(cats)
    max_val = max(cats.values())
    max_cat = max(cats, key=cats.get)
    
    # Concentracao (0 a 1)
    concentracao = max_val / total
    
    # Diversidade (inverso da concentracao)
    diversidade = num_cats / (num_cats + 3)  # suavizado
    
    # Multi-orgaos (escala logaritmica)
    num_orgs = len(forn_org_val[f])
    multi_org = math.log(1 + num_orgs) / math.log(50)  # normalizado
    
    # Centralidade na rede
    if f in F:
        deg = F.degree(f, weight="weight")
        max_deg = max(dict(F.degree(weight="weight")).values()) if F.number_of_nodes() > 0 else 1
        centralidade = min(1.0, deg / (max_deg * 0.5 + 1))
    else:
        centralidade = 0
    
    # Bonus de cluster
    cluster_bonus = 1.0
    if f in node_cluster:
        # Verificar se tem outros do mesmo cluster
        cid = node_cluster[f]
        cluster_size = sum(1 for n in node_cluster if node_cluster[n] == cid)
        if cluster_size > 5:
            cluster_bonus = 1.1 + (0.01 * min(10, cluster_size - 5))
    
    # Score estrutural (variavel)
    score = (
        0.35 * concentracao +
        0.20 * diversidade +
        0.25 * multi_org +
        0.20 * centralidade
    ) * cluster_bonus
    
    if score > 0.3:
        casos.append({
            "forn": f,
            "score": score,
            "cat": max_cat,
            "conc": concentracao,
            "div": diversidade,
            "orgs": num_orgs,
            "cent": centralidade,
            "total": total
        })

print(f"Casos detectados: {len(casos)}")

# 6. RESULTADOS
print("\n" + "=" * 100)
print("RANKING v4.1 - CORRECAO ESTRUTURAL")
print("=" * 100)
print(f"{'#':<4} {'Fornecedor':<38} {'Cat':<12} {'Score':<7} {'Conc':<5} {'Div':<5} {'Orgs':<5}")
print("-" * 100)

casos.sort(key=lambda x: x["score"], reverse=True)

for i, c in enumerate(casos[:25], 1):
    nivel = "🔴" if c["score"] > 0.75 else "🟡" if c["score"] > 0.6 else "⚡"
    print(f"{i:<4} {c['forn'][:36]:<38} {c['cat']:<12} {c['score']:<7.3f} {c['conc']:<5.2f} {c['div']:<5.2f} {c['orgs']:<5} {nivel}")

print("\n" + "=" * 100)
altos = len([c for c in casos if c["score"] > 0.75])
medios = len([c for c in casos if 0.6 < c["score"] <= 0.75])
baixos = len([c for c in casos if 0.45 < c["score"] <= 0.6])

print(f"🔴 ALTO (>0.75):     {altos:4d}")
print(f"🟡 MEDIO (0.60-0.75): {medios:4d}")
print(f"⚡ ATENCAO (0.45-0.60): {baixos:4d}")
print(f"Total: {len(casos)}")

# Distribuicao por categoria
print("\nPor categoria (top 10):")
cat_dist = defaultdict(int)
for c in casos:
    cat_dist[c["cat"]] += 1
for cat, cnt in sorted(cat_dist.items(), key=lambda x: -x[1])[:10]:
    pct = 100 * cnt / len(casos)
    print(f"  {cat:<15}: {cnt:4d} ({pct:5.1f}%)")

conn.close()
print("=" * 100)
print("✓ v4.1 Correcao Estrutural concluida!")
ENDOFFILE

python v41_corrigido.py
