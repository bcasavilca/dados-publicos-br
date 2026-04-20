#!/bin/bash
# Baseline Temporal - Evolução mensal

cat > temporal.py << 'EOF'
import os
import psycopg2
from datetime import datetime

print("=" * 70)
print("BASELINE TEMPORAL - Análise de Evolução Mensal")
print("=" * 70)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# ============================================================
# 1. Criar tabela temporal
# ============================================================
cur.execute("""
    CREATE TABLE IF NOT EXISTS baseline_temporal (
        id SERIAL PRIMARY KEY,
        mes TEXT,
        total_contratos INT,
        total_valor NUMERIC,
        fornecedores_unicos INT,
        concentracao_top1 NUMERIC,
        media_valor NUMERIC,
        max_valor NUMERIC,
        alertas INT DEFAULT 0,
        criado_em TIMESTAMP DEFAULT NOW()
    )
""")

# Limpar dados antigos de teste
cur.execute("DELETE FROM baseline_temporal WHERE criado_em < NOW() - INTERVAL '1 hour'")

print("\n[1/3] Criando baseline temporal...")

# Agrupar SP por mês (simulado - usando dados existentes)
# Em dados reais: SELECT DATE_TRUNC('month', data) as mes, ...
cur.execute("""
    SELECT 
        SUBSTRING(data FROM 4 FOR 2) as mes_num,
        COUNT(*) as contratos,
        SUM(valor) as total,
        COUNT(DISTINCT fornecedor) as forn_unicos
    FROM sp_contratos
    WHERE data IS NOT NULL AND data != ''
    GROUP BY SUBSTRING(data FROM 4 FOR 2)
    ORDER BY mes_num
""")

meses = cur.fetchall()
print(f"Meses encontrados: {len(meses)}")

# Calcular concentração por mês
for mes_num, contratos, total, forn_unicos in meses:
    mes_nome = f"2024-{mes_num}"
    
    # Top 1 do mês
    cur.execute("""
        SELECT fornecedor, COUNT(*) 
        FROM sp_contratos 
        WHERE SUBSTRING(data FROM 4 FOR 2) = %s
        GROUP BY fornecedor 
        ORDER BY COUNT(*) DESC 
        LIMIT 1
    """, (mes_num,))
    
    top1 = cur.fetchone()
    conc_top1 = (top1[1] / contratos) if top1 else 0
    
    # Média e máximo
    cur.execute("""
        SELECT AVG(valor), MAX(valor)
        FROM sp_contratos
        WHERE SUBSTRING(data FROM 4 FOR 2) = %s
    """, (mes_num,))
    
    media, maximo = cur.fetchone()
    
    # Inserir baseline
    cur.execute("""
        INSERT INTO baseline_temporal 
        (mes, total_contratos, total_valor, fornecedores_unicos, 
         concentracao_top1, media_valor, max_valor)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (mes_nome, contratos, total, forn_unicos, conc_top1, media, maximo))

conn.commit()

# ============================================================
# 2. Análise de variação temporal
# ============================================================
print("\n[2/3] Analisando variações temporais...")

cur.execute("""
    SELECT * FROM baseline_temporal 
    ORDER BY mes
""")

baselines = cur.fetchall()

print(f"\n{'Mês':<10} {'Contratos':>10} {'Valor Total':>15} {'Top1%':>8} {'Alerta':<20}")
print("-" * 70)

alertas_gerados = 0

for i, row in enumerate(baselines):
    mes = row[1]
    contratos = row[2]
    valor = row[3]
    conc = row[5]
    
    alertas = []
    
    # Comparar com mês anterior
    if i > 0:
        prev = baselines[i-1]
        prev_contratos = prev[2]
        prev_valor = prev[3]
        prev_conc = prev[5]
        
        # Spike de contratos (+50%)
        if contratos > prev_contratos * 1.5:
            alertas.append(f" Spike contratos (+{(contratos/prev_contratos-1)*100:.0f}%)")
        
        # Spike de valor (+100%)
        if valor > prev_valor * 2:
            alertas.append(f" Spike valor (+{(valor/prev_valor-1)*100:.0f}%)")
        
        # Aumento de concentração (+30% relativo)
        if conc > prev_conc * 1.3:
            alertas.append(f" Concentração subiu")
    
    # Threshold absolutos
    if conc > 0.40:  # Mais de 40% em um fornecedor
        alertas.append(" Concentração crítica")
    
    alerta_str = "; ".join(alertas) if alertas else "-"
    if alertas:
        alertas_gerados += 1
    
    print(f"{mes:<10} {contratos:>10,} R$ {valor/1e6:>12.1f}M {conc*100:>7.1f}% {alerta_str:<30}")

# ============================================================
# 3. Estatísticas gerais
# ============================================================
print("\n[3/3] Resumo temporal:")

cur.execute("SELECT AVG(total_contratos), STDDEV(total_contratos) FROM baseline_temporal")
avg_c, std_c = cur.fetchone()

cur.execute("SELECT AVG(total_valor), STDDEV(total_valor) FROM baseline_temporal")
avg_v, std_v = cur.fetchone()

print(f"\nMédia mensal: {avg_c:.0f} contratos, R$ {avg_v/1e6:.1f}M")
print(f"Desvio padrão: {std_c:.0f} contratos, R$ {std_v/1e6:.1f}M")
print(f"Alertas gerados: {alertas_gerados}")

# Calcular score temporal médio
print("\n" + "=" * 70)
print("SCORE TEMPORAL para integração no motor:")
print("=" * 70)

# Fórmula: quanto mais estável, menor o score
# Alto desvio = alto risco temporal
if avg_c > 0:
    cv_contratos = std_c / avg_c  # Coeficiente de variação
    cv_valor = std_v / avg_v
    
    score_temporal = min(1.0, (cv_contratos + cv_valor) / 2)
    
    print(f"CV Contratos: {cv_contratos:.2f}")
    print(f"CV Valor: {cv_valor:.2f}")
    print(f"Score Temporal: {score_temporal:.3f}")
    
    if score_temporal > 0.5:
        print("⚠️  ALTA VARIABILIDADE - Instabilidade detectada")
    else:
        print("✅ Estabilidade temporal")

conn.close()

print("\n" + "=" * 70)
print("✓ Baseline temporal concluído!")
print("=" * 70)
EOF

python temporal.py
