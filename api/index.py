from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import os

app = Flask(__name__)
CORS(app)

# Carregar CSV de portais
def carregar_portais():
    try:
        # Vercel serverless: ../data/catalogos.csv
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Erro: {e}")
        return []

PORTAIS = carregar_portais()

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'online',
        'total_portais': len(PORTAIS)
    })

@app.route('/buscar', methods=['GET'])
def buscar():
    termo = request.args.get('q', '').lower()
    resultados = [p for p in PORTAIS if any(termo in str(v).lower() for v in p.values())]
    return jsonify({'termo': termo, 'total': len(resultados), 'portais': resultados[:20]})
