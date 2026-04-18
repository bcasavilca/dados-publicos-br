#!/usr/bin/env python3
"""
Versao simplificada - apenas portais locais (sem dados.gov.br)
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import csv
import os

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
        print(f"Erro ao carregar CSV: {e}")
        return []

data = load_data()

@app.route('/')
def home():
    return jsonify({
        'nome': 'Dados Publicos BR',
        'versao': '2.7-simple',
        'portais': len(data)
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'portais': len(data)})

@app.route('/catalogo')
def catalogo():
    # Adicionar tipo e score
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

@app.route('/buscar')
def buscar():
    q = request.args.get('q', '').lower()
    
    if not q or len(q) < 2:
        return jsonify({'erro': 'Termo muito curto', 'busca': q}), 400
    
    results = []
    for row in data:
        # Buscar em todas as colunas
        match = any(q in str(val).lower() for val in row.values())
        if match:
            row_copy = row.copy()
            row_copy['tipo'] = 'portal'
            row_copy['score'] = 50 if row.get('Qualidade') == 'Alta' else 30
            results.append(row_copy)
    
    return jsonify({
        'busca': q,
        'total_resultados': len(results),
        'total_portais': len(results),
        'total_datasets': 0,
        'resultados': results
    })

@app.route('/estatisticas')
def estatisticas():
    return jsonify({
        'total_portais': len(data),
        'ufs': len(set(row.get('UF', '') for row in data)),
        'qualidade_alta': len([r for r in data if r.get('Qualidade') == 'Alta']),
        'qualidade_media': len([r for r in data if r.get('Qualidade') == 'Media']),
        'qualidade_baixa': len([r for r in data if r.get('Qualidade') == 'Baixa'])
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[OK] Servidor iniciando na porta {port}")
    print(f"[OK] Carregados {len(data)} portais")
    app.run(host='0.0.0.0', port=port)
