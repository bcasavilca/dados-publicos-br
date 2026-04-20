#!/bin/bash
# Nivel 2 Hibrido - Baseline Temporal Robusto

cat > nivel2_hibrido.py << 'PYEND'
import os
import psycopg2
import math

print("=" * 80)
print("NIVEL 2 - BASELINE TEMPORAL HIBRIDO")
print("Real (2%) + Proxy (98%) + Blocos Estruturais")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# ============================================================
# 1. Criar tabela temporal robusta
# ============================================================
print("\n[1/4] Criando tabela temporal_hibrido...")

cur.execute("""
    DROP TABLE IF EXISTS baseline_temporal_hibrido
""")

cur.execute("""
    CREATE TABLE baseline_temporal_hibrido (
        id SERIAL PRIMARY KEY,
        tipo_periodo TEXT,        -- 'real', 'proxy', 'bloco'
        periodo_id TEXT,          -- mes-ano, bloco-id, etc
        total_contratos INT,
        total_valor NUMERIC,
        fornecedores_unicos INT,
        concentracao_top1 NUMERIC,
        media_valor NUMERIC,
        max_valor NUMERIC,
        criado_em TIMESTAMP DEFAULT NOW()
    )
""")

# ============================================================
# 2. Extrair tempo REAL (com data_assinatura)
# ============================================================
print("\n[2/4] Extraindo tempo REAL (com data)...")

cur.execute("""
    SELECT 
        SUBSTRING(data_assinatura FROM 4 FOR 2) as mes,
        COUNT(*) as contratos,
        SUM(valor) as total,
        COUNT(DISTINCT fornecedor) as forn_unicos
    FROM sp_contratos
    WHERE data_assinatura IS NOT NULL 
      AND data_assinatura != ''
      AND data_assinatura LIKE '__/____'
    GROUP BY SUBSTRING(data_assinatura FROM 4 FOR 2)
    ORDER BY mes
""")

meses_reais = cur.fetchall()
print(f"Meses com data real: {len(meses_reais)}")

for mes, contratos, total, forn_unicos in meses_reais:
    # Calcular concentracao top1
    cur.execute("""
        SELECT COUNT(*) 
        FROM sp_contratos
        WHERE data_assinatura LIKE %s
        GROUP BY fornecedor
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """, (f'%/{mes}/%',))
    
    top1 = cur.fetchone()
    conc_top1 = (top1[0] / contratos) if top1 else 0
    
    # Media e max
    cur.execute("""
        SELECT AVG(valor), MAX(valor)
        FROM sp_contratos
        WHERE data_assinatura LIKE %s
    """, (f'%/{mes}/%',))
    
    media, maximo = cur.fetchone()
    
    cur.execute("""
        INSERT INTO baseline_temporal_hibrido 
        (tipo_periodo, periodo_id, total_contratos, total_valor, 
         fornecedores_unicos, concentracao_top1, media_valor, max_valor)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, ('real', f'2024-{mes}', contratos, total, forn_unicos, conc_top1, media, maximo))

print(f"✓ Inseridos {len(meses_reais)} periodos reais")

# ============================================================
# 3. Criar BLOCOS temporais (para dados sem data)
# ============================================================
print("\n[3/4] Criando BLOCOS temporais (proxy)...")

cur.execute("SELECT COUNT(*) FROM sp_contratos")
total = cur.fetchone()[0]

# Dividir em 4 blocos por ordem de ID
blocos = [
    (1, int(total * 0.25), 'bloco_1'),
    (int(total * 0.25) + 1, int(total * 0.50), 'bloco_2'),
    (int(total * 0.50) + 1, int(total * 0.75), 'bloco_3'),
    (int(total * 0.75) + 1, total, 'bloco_4')
]

for inicio, fim, nome in blocos:
    cur.execute("""
        SELECT COUNT(*), SUM(valor), COUNT(DISTINCT fornecedor)
        FROM sp_contratos
        WHERE id BETWEEN %s AND %s
    """, (inicio, fim))
    
    contratos, total_valor, forn_unicos = cur.fetchone()
    
    # Top 1 concentracao
    cur.execute("""
        SELECT COUNT(*) 
        FROM sp_contratos
        WHERE id BETWEEN %s AND %s
        GROUP BY fornecedor
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """, (inicio, fim))
    
    top1 = cur.fetchone()
    conc_top1 = (top1[0] / contratos) if top1 else 0
    
    # Media e max
    cur.execute("""
        SELECT AVG(valor), MAX(valor)
        FROM sp_contratos
        WHERE id BETWEEN %s AND %s
    """, (inicio, fim))
    
    media, maximo = cur.fetchone()
    
    cur.execute("""
        INSERT INTO baseline_temporal_hibrido 
        (tipo_periodo, periodo_id, total_contratos, total_valor,
         fornecedores_unicos, concentracao_top1, media_valor, max_valor)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, ('bloco', nome, contratos, total_valor, forn_unicos, conc_top1, media, maximo))

print(f"✓ Inseridos {len(blocos)} blocos temporais")

conn.commit()

# ============================================================
# 4. Analisar tendencias e metricas
# ============================================================
print("\n[4/4] Analisando tendencias...")

print("\n" + "=" * 80)
print("BASELINE TEMPORAL HIBRIDO - RESULTADOS")
print("=" * 80)

# Periodos reais
print("\n📅 PERIODOS REAIS (com data):")
print(f"{'Periodo':<12} {'Contratos':>10} {'Valor (M)':>12} {'Conc%':>8} {'Status':<15}")
print("-" * 70)

cur.execute("""
    SELECT * FROM baseline_temporal_hibrido 
    WHERE tipo_periodo = 'real'
    ORDER BY periodo_id
""")

anterior = None
alertas_reais = []
for row in cur.fetchall():
    periodo = row[3]
    contratos = row[4]
    valor = row[5]
    conc = row[7]
    
    status = "-"
    if anterior:
        if contratos > anterior[4] * 1.3:
            status = "📈 ALTA"
            alertas_reais.append((periodo, 'spike', contratos/anterior[4]))
        elif contratos < anterior[4] * 0.7:
            status = "📉 BAIXA"
    
    print(f"{periodo:<12} {contratos:>10,} R${valor/1e6:>10.1f}M {conc*100:>7.1f}% {status:<15}")
    anterior = row

# Blocos
print("\n📦 BLOCOS TEMPORAIS (proxy por ordem):")
print(f"{'Bloco':<12} {'Contratos':>10} {'Valor (M)':>12} {'Conc%':>8} {'Status':<15}")
print("-" * 70)

cur.execute("""
    SELECT * FROM baseline_temporal_hibrido 
    WHERE tipo_periodo = 'bloco'
    ORDER BY periodo_id
""")

anterior = None
for row in cur.fetchall():
    bloco = row[3]
    contratos = row[4]
    valor = row[5]
    conc = row[7]
    
    status = "-"
    if anterior:
        diff = (contratos - anterior[4]) / anterior[4]
        if diff > 0.2:
            status = "📈 CRESC"
        elif diff < -0.2:
            status = "📉 QUEDA"
    
    print(f"{bloco:<12} {contratos:>10,} R${valor/1e6:>10.1f}M {conc*100:>7.1f}% {status:<15}")
    anterior = row

# Resumo
print("\n" + "=" * 80)
print("METRICAS DE ESTABILIDADE")
print("=" * 80)

cur.execute("""
    SELECT 
        AVG(total_contratos), STDDEV(total_contratos),
        AVG(concentracao_top1), STDDEV(concentracao_top1)
    FROM baseline_temporal_hibrido
""")

avg_c, std_c, avg_conc, std_conc = cur.fetchone()

cv_contratos = std_c / avg_c if avg_c > 0 else 0
cv_conc = std_conc / avg_conc if avg_conc > 0 else 0

print(f"\nContratos:")
print(f"  Media: {avg_c:.0f}")
print(f"  Desvio: {std_c:.0f}")
print(f"  CV (volatilidade): {cv_contratos:.2f}")

print(f"\nConcentracao:")
print(f"  Media: {avg_conc*100:.1f}%")
print(f"  Desvio: {std_conc*100:.1f}%")
print(f"  CV: {cv_conc:.2f}")

print(f"\n{'='*80}")
if cv_contratos > 0.3:
    print("⚠️  SISTEMA VOLATIL: Alta variacao temporal")
elif cv_contratos > 0.15:
    print("⚡ SISTEMA MODERADO: Variacao controlada")
else:
    print("✅ SISTEMA ESTAVEL: Comportamento previsivel")

print(f"{'='*80}")

conn.close()

print("\n✓ Nivel 2 Hibrido implementado!")
print("\nProximo: Integrar no Motor v3.0")
PYEND

python nivel2_hibrido.py
