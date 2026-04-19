from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import os

app = Flask(__name__)
CORS(app)

# Carregar CSV de portais
def carregar_portais():
    try:
        # Caminho para Vercel (raiz do projeto)
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'catalogos.csv')
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Erro ao carregar CSV: {e}")
        return []

PORTAIS = carregar_portais()

@app.route('/api/', methods=['GET'])
def home():
    return jsonify({
        'status': 'online',
        'servico': 'Dados Publicos BR API',
        'versao': '2.5-vercel',
        'total_portais': len(PORTAIS),
        'endpoints': ['/api/', '/api/buscar?q=termo']
    })

@app.route('/api/buscar', methods=['GET'])
def buscar():
    termo = request.args.get('q', '').lower()
    resultados = [p for p in PORTAIS if any(termo in str(v).lower() for v in p.values())]
    return jsonify({
        'termo': termo,
        'total': len(resultados),
        'portais': resultados[:20]
    })

# Handler Vercel
def handler(request):
    """Entry point para Vercel serverless"""
    from werkzeug.wrappers import Request as WerkzeugRequest
    
    # Adaptar request do Vercel para Flask
    with app.test_client() as client:
        path = request.get('path', '/')
        query = request.get('query', {})
        
        # Montar URL
        url = path
        if query:
            from urllib.parse import urlencode
            url += '?' + urlencode(query)
        
        response = client.get(url)
        return {
            'statusCode': response.status_code,
            'body': response.get_json(),
            'headers': {'Content-Type': 'application/json'}
        }

# Local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
