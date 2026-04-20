from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import csv
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Parse query string
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        termo = params.get('q', [''])[0].lower()
        
        # Carregar portais
        portais = self.carregar_portais()
        
        # Filtrar
        resultados = []
        for p in portais:
            if any(termo in str(v).lower() for v in p.values()):
                resultados.append(p)
        
        response = {
            'termo': termo,
            'total': len(resultados),
            'portais': resultados[:20]
        }
        
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
        return
    
    def carregar_portais(self):
        """Carrega portais do CSV"""
        try:
            # Caminho relativo na Vercel
            csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except:
            return []
