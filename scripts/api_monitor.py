#!/usr/bin/env python3
"""
API com monitoramento de portais
Versao 2.7 - Passo 1 da evolucao
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import csv
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app, origins=['*'])

# Carregar CSV
def load_data():
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"[Erro] Carregar CSV: {e}")
        return []

# Carregar relatório de monitoramento
def load_monitor_report():
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'monitor_report.json')
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

data = load_data()

@app.route('/')
def home():
    return jsonify({
        'nome': 'Dados Publicos BR',
        'versao': '2.7-monitor',
        'portais': len(data),
        'monitoramento': 'ativo'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'portais': len(data)})

@app.route('/status')
def status():
    """Retorna status de monitoramento dos portais"""
    report = load_monitor_report()
    if report:
        return jsonify({
            'ultima_verificacao': report.get('generated_at'),
            'total': report.get('total_portais'),
            'online': report.get('online'),
            'offline': report.get('offline'),
            'online_percentual': report.get('online_percentage'),
            'latencia_media_ms': report.get('avg_latency_ms')
        })
    return jsonify({'erro': 'Relatorio de monitoramento nao disponivel. Execute scripts/monitor.py'}), 503

@app.route('/status/detalhado')
def status_detalhado():
    """Retorna status detalhado de cada portal"""
    report = load_monitor_report()
    if report:
        return jsonify(report)
    return jsonify({'erro': 'Relatorio de monitoramento nao disponivel'}), 503

@app.route('/buscar')
def buscar():
    q = request.args.get('q', '').lower().strip()
    
    if not q or len(q) < 2:
        return jsonify({'erro': 'Termo muito curto', 'busca': q}), 400
    
    resultados = []
    
    # Buscar em portais locais
    for row in data:
        match = any(q in str(val).lower() for val in row.values())
        if match:
            row_copy = row.copy()
            row_copy['tipo'] = 'portal'
            row_copy['score'] = 50 if row.get('Qualidade') == 'Alta' else 30
            resultados.append(row_copy)
    
    # Ordenar por score
    resultados.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return jsonify({
        'busca': q,
        'total_resultados': len(resultados),
        'resultados': resultados
    })

@app.route('/catalogo')
def catalogo():
    """Lista todos os portais locais"""
    results = []
    for row in data:
        row_copy = row.copy()
        row_copy['tipo'] = 'portal'
        row_copy['score'] = 50 if row.get('Qualidade') == 'Alta' else 30
        results.append(row_copy)
    
    return jsonify({
        'total': len(results),
        'resultados': results
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[OK] API com monitoramento iniciando na porta {port}")
    print(f"[OK] Portais carregados: {len(data)}")
    print(f"[OK] Endpoints: /status, /status/detalhado, /buscar, /catalogo")
    app.run(host='0.0.0.0', port=port)
