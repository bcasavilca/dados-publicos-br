#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Gateway Unificado
Roteia entre API de Catalogo e API de Investigacao
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Import APIs
from api.catalog import buscar as catalog_buscar

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
@app.route('/api/analise', methods=['POST'])
def analise():
    return jsonify({"status": "not implemented"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
