from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import csv
import os

# Carregar CSV de portais
def carregar_portais():
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except:
        return []

PORTAIS = carregar_portais()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Roteamento simples
        if '/buscar' in path:
            termo = params.get('q', [''])[0].lower()
            resultados = [p for p in PORTAIS if any(termo in str(v).lower() for v in p.values())]
            response = {'termo': termo, 'total': len(resultados), 'portais': resultados[:20]}
        else:
            # Health check
            response = {
                'status': 'online',
                'servico': 'Dados Publicos BR API',
                'versao': '2.3-vercel',
                'total_portais': len(PORTAIS),
                'endpoints': ['/api/', '/api/buscar?q=termo']
            }
        
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
