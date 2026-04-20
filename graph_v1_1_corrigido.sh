#!/bin/bash
# Graph Engine v1.1 - Contexto Temporal Corrigido

cat > graph_v1_1.py << 'PYEND'
import os
import psycopg2
from itertools import combinations

print("=" * 80)
print("GRAPH ENGINE v1.1 - CONTEXTO TEMPORAL CORRIGIDO")
print("Conectando apenas fornecedores do mesmo orgao + mes")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 1. Limpar edges antigos (com contexto errado)
print("\n[1/4] Limpando edges com contexto amplo...")
cur.execute("DELETE FROM graph_edges WHERE relation_type = 'co_occurrence'")
cur.execute("DELETE FROM graph_edges WHERE relation_type = 'co_occurrence_temporal'")
conn.commit()
print("✓ Limpo")

# 2. Criar edges com contexto temporal (ORGAO + MES)
print("\n[2/4] Criando edges com contexto temporal (orgao + mes)...")

cur.execute("""
    SELECT 
        orgao,
        SUBSTRING(data_assinatura FROM 4 FOR 2) as mes,
        fornecedor,
        COUNT(*) as qtd
    FROM sp_contratos
    WHERE data_assinatura IS NOT NULL 
      AND data_assinatura != ''
      AND SUBSTRING(data_assinatura FROM 4 FOR 2) ~ '^[0-9]{2}$'
    GROUP BY orgao, mes, fornecedor
    ORDER BY orgao, mes
""")

# Agrupar por (orgao, mes)
contextos = {}
for orgao, mes, fornecedor, qtd in cur.fetchall():
    chave = f"{orgao}__{mes}"
    if chave not in contextos:
        contextos[chave] = []
    contextos[chave].append((fornecedor, qtd))

print(f"Contextos (orgao + mes) encontrados: {len(contextos)}")

# Gerar edges apenas dentro do mesmo contexto temporal
edges = 0
for contexto, fornecedores in contextos.items():
    # Pegar fornecedores com significancia (>= 3 contratos nesse mes)
    significativos = [(f, q) for f, q in fornecedores if q >= 3]
    
    if len(significativos) >= 2:
        for (a, qa), (b, qb) in combinations(significativos, 2):
            peso = min(qa, qb)
            
            # CORRECAO: Inserir com tipo novo
            cur.execute("""
                INSERT INTO graph_edges (node_a, node_b, relation_type, weight)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (node_a, node_b, relation_type)
                DO UPDATE SET weight = graph_edges.weight + EXCLUDED.weight
            """, (a, b, 'co_occurrence_temporal', peso))
            edges += 1

conn.commit()
print(f"✓ Edges criados: {edges:,}")

# 3. Analisar resultado
print("\n[3/4] Analisando grafo corrigido...")

cur.execute("""
    SELECT node_a, node_b, weight 
    FROM graph_edges 
    WHERE relation_type = 'co_occurrence_temporal'
    ORDER BY weight DESC
    LIMIT 20
""")

top_edges = cur.fetchall()
print(f"\nTop 20 conexoes mais fortes (temporal):")
print(f"{'Fornecedor A':<35} {'Fornecedor B':<35} {'Peso':>6}")
print("-" * 80)

for a, b, w in top_edges:
    print(f"{a[:33]:<35} {b[:33]:<35} {w:>6}")

# 4. Detectar clusters (fornecedores que aparecem em multiplos contextos)
print("\n[4/4] Detectando fornecedores em multiplos contextos...")

cur.execute("""
    SELECT node_a, COUNT(DISTINCT node_b) as conexoes, SUM(weight) as total
    FROM graph_edges
    WHERE relation_type = 'co_occurrence_temporal'
    GROUP BY node_a
    ORDER BY conexoes DESC, total DESC
    LIMIT 10
""")

print(f"\nFornecedores mais conectados (aparecem em varios contextos):")
print(f"{'Fornecedor':<40} {'Conexoes':>10} {'Peso Total':>12}")
print("-" * 65)

for node, conexoes, total in cur.fetchall():
    print(f"{node[:38]:<40} {conexoes:>10} {total:>12}")

# Comparacao
print("\n" + "=" * 80)
print("COMPARACAO: Antes vs Depois")
print("=" * 80)

cur.execute("SELECT COUNT(*) FROM graph_edges WHERE relation_type = 'co_occurrence'")
antigo = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM graph_edges WHERE relation_type = 'co_occurrence_temporal'")
novo = cur.fetchone()[0]

print(f"\nEdges antigos (contexto amplo): {antigo:,}")
print(f"Edges novos (contexto temporal): {novo:,}")
print(f"Reducao: {(1 - novo/antigo)*100:.1f}%" if antigo > 0 else "N/A")

if novo < antigo * 0.5:
    print("\n✅ GRAFO REFINADO: Menos ruido, mais sinal real")
else:
    print("\n⚠️  Ainda denso - considerar threshold mais alto")

conn.close()

print("\n" + "=" * 80)
print("✓ Graph Engine v1.1 concluido!")
print("=" * 80)
print("\nProximo: Implementar Louvain clustering nos edges corrigidos")
PYEND

python graph_v1_1.py
