#!/usr/bin/env python3
"""
API com busca HIBRIDA completa:
- Portais locais (CSV)
- Datasets do dados.gov.br (API em tempo real)
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import csv
import os
import sys

# Adicionar path para imports
sys.path.append(os.path.dirname(__file__))
from dadosgov_crawler import DadosGovCrawler

app = Flask(__name__)
CORS(app, origins=['*'])

# Carregar portais locais
def load_portais():
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"[Erro] Carregar CSV: {e}")
        return []

portais_data = load_portais()
crawler = DadosGovCrawler()

@app.route('/')
def home():
    return jsonify({
        'nome': 'Dados Publicos BR',
        'versao': '3.0-hibrida',
        'portais': len(portais_data),
        'fontes': ['portais_locais', 'dados.gov.br']
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'portais': len(portais_data)
    })

@app.route('/buscar')
def buscar():
    q = request.args.get('q', '').lower().strip()
    
    if not q or len(q) < 2:
        return jsonify({'erro': 'Termo muito curto', 'busca': q}), 400
    
    resultados = []
    
    # 1. Buscar em portais locais
    for row in portais_data:
        match = any(q in str(val).lower() for val in row.values())
        if match:
            row_copy = row.copy()
            row_copy['tipo'] = 'portal'
            row_copy['score'] = 50 if row.get('Qualidade') == 'Alta' else 30
            resultados.append(row_copy)
    
    total_portais = len(resultados)
    
    # 2. Buscar no dados.gov.br (API em tempo real)
    try:
        datasets = crawler.search_datasets(q, rows=20)
        resultados.extend(datasets)
    except Exception as e:
        print(f"[Erro] dados.gov.br: {e}")
        datasets = []
    
    total_datasets = len(datasets)
    
    # 3. Ordenar por score
    resultados.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return jsonify({
        'busca': q,
        'total_resultados': len(resultados),
        'total_portais': total_portais,
        'total_datasets': total_datasets,
        'fontes': ['portais_locais', 'dados.gov.br'],
        'resultados': resultados
    })

@app.route('/datasets')
def datasets():
    """Busca apenas datasets do dados.gov.br"""
    q = request.args.get('q', '').strip()
    
    if not q:
        # Retorna populares
        datasets = crawler.search_datasets('', rows=20)
    else:
        datasets = crawler.search_datasets(q, rows=20)
    
    return jsonify({
        'termo': q,
        'total': len(datasets),
        'datasets': datasets
    })

@app.route('/catalogo')
def catalogo():
    """Lista todos os portais locais"""
    results = []
    for row in portais_data:
        row_copy = row.copy()
        row_copy['tipo'] = 'portal'
        row_copy['score'] = 50 if row.get('Qualidade') == 'Alta' else 30
        results.append(row_copy)
    
    return jsonify({
        'total': len(results),
        'resultados': results
    })

@app.route('/estatisticas')
def estatisticas():
    """Estatisticas gerais"""
    return jsonify({
        'total_portais': len(portais_data),
        'ufs': len(set(row.get('UF', '') for row in portais_data)),
        'qualidade_alta': len([r for r in portais_data if r.get('Qualidade') == 'Alta']),
        'fontes': ['portais_locais', 'dados.gov.br']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[OK] API Hibrida iniciando na porta {port}")
    print(f"[OK] Portais carregados: {len(portais_data)}")
    print(f"[OK] Dados.gov.br integrado")
    app.run(host='0.0.0.0', port=port)
