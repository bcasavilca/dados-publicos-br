#!/usr/bin/env python3
"""
API Gateway Unificado
Roteia entre API de Catálogo e API de Investigação
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Import APIs
from api.catalog import buscar as catalog_buscar
from api.investigation import cerebro as investigation_cerebro

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "services": {
            "catalog": "/api/catalog/*",
            "investigation": "/api/investigation/*"
        }
    })

# Catalog Routes
@app.route('/api/buscar')
def buscar():
    return catalog_buscar.buscar(request.args.get('q'))

# Investigation Routes  
@app.route('/api/analise')
def analise():
    return investigation_cerebro.analisar(request.json)

if __name__ == '__main__':
    app.run(debug=True)
