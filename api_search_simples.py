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

# Config PostgreSQL (Railway) - Railway gera DATABASE_URL automaticamente
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Usar DATABASE_URL se disponível (Railway), senão usar config individual
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        # Fallback para variáveis individuais
        conn = psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=os.getenv('PGPORT', '5432'),
            database=os.getenv('PGDATABASE', 'railway'),
            user=os.getenv('PGUSER', 'postgres'),
            password=os.getenv('PGPASSWORD', 'postgres')
        )
        return conn

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

@app.route('/importar-csv')
def importar_csv():
    """Importa os 86 portais do CSV para o banco"""
    import csv
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Ler CSV
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'catalogos.csv')
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            portais = list(reader)
        
        inseridos = 0
        for p in portais:
            cur.execute("""
                INSERT INTO documents (titulo, descricao, orgao, estado, url, fonte)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                p.get('Titulo', ''),
                f"{p.get('Esfera', '')} - {p.get('TipoAcesso', '')} - {p.get('Qualidade', '')}",
                p.get('Municipio', 'N/A') or p.get('Esfera', ''),
                p.get('UF', ''),
                p.get('URL', ''),
                'catalogo_csv'
            ))
            inseridos += cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'total_csv': len(portais),
            'inseridos': inseridos,
            'mensagem': f'{inseridos} de {len(portais)} portais importados'
        })
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/setup')
def setup():
    """Cria tabela e insere dados de teste"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Criar tabela
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(500),
                descricao TEXT,
                orgao VARCHAR(255),
                estado VARCHAR(2),
                url VARCHAR(1000),
                fonte VARCHAR(100),
                search_vector tsvector GENERATED ALWAYS AS (
                    to_tsvector('portuguese', 
                        coalesce(titulo, '') || ' ' || 
                        coalesce(descricao, '')
                    )
                ) STORED
            )
        """)
        
        # Criar índice
        cur.execute("CREATE INDEX IF NOT EXISTS idx_search ON documents USING GIN(search_vector)")
        
        # Inserir dados de teste
        dados_teste = [
            ('Saúde Pública Bahia', 'Dados de vacinação e hospitais', 'Secretaria de Saúde', 'BA', 'https://exemplo.com/ba-saude', 'teste'),
            ('Educação São Paulo', 'Escolas e professores', 'Secretaria de Educação', 'SP', 'https://exemplo.com/sp-edu', 'teste'),
            ('Transporte Ceará', 'Ônibus e metrô', 'Secretaria de Transportes', 'CE', 'https://exemplo.com/ce-trans', 'teste'),
            ('Gastos Fortaleza', 'Diárias e licitações', 'Prefeitura de Fortaleza', 'CE', 'https://exemplo.com/fort-gastos', 'teste'),
            ('Saúde Recife', 'Postos de saúde', 'Prefeitura de Recife', 'PE', 'https://exemplo.com/rec-saude', 'teste'),
        ]
        
        for d in dados_teste:
            cur.execute("""
                INSERT INTO documents (titulo, descricao, orgao, estado, url, fonte)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, d)
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'status': 'ok', 'mensagem': 'Tabela criada e 5 registros inseridos'})
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"API Railway - Porta {port}")
    app.run(host='0.0.0.0', port=port)
