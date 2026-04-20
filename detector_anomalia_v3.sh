#!/bin/bash
# Detector de Anomalia v3.0 - Max + Boost + Casos Investigaveis

cat > detector_v3.py << 'PYEND'
import os
import psycopg2
import math
from collections import defaultdict

print("=" * 80)
print("DETECTOR DE ANOMALIA v3.0")
print("Max + Boost | Casos Investigaveis | Explicabilidade")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 1. Coletar dados brutos
print("\n[1/4] Coletando dados...")

cur.execute("""
    SELECT 
        fornecedor,
        orgao,
        SUBSTRING(data_assinatura FROM 4 FOR 2) as mes,
        COUNT(*) as contratos,
        SUM(valor) as total_valor
    FROM sp_contratos
    WHERE data_assinatura IS NOT NULL
    GROUP BY fornecedor, orgao, mes
    ORDER BY fornecedor, orgao, mes
""")

dados = cur.fetchall()
print(f"Registros coletados: {len(dados)}")

# 2. Calcular metricas por fornecedor
print("\n[2/4] Calculando metricas de anomalia...")

metricas = defaultdict(lambda: {
    'orgaos': set(),
    'meses': set(),
    'total_contratos': 0,
    'total_valor': 0,
    'por_orgao': defaultdict(int),
    'sequencia': []
})

for forn, org, mes, qtd, valor in dados:
    metricas[forn]['orgaos'].add(org)
    metricas[forn]['meses'].add(mes)
    metricas[forn]['total_contratos'] += qtd
    metricas[forn]['total_valor'] += valor
    metricas[forn]['por_orgao'][org] += qtd
    metricas[forn]['sequencia'].append((org, mes, qtd))

# 3. Detectores de anomalia
print("\n[3/4] Aplicando detectores...")

casos = []

for forn, m in metricas.items():
    # Detector 1: Dominio absoluto (>70% de um orgao)
    for org, qtd_org in m['por_orgao'].items():
        if m['total_contratos'] > 0:
            dominio = qtd_org / m['total_contratos']
            if dominio > 0.70:
                casos.append({
                    'forn': forn,
                    'tipo': 'DOMINIO_ABSOLUTO',
                    'score': 0.75 + (dominio - 0.70) * 0.5,
                    'detalhe': f'Domina {dominio*100:.1f}% do orgao {org[:30]}',
                    'evidencia': f'{qtd_org} de {m["total_contratos"]} contratos'
                })
    
    # Detector 2: Exclusividade (1 orgao so)
    if len(m['orgaos']) == 1 and m['total_contratos'] >= 20:
        org_unico = list(m['orgaos'])[0]
        casos.append({
            'forn': forn,
            'tipo': 'EXCLUSIVIDADE',
            'score': 0.65,
            'detalhe': f'Exclusivo do orgao {org_unico[:30]}',
            'evidencia': f'{m["total_contratos"]} contratos em unico orgao'
        })
    
    # Detector 3: Concentracao temporal (muitos contratos em poucos meses)
    if len(m['meses']) <= 3 and m['total_contratos'] >= 30:
        casos.append({
            'forn': forn,
            'tipo': 'CONCENTRACAO_TEMPORAL',
            'score': 0.60,
            'detalhe': f'{m["total_contratos"]} contratos em apenas {len(m["meses"])} meses',
            'evidencia': f'Meses: {", ".join(sorted(m["meses"]))}'
        })

# 4. Ordenar e exibir casos
print("\n" + "=" * 80)
print("CASOS INVESTIGAVEIS")
print("=" * 80)

# Agrupar por fornecedor (um fornecedor pode ter multiplos alertas)
fornecedor_alertas = defaultdict(list)
for c in casos:
    fornecedor_alertas[c['forn']].append(c)

# Calcular score final (max + boost)
fornecedor_scores = []
for forn, alertas in fornecedor_alertas.items():
    score_base = max(a['score'] for a in alertas)
    bonus = len(alertas) * 0.05  # Boost por multiplos sinais
    score_final = min(score_base + bonus, 1.0)
    
    fornecedor_scores.append({
        'forn': forn,
        'score': score_final,
        'alertas': alertas,
        'qtd_alertas': len(alertas)
    })

# Ordenar por score
fornecedor_scores.sort(key=lambda x: x['score'], reverse=True)

# Exibir top 15
print(f"\n{'Rank':<6} {'Fornecedor':<35} {'Score':>7} {'Alertas':<40}")
print("-" * 95)

for i, fs in enumerate(fornecedor_scores[:15], 1):
    nivel = "🔴 ALTO" if fs['score'] > 0.70 else "🟡 MEDIO" if fs['score'] > 0.55 else "⚡ ATENCAO"
    tipos = ", ".join([a['tipo'][:15] for a in fs['alertas'][:2]])
    print(f"{i:<6} {fs['forn'][:33]:<35} {fs['score']:>7.3f} {tipos:<40} {nivel}")

# Detalhes dos top 5
print("\n" + "=" * 80)
print("DETALHES DOS TOP 5 CASOS")
print("=" * 80)

for i, fs in enumerate(fornecedor_scores[:5], 1):
    print(f"\n{i}. {fs['forn']}")
    print(f"   Score Final: {fs['score']:.3f} ({len(fs['alertas'])} sinais combinados)")
    print(f"   Evidencias:")
    for a in fs['alertas']:
        print(f"      • {a['tipo']}: {a['detalhe']}")
        print(f"        └─ {a['evidencia']}")

# Estatisticas
print("\n" + "=" * 80)
print("ESTATISTICAS")
print("=" * 80)

altos = len([f for f in fornecedor_scores if f['score'] > 0.70])
medios = len([f for f in fornecedor_scores if 0.55 < f['score'] <= 0.70])
atencao = len([f for f in fornecedor_scores if f['score'] <= 0.55])

print(f"\n🔴 Alto Risco (>0.70): {altos} casos")
print(f"🟡 Medio Risco (0.55-0.70): {medios} casos")
print(f"⚡ Atencao (<0.55): {atencao} casos")
print(f"\nTotal fornecedores analisados: {len(metricas)}")
print(f"Total casos gerados: {len(casos)}")

if altos == 0:
    print("\n⚠️  Nenhum caso em ALTO RISCO")
    print("    Sugestoes:")
    print("    - Ajustar thresholds de dominio (atual: 70%)")
    print("    - Adicionar detector de rodizio")
    print("    - Incluir analise de CNPJ/Grupos Economicos")

conn.close()

print("\n" + "=" * 80)
print("✓ Detector v3.0 concluido!")
print("=" * 80)
PYEND

python detector_v3.py
