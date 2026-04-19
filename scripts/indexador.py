#!/usr/bin/env python3
"""
Sincronização PostgreSQL → Meilisearch
Indexa documentos para busca rápida
"""

import psycopg2
import meilisearch
import os
from datetime import datetime

# Configuração
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'dados_publicos'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

MEILI_HOST = os.getenv('MEILI_HOST', 'http://localhost:7700')
MEILI_KEY = os.getenv('MEILI_MASTER_KEY', 'masterKey123')

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_meili_client():
    return meilisearch.Client(MEILI_HOST, MEILI_KEY)

def indexar_documentos(batch_size=100):
    """Indexa documentos não indexados no Meilisearch"""
    
    print("Conectando ao PostgreSQL...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("Conectando ao Meilisearch...")
    meili = get_meili_client()
    
    # Verificar/criar índice
    try:
        meili.get_index('documents')
        print("Índice 'documents' encontrado")
    except:
        print("Criando índice 'documents'...")
        meili.create_index('documents', {'primaryKey': 'id'})
    
    index = meili.index('documents')
    
    # Configurar campos buscáveis
    index.update_searchable_attributes([
        'titulo',
        'descricao', 
        'orgao',
        'estado',
        'categoria'
    ])
    
    # Configurar filtros
    index.update_filterable_attributes([
        'estado',
        'tipo',
        'categoria',
        'fonte'
    ])
    
    # Buscar documentos não indexados
    cur.execute(
        """SELECT id, titulo, descricao, orgao, estado, tipo, 
                  categoria, url, fonte, score_base
           FROM documents 
           WHERE indexed = FALSE 
           LIMIT %s""",
        (batch_size,)
    )
    
    documentos = cur.fetchall()
    
    if not documentos:
        print("Nenhum documento para indexar")
        cur.close()
        conn.close()
        return 0
    
    print(f"Indexando {len(documentos)} documentos...")
    
    # Preparar para Meilisearch
    meili_docs = []
    ids_indexados = []
    
    for doc in documentos:
        meili_doc = {
            'id': str(doc[0]),
            'titulo': doc[1] or '',
            'descricao': doc[2] or '',
            'orgao': doc[3] or '',
            'estado': doc[4] or '',
            'tipo': doc[5] or '',
            'categoria': doc[6] or '',
            'url': doc[7] or '',
            'fonte': doc[8] or '',
            'score': float(doc[9]) if doc[9] else 0.5
        }
        meili_docs.append(meili_doc)
        ids_indexados.append(doc[0])
    
    # Indexar no Meilisearch
    index.add_documents(meili_docs)
    
    # Marcar como indexados no PostgreSQL
    cur.execute(
        """UPDATE documents SET indexed = TRUE WHERE id = ANY(%s)""",
        (ids_indexados,)
    )
    conn.commit()
    
    print(f"✓ {len(documentos)} documentos indexados")
    
    cur.close()
    conn.close()
    
    return len(documentos)

def buscar_meili(query, filtros=None, limite=20):
    """Busca no Meilisearch"""
    meili = get_meili_client()
    index = meili.index('documents')
    
    search_params = {'limit': limite}
    
    if filtros:
        search_params['filter'] = filtros
    
    result = index.search(query, search_params)
    return result

if __name__ == '__main__':
    import sys
    
    print("=" * 80)
    print("INDEXADOR - PostgreSQL → Meilisearch")
    print("=" * 80)
    print()
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python indexador.py sync       # Indexa documentos pendentes")
        print("  python indexador.py buscar 'termo'  # Busca teste")
        print()
        sys.exit(1)
    
    comando = sys.argv[1]
    
    if comando == 'sync':
        total = 0
        while True:
            batch = indexar_documentos(batch_size=100)
            total += batch
            if batch == 0:
                break
        print(f"\n✓ Total indexado: {total} documentos")
    
    elif comando == 'buscar':
        if len(sys.argv) < 3:
            print("Erro: informe o termo de busca")
            sys.exit(1)
        
        termo = sys.argv[2]
        resultados = buscar_meili(termo)
        
        print(f"Buscando: '{termo}'")
        print(f"Encontrados: {resultados.get('estimatedTotalHits', 0)} documentos")
        print()
        
        for hit in resultados.get('hits', [])[:10]:
            print(f"- {hit.get('titulo', 'Sem título')}")
            print(f"  Orgão: {hit.get('orgao', 'N/A')} | Estado: {hit.get('estado', 'N/A')}")
            print(f"  Score: {hit.get('_rankingScore', 0):.2f}")
            print()
