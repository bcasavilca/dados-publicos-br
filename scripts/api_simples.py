#!/usr/bin/env python3
"""
API Simples - Dados Públicos BR
Versão mínima para garantir funcionamento
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'nome': 'Dados Públicos BR API',
        'versao': '2.1-simple',
        'endpoints': [
            '/',
            '/health',
            '/buscar'
        ]
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'servico': 'online'})

@app.route('/buscar')
def buscar():
    termo = request.args.get('q', '')
    return jsonify({
        'termo': termo,
        'status': 'funcionando',
        'resultados': []
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
