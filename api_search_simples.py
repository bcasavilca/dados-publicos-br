#!/usr/bin/env python3
"""
API Flask - Versão simplificada para Railway
Usa PostgreSQL direto (sem Meilisearch)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os

app = Flask(__name__)
CORS(app)

# Config PostgreSQL (Railway)
DB_CONFIG = {
    'host': os.getenv('RAILWAY_PG_HOST', os.getenv('DB_HOST', 'localhost')),
    'port': os.getenv('RAILWAY_PG_PORT', os.getenv('DB_PORT', '5432')),
    'database': os.getenv('RAILWAY_PG_DATABASE', os.getenv('DB_NAME', 'dados_publicos')),
    'user': os.getenv('RAILWAY_PG_USER', os.getenv('DB_USER', 'postgres')),
    'password': os.getenv('RAILWAY_PG_PASSWORD', os.getenv('DB_PASSWORD', 'postgres'))
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/')
def home():
    """Status"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM documents")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        status = 'online'
    except Exception as e:
        count = 0
        status = f'erro: {str(e)[:50]}'
    
    return jsonify({
        'status': status,
        'versao': '3.0-railway',
        'documentos': count,
        'endpoints': ['/search?q=termo', '/search?q=termo&estado=BA']
    })

@app.route('/search')
def search():
    """Busca no PostgreSQL"""
    query = request.args.get('q', '')
    estado = request.args.get('estado')
    limite = int(request.args.get('limit', 20))
    
    if not query:
        return jsonify({'erro': 'Parâmetro q obrigatório'}), 400
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Busca com full-text search
        sql = """
            SELECT id, titulo, descricao, orgao, estado, url, fonte
            FROM documents
            WHERE search_vector @@ plainto_tsquery('portuguese', %s)
        """
        params = [query]
        
        if estado:
            sql += " AND estado = %s"
            params.append(estado.upper())
        
        sql += " ORDER BY ts_rank(search_vector, plainto_tsquery('portuguese', %s)) DESC"
        params.append(query)
        sql += " LIMIT %s"
        params.append(limite)
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        
        resultados = []
        for row in rows:
            resultados.append({
                'id': row[0],
                'titulo': row[1],
                'descricao': row[2],
                'orgao': row[3],
                'estado': row[4],
                'url': row[5],
                'fonte': row[6]
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            'query': query,
            'total': len(resultados),
            'resultados': resultados
        })
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"API Railway - Porta {port}")
    app.run(host='0.0.0.0', port=port)
