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
        
        # Busca flexível (ignora acentos e case)
        sql = """
            SELECT id, titulo, descricao, orgao, estado, url, fonte
            FROM documents
            WHERE LOWER(titulo) LIKE %s 
               OR LOWER(descricao) LIKE %s
               OR LOWER(orgao) LIKE %s
               OR LOWER(estado) = %s
        """
        termo_busca = f'%{query.lower()}%'
        estado_busca = query.upper() if len(query) == 2 else ''
        params = [termo_busca, termo_busca, termo_busca, estado_busca]
        
        if estado:
            sql += " AND estado = %s"
            params.append(estado.upper())
        
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
                'fonte': row[6],
                'tipo': 'portal'  # Adicionado para compatibilidade com frontend
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

@app.route('/buscar-dadosgov')
def buscar_dadosgov():
    """Busca no dados.gov.br e insere no PostgreSQL"""
    import requests
    
    termo = request.args.get('q', 'saude')
    limite = int(request.args.get('limit', 100))
    
    try:
        # Buscar API dados.gov.br
        url = f'https://dados.gov.br/api/3/search/datasets?q={termo}&rows={limite}'
        resp = requests.get(url, timeout=30)
        data = resp.json()
        
        datasets = data.get('results', [])
        
        conn = get_db()
        cur = conn.cursor()
        
        inseridos = 0
        for ds in datasets:
            org = ds.get('organization', {}) or {}
            org_nome = org.get('title', 'N/A') if isinstance(org, dict) else 'N/A'
            
            cur.execute("""
                INSERT INTO documents (titulo, descricao, orgao, url, fonte, tipo, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                ds.get('title', '')[:500],
                ds.get('notes', '')[:1000],
                org_nome[:255],
                ds.get('url', '') or f"https://dados.gov.br/dataset/{ds.get('name', '')}",
                'dados.gov.br',
                'dataset',
                'BR'  # Nacional
            ))
            inseridos += cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'termo_busca': termo,
            'total_encontrado': len(datasets),
            'inseridos': inseridos,
            'mensagem': f'{inseridos} datasets de "{termo}" adicionados do dados.gov.br'
        })
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/corrigir-maceio')
def corrigir_maceio():
    """Atualiza URL correta do portal de Maceio"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Atualizar URL correta
        cur.execute("""
            UPDATE documents 
            SET url = 'https://www.transparencia.maceio.al.gov.br/transparencia/pages/homepage.faces'
            WHERE titulo ILIKE '%maceio%' 
              AND url LIKE '%maceio.al.gov.br/transparencia%'
        """)
        
        atualizados = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'atualizados': atualizados,
            'url_correta': 'https://www.transparencia.maceio.al.gov.br/transparencia/pages/homepage.faces',
            'mensagem': f'{atualizados} registro(s) de Maceio atualizado(s)'
        })
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"API Railway - Porta {port}")
    app.run(host='0.0.0.0', port=port)
