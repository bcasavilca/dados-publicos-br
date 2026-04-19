#!/usr/bin/env python3
"""
API Flask - Versão SEM BANCO DE DADOS
Funciona 100% em qualquer lugar (Vercel, Railway, etc)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import os
import json

app = Flask(__name__)
CORS(app)

# Carregar dados do CSV em memória
PORTAIS = []

def carregar_csv():
    """Carrega CSV na memória ao iniciar"""
    global PORTAIS
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'catalogos.csv')
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            PORTAIS = list(reader)
        print(f"✓ {len(PORTAIS)} portais carregados")
    except Exception as e:
        print(f"Erro ao carregar CSV: {e}")
        PORTAIS = []

# Carregar na inicialização
carregar_csv()

@app.route('/')
def home():
    """Status"""
    return jsonify({
        'status': 'online',
        'versao': '3.0-sem-banco',
        'total_portais': len(PORTAIS),
        'endpoints': [
            '/search?q=termo',
            '/search?q=termo&estado=BA',
            '/portais - lista todos'
        ]
    })

@app.route('/search')
def search():
    """Busca nos portais"""
    query = request.args.get('q', '').lower()
    estado = request.args.get('estado', '').upper()
    limite = int(request.args.get('limit', 20))
    
    if not query and not estado:
        return jsonify({
            'erro': 'Informe q (busca) ou estado (UF)',
            'exemplo': '/search?q=saude&estado=BA'
        }), 400
    
    resultados = []
    for p in PORTAIS:
        match = True
        
        # Filtro por termo
        if query:
            texto = ' '.join(str(v).lower() for v in p.values())
            if query not in texto:
                match = False
        
        # Filtro por estado
        if estado and match:
            uf = p.get('estado', '').upper()
            if estado not in uf:
                match = False
        
        if match:
            resultados.append(p)
    
    # Limitar
    resultados = resultados[:limite]
    
    return jsonify({
        'query': query,
        'estado': estado,
        'total': len(resultados),
        'resultados': resultados
    })

@app.route('/portais')
def listar_portais():
    """Lista todos os portais"""
    limite = int(request.args.get('limit', 100))
    return jsonify({
        'total': len(PORTAIS),
        'portais': PORTAIS[:limite]
    })

@app.route('/estados')
def listar_estados():
    """Lista estados disponíveis"""
    estados = set()
    for p in PORTAIS:
        estados.add(p.get('estado', 'N/A'))
    return jsonify({
        'total': len(estados),
        'estados': sorted(list(estados))
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"API sem banco - Porta {port}")
    app.run(host='0.0.0.0', port=port)
