from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import os

app = Flask(__name__)
CORS(app)

# Carregar CSV de portais
def carregar_portais():
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Erro ao carregar CSV: {e}")
        return []

PORTAIS = carregar_portais()

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'online',
        'servico': 'Dados Publicos BR API',
        'versao': '2.4-vercel-flask',
        'total_portais': len(PORTAIS),
        'endpoints': ['/api/', '/api/buscar?q=termo']
    })

@app.route('/buscar', methods=['GET'])
def buscar():
    termo = request.args.get('q', '').lower()
    resultados = [p for p in PORTAIS if any(termo in str(v).lower() for v in p.values())]
    return jsonify({
        'termo': termo,
        'total': len(resultados),
        'portais': resultados[:20]
    })

# Para Vercel serverless
if __name__ == '__main__':
    app.run()
