#!/usr/bin/env python3
"""
Pipeline de ingestão - Dados Públicos BR
Busca dados de APIs externas e salva no PostgreSQL
"""

import psycopg2
import requests
import json
from datetime import datetime
import hashlib
import sys
import os
from urllib.parse import urlencode

# Configuração PostgreSQL
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'dados_publicos'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

def get_db_connection():
    """Retorna conexão com PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)

def criar_hash(payload):
    """Cria hash único para evitar duplicatas"""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

def registrar_job(tipo, fonte_id=None):
    """Cria job de ingestão"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO ingest_jobs (fonte_id, tipo, status, started_at) 
           VALUES (%s, %s, 'rodando', NOW()) RETURNING id""",
        (fonte_id, tipo)
    )
    job_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return job_id

def finalizar_job(job_id, status, registros_coletados=0, registros_novos=0, erro_msg=None):
    """Finaliza job de ingestão"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE ingest_jobs 
           SET status=%s, registros_coletados=%s, registros_novos=%s, 
               erro_msg=%s, finished_at=NOW()
           WHERE id=%s""",
        (status, registros_coletados, registros_novos, erro_msg, job_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def salvar_raw(fonte_id, tipo, payload):
    """Salva dados brutos no PostgreSQL"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    hash_val = criar_hash(payload)
    
    # Verificar duplicata
    cur.execute("SELECT id FROM raw_data WHERE hash=%s", (hash_val,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return None  # Duplicata
    
    # Inserir
    cur.execute(
        """INSERT INTO raw_data (fonte_id, tipo, payload_json, hash)
           VALUES (%s, %s, %s, %s) RETURNING id""",
        (fonte_id, tipo, json.dumps(payload), hash_val)
    )
    raw_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return raw_id

def normalizar_documento(raw_id, fonte, payload):
    """Normaliza dados brutos para documento buscável"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Extrair campos comuns
    titulo = payload.get('titulo') or payload.get('title') or payload.get('name', '')
    descricao = payload.get('descricao') or payload.get('description') or payload.get('notes', '')
    orgao = payload.get('orgao') or payload.get('organization', {}).get('title', '')
    url = payload.get('url') or payload.get('link', '')
    
    cur.execute(
        """INSERT INTO documents 
           (raw_id, titulo, descricao, orgao, tipo, url, fonte, fonte_nome, indexed)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE)""",
        (raw_id, titulo[:500], descricao, orgao[:255], 'dataset', url[:1000], 
         fonte, payload.get('fonte_nome', fonte), False)
    )
    conn.commit()
    cur.close()
    conn.close()

class IngestorDadosGov:
    """Ingestor para dados.gov.br"""
    
    BASE_URL = 'https://dados.gov.br/api/3'
    
    def __init__(self):
        self.fonte_id = 1  # ID no banco
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'DadosPublicosBR/1.0'})
    
    def buscar_datasets(self, termo='', limite=100):
        """Busca datasets no dados.gov.br"""
        params = {'q': termo, 'rows': limite}
        url = f"{self.BASE_URL}/search/datasets"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except Exception as e:
            print(f"Erro ao buscar dados.gov.br: {e}")
            return []
    
    def ingest(self, termo='', limite=100):
        """Executa ingestão completa"""
        job_id = registrar_job('dadosgov', self.fonte_id)
        
        try:
            datasets = self.buscar_datasets(termo, limite)
            registros = 0
            novos = 0
            
            print(f"Coletados {len(datasets)} datasets de dados.gov.br")
            
            for ds in datasets:
                registros += 1
                
                # Adicionar metadados
                ds['fonte_nome'] = 'dados.gov.br'
                ds['url'] = ds.get('link') or f"https://dados.gov.br/dataset/{ds.get('name', '')}"
                
                # Salvar raw
                raw_id = salvar_raw(self.fonte_id, 'dataset', ds)
                if raw_id:
                    novos += 1
                    normalizar_documento(raw_id, 'dados.gov.br', ds)
                
                if registros % 10 == 0:
                    print(f"  Processados {registros}/{len(datasets)}...")
            
            finalizar_job(job_id, 'sucesso', registros, novos)
            print(f"✓ Ingestão concluída: {novos} novos registros")
            
        except Exception as e:
            finalizar_job(job_id, 'erro', erro_msg=str(e))
            print(f"✗ Erro na ingestão: {e}")
            raise

def ingest_manual_csv(caminho_csv, fonte_nome='CSV Manual'):
    """Ingestão manual de CSV de portais"""
    import csv
    
    job_id = registrar_job('csv_manual')
    registros = 0
    novos = 0
    
    try:
        with open(caminho_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                registros += 1
                
                # Normalizar payload
                payload = {
                    'titulo': row.get('nome', row.get('titulo', '')),
                    'descricao': row.get('descricao', row.get('descricao', '')),
                    'orgao': row.get('municipio', row.get('estado', '')),
                    'url': row.get('url', ''),
                    'fonte_nome': fonte_nome
                }
                
                raw_id = salvar_raw(None, 'portal', payload)
                if raw_id:
                    novos += 1
                    normalizar_documento(raw_id, fonte_nome, payload)
        
        finalizar_job(job_id, 'sucesso', registros, novos)
        print(f"✓ CSV ingerido: {novos} registros novos")
        
    except Exception as e:
        finalizar_job(job_id, 'erro', erro_msg=str(e))
        raise

if __name__ == '__main__':
    print("=" * 80)
    print("PIPELINE DE INGESTÃO - Dados Públicos BR")
    print("=" * 80)
    print()
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python ingest.py dadosgov [termo] [limite]")
        print("  python ingest.py csv caminho/arquivo.csv")
        print()
        sys.exit(1)
    
    comando = sys.argv[1]
    
    if comando == 'dadosgov':
        termo = sys.argv[2] if len(sys.argv) > 2 else ''
        limite = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        
        ingestor = IngestorDadosGov()
        ingestor.ingest(termo, limite)
    
    elif comando == 'csv':
        if len(sys.argv) < 3:
            print("Erro: informe o caminho do CSV")
            sys.exit(1)
        ingest_manual_csv(sys.argv[2])
    
    else:
        print(f"Comando desconhecido: {comando}")
