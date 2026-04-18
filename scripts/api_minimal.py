#!/usr/bin/env python3
"""
Versao MINIMAL - sem dependencias pesadas
"""
from flask import Flask, jsonify
from flask_cors import CORS
import csv
import os

app = Flask(__name__)
CORS(app, origins=['*'])

# Carregar CSV manualmente
def load_csv():
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Erro ao carregar CSV: {e}")
        return []

data = load_csv()

@app.route('/')
def home():
    return jsonify({'status': 'ok', 'portais': len(data)})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'portais': len(data)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[OK] Servidor iniciando na porta {port}")
    print(f"[OK] Carregados {len(data)} portais")
    app.run(host='0.0.0.0', port=port)
