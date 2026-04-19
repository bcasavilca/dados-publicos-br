#!/usr/bin/env python3
"""
API Flask - Dados Públicos BR v3.0
Usa Meilisearch para busca rápida
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import meilisearch
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Meilisearch config
MEILI_HOST = os.getenv('MEILI_HOST', 'http://localhost:7700')
MEILI_KEY = os.getenv('MEILI_MASTER_KEY', 'masterKey123')
meili_client = meilisearch.Client(MEILI_HOST, MEILI_KEY)

@app.route('/')
def home():
    """Status da API"""
    try:
        stats = meili_client.get_index('documents').get_stats()
        meili_status = 'online'
    except:
        stats = {}
        meili_status = 'offline'
    
    return jsonify({
        'status': 'online',
        'versao': '3.0',
        'meilisearch': meili_status,
        'documentos_indexados': stats.get('numberOfDocuments', 0),
        'endpoints': [
            '/search?q=termo',
            '/search?q=termo&estado=BA',
            '/search?q=termo&tipo=dataset'
        ]
    })

@app.route('/search')
def search():
    """
    Busca em documentos indexados
    
    Parâmetros:
    - q: termo de busca
    - estado: filtro por UF (BA, SP, CE...)
    - tipo: filtro por tipo (dataset, portal)
    - categoria: filtro por categoria
    - limit: limite de resultados (padrão: 20)
    """
    query = request.args.get('q', '')
    estado = request.args.get('estado')
    tipo = request.args.get('tipo')
    categoria = request.args.get('categoria')
    limite = int(request.args.get('limit', 20))
    
    if not query:
        return jsonify({
            'erro': 'Parâmetro q é obrigatório',
            'exemplo': '/search?q=saude+BA'
        }), 400
    
    try:
        index = meili_client.index('documents')
        
        # Montar filtros
        filtros = []
        if estado:
            filtros.append(f'estado = "{estado.upper()}"')
        if tipo:
            filtros.append(f'tipo = "{tipo}"')
        if categoria:
            filtros.append(f'categoria = "{categoria}"')
        
        search_params = {'limit': limite}
        if filtros:
            search_params['filter'] = ' AND '.join(filtros)
        
        # Executar busca
        result = index.search(query, search_params)
        
        return jsonify({
            'query': query,
            'total': result.get('estimatedTotalHits', 0),
            'tempo_ms': result.get('processingTimeMs', 0),
            'resultados': result.get('hits', [])
        })
    
    except Exception as e:
        return jsonify({
            'erro': 'Erro na busca',
            'mensagem': str(e)
        }), 500

@app.route('/autocomplete')
def autocomplete():
    """Sugestões de autocomplete"""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify({'sugestoes': []})
    
    try:
        index = meili_client.index('documents')
        result = index.search(query, {'limit': 5})
        
        sugestoes = []
        for hit in result.get('hits', []):
            titulo = hit.get('titulo', '')
            if titulo and titulo not in sugestoes:
                sugestoes.append(titulo)
        
        return jsonify({
            'query': query,
            'sugestoes': sugestoes[:5]
        })
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/stats')
def stats():
    """Estatísticas do sistema"""
    try:
        index = meili_client.index('documents')
        stats = index.get_stats()
        
        return jsonify({
            'documentos': stats.get('numberOfDocuments', 0),
            'tamanho': stats.get('size', 0),
            'atualizacao': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 80)
    print("API v3.0 - Search com Meilisearch")
    print("=" * 80)
    print(f"Porta: {port}")
    print(f"Meilisearch: {MEILI_HOST}")
    print("=" * 80)
    app.run(host='0.0.0.0', port=port)
