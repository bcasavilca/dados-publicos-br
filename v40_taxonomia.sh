#!/bin/bash
# v4.0 - Taxonomia de Gastos (Base Semantica)

cat > v40_taxonomia.py << 'ENDOFFILE'
import os
import psycopg2
import math
from collections import defaultdict

print("=" * 90)
print("v4.0 - TAXONOMIA DE GASTOS (BASE SEMANTICA)")
print("Anomalia INTRA-CATEGORIA")
print("=" * 90)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# 1. MAPA SIMPLES DE CATEGORIA (ajustavel depois)
def categorizar(texto):
    t = (texto or "").lower()
    
    if any(x in t for x in ["obra", "engenharia", "constru", "paviment", "predial", "reforma"]):
        return "OBRAS"
    
    if any(x in t for x in ["software", "ti", "tecnologia", "sistema", "informatica", "licenca", "computador"]):
        return "TI"
    
    if any(x in t for x in ["hospital", "medic", "saude", "clinica", "farmacia", "vacina", "equipamento medico"]):
        return "SAUDE"
    
    if any(x in t for x in ["evento", "show", "cultura", "festival", "artistico", "musica", "teatro"]):
        return "EVENTOS"
    
    if any(x in t for x in ["limpeza", "servico", "manutencao", "conservacao", "vigilancia"]):
        return "SERVICOS"
    
    if any(x in t for x in ["alimento", "merenda", "restaurante", "refeicao", "nutricao"]):
        return "ALIMENTACAO"
    
    if any(x in t for x in ["veiculo", "carro", "onibus", "transporte", "combustivel", "locacao"]):
        return "TRANSPORTE"
    
    return "OUTROS"

# 2. CARREGAR DADOS
print("\n[1/3] Carregando contratos...")

cur.execute("""
    SELECT fornecedor,
           descricao_item,
           COUNT(*) as qtd
    FROM sp_contratos
    WHERE data_assinatura IS NOT NULL
    GROUP BY fornecedor, descricao_item
""")

data = cur.fetchall()

# 3. AGRUPAR POR CATEGORIA
print("\n[2/3] Construindo baselines por categoria...")

cat_fornecedor = defaultdict(lambda: defaultdict(int))

for forn, desc, qtd in data:
    cat = categorizar(desc)
    cat_fornecedor[cat][forn] += qtd

print(f"Categorias detectadas: {len(cat_fornecedor)}")
for cat in cat_fornecedor:
    print(f"  {cat}: {len(cat_fornecedor[cat])} fornecedores")

# 4. CALCULAR ANOMALIA INTRA-CATEGORIA
print("\n[3/3] Detectando anomalias...")

casos = []

for cat, fornecedores in cat_fornecedor.items():
    valores = list(fornecedores.values())
    if len(valores) < 5:
        continue
    
    media = sum(valores) / len(valores)
    var = sum((x - media) ** 2 for x in valores) / len(valores)
    std = math.sqrt(var + 1e-9)
    
    for forn, qtd in fornecedores.items():
        z = (qtd - media) / (std + 1e-6)
        
        if z > 1.5:
            score = math.log(1 + z)
            casos.append({
                "forn": forn,
                "cat": cat,
                "qtd": qtd,
                "media_cat": media,
                "z": z,
                "score": score
            })

print(f"Casos detectados: {len(casos)}")

# 5. RANKING
print("\n" + "=" * 90)
print("RANKING v4.0 - INTRA CATEGORIA")
print("=" * 90)
print(f"{'#':<4} {'Fornecedor':<35} {'Categoria':<12} {'Qtd':<6} {'Media':<8} {'Z':<6} {'Score':<6}")
print("-" * 90)

casos.sort(key=lambda x: x["score"], reverse=True)

for i, c in enumerate(casos[:25], 1):
    nivel = "🔴" if c["score"] > 2 else "🟡" if c["score"] > 1 else "⚡"
    print(f"{i:<4} {c['forn'][:33]:<35} {c['cat']:<12} {c['qtd']:<6} {c['media_cat']:<8.1f} {c['z']:<6.2f} {c['score']:<6.2f} {nivel}")

print("\n" + "=" * 90)

# Estatisticas por categoria
print("\nPor categoria:")
for cat in ["OBRAS", "TI", "SAUDE", "EVENTOS", "SERVICOS", "ALIMENTACAO", "TRANSPORTE", "OUTROS"]:
    count = len([c for c in casos if c["cat"] == cat])
    if count > 0:
        print(f"  {cat:<12}: {count} casos")

print(f"\nTotal casos: {len(casos)}")

conn.close()
print("=" * 90)
print("✓ v4.0 Taxonomia de Gastos concluido!")
print("=" * 90)
ENDOFFILE

python v40_taxonomia.py
