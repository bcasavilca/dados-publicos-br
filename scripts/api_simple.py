#!/usr/bin/env python3
"""
Versao simplificada da API - apenas portais locais
Para debug no Render
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os

app = Flask(__name__)
CORS(app, origins=['*'])

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')

def load_data():
    try:
        df = pd.read_csv(CSV_PATH)
        print(f"[OK] Carregados {len(df)} portais")
        return df
    except Exception as e:
        print(f"[ERRO] {e}")
        return pd.DataFrame()

df = load_data()

@app.route('/')
def home():
    return jsonify({
        'nome': 'Dados Publicos BR',
        'versao': '2.6-debug',
        'portais': len(df)
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'portais': len(df)
    })

@app.route('/catalogo')
def catalogo():
    return jsonify({
        'total': len(df),
        'resultados': df.to_dict('records')
    })

@app.route('/buscar')
def buscar():
    q = request.args.get('q', '').lower()
    if not q:
        return jsonify({'erro': 'Termo obrigatorio'}), 400
    
    mask = df.apply(
        lambda row: any(q in str(val).lower() for val in row),
        axis=1
    )
    results = df[mask].to_dict('records')
    
    # Adicionar tipo
    for r in results:
        r['tipo'] = 'portal'
        r['score'] = 50 if r.get('Qualidade') == 'Alta' else 30
    
    return jsonify({
        'busca': q,
        'total': len(results),
        'resultados': results
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
