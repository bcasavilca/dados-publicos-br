import os
import psycopg2
import math
from collections import defaultdict, deque

print("=" * 90)
print("v3.6 - DUAL-SCORE SYSTEM (AUDITORIA SERIE)")
print("Risk Score + Confidence Score")
print("=" * 90)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("\n[1/3] Carregando contratos...")
cur.execute("""
    SELECT fornecedor, SUBSTRING(data_assinatura FROM 4 FOR 2), COUNT(*)
    FROM sp_contratos WHERE data_assinatura IS NOT NULL
    GROUP BY fornecedor, SUBSTRING(data_assinatura FROM 4 FOR 2)
    ORDER BY fornecedor, SUBSTRING(data_assinatura FROM 4 FOR 2)
""")

data = cur.fetchall()

print("\n[2/3] Calculando baseline individual...")
window_size = 6
forn_series = defaultdict(lambda: deque(maxlen=window_size))

for forn, mes, qtd in data:
    forn_series[forn].append(qtd)

stats = {}
for forn, series in forn_series.items():
    if len(series) >= 3:
        mean = sum(series) / len(series)
        var = sum((x - mean) ** 2 for x in series) / len(series)
        std = math.sqrt(var) if var > 0 else 1e-6
        stats[forn] = {"mean": mean, "std": std, "series": list(series)}

print("\n[3/3] Calculando Dual-Score...")
casos = []

for forn in stats:
    s = stats[forn]
    series = s.get("series", [])
    if not series:
        continue
    
    x_t = series[-1]
    mu = s.get("mean", 0)
    sigma = s.get("std", 1e-6)
    
    # Z-score (anomalia bruta)
    z = (x_t - mu) / sigma if x_t > mu else 0
    
    # Estabilidade (E)
    E = 1.0 / (1.0 + sigma)
    
    # Regime shift detection
    first = series[:len(series)//2]
    second = series[len(series)//2:]
    
    if len(first) >= 2 and len(second) >= 2:
        mu1 = sum(first) / len(first)
        mu2 = sum(second) / len(second)
        regime_shift = abs(mu2 - mu1) / (mu1 + 1e-6)
    else:
        regime_shift = 0.0
    
    R = 1.0 / (1.0 + regime_shift)
    
    # DUAL-SCORE SYSTEM
    # Risk Score: anomalia bruta (range reaberto)
    risk_score = z * (0.7 + 0.3 * E) * (0.7 + 0.3 * R)
    
    # Confidence Score: qualidade do sinal
    confidence_score = E * R
    
    # Classificacao Dual
    if risk_score >= 1.2 and confidence_score >= 0.5:
        nivel = "🔴 ALTO"
    elif risk_score >= 0.8 and confidence_score >= 0.4:
        nivel = "🟡 MEDIO"
    elif risk_score >= 0.5:
        nivel = "⚡ ATENCAO"
    else:
        nivel = None
    
    if nivel:
        casos.append({
            "forn": str(forn),
            "z": z,
            "risk": risk_score,
            "confidence": confidence_score,
            "regime": regime_shift,
            "nivel": nivel
        })

casos.sort(key=lambda x: x["risk"], reverse=True)

print("\n" + "=" * 90)
print("RANKING INVESTIGATIVO v3.6 - DUAL-SCORE")
print("=" * 90)
print(f"{'#':<4} {'Fornecedor':<38} {'Z':<6} {'Risk':<8} {'Conf':<8} {'Nivel':<10}")
print("-" * 90)

for i, c in enumerate(casos[:20], 1):
    print(f"{i:<4} {c['forn'][:36]:<38} {c['z']:<6.2f} {c['risk']:<8.3f} {c['confidence']:<8.3f} {c['nivel']:<10}")

print("\n" + "=" * 90)
altos = len([c for c in casos if "ALTO" in c["nivel"]])
medios = len([c for c in casos if "MEDIO" in c["nivel"]])
atencao = len([c for c in casos if "ATENCAO" in c["nivel"]])

print(f"🔴 ALTO: {altos} | 🟡 MEDIO: {medios} | ⚡ ATENCAO: {atencao} | Total: {len(casos)}")

conn.close()
print("=" * 90)
print("✓ v3.6 Dual-Score System concluido!")
print("=" * 90)
