#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integracao com dados.gov.br
Busca datasets reais via API CKAN do governo federal
"""

import requests
import pandas as pd
from typing import List, Dict
import time

class DadosGovClient:
    """
    Cliente para API do dados.gov.br (CKAN)
    """
    
    BASE_URL = "https://dados.gov.br/api/3/action"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DadosPublicosBR/1.0'
        })
    
    def search_datasets(self, query: str = "", rows: int = 100) -> List[Dict]:
        """
        Busca datasets na API do dados.gov.br
        """
        url = f"{self.BASE_URL}/package_search"
        
        params = {
            'q': query,
            'rows': rows,
            'sort': 'score desc'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                results = data['result']['results']
                return self._normalize_datasets(results)
            
            return []
            
        except Exception as e:
            print(f"Erro ao buscar datasets: {e}")
            return []
    
    def get_popular_datasets(self, rows: int = 20) -> List[Dict]:
        """
        Retorna datasets mais populares
        """
        url = f"{self.BASE_URL}/package_search"
        
        params = {
            'rows': rows,
            'sort': 'views_recent desc'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('success'):
                results = data['result']['results']
                return self._normalize_datasets(results)
            
            return []
            
        except Exception as e:
            print(f"Erro ao buscar populares: {e}")
            return []
    
    def get_organization_datasets(self, org_id: str, rows: int = 50) -> List[Dict]:
        """
        Busca datasets de uma organizacao especifica
        Ex: "ministerio-da-saude", "receita-federal"
        """
        return self.search_datasets(query=f"organization:{org_id}", rows=rows)
    
    def _normalize_datasets(self, results: List[Dict]) -> List[Dict]:
        """
        Normaliza os dados do formato CKAN para formato padrao
        """
        normalized = []
        
        for dataset in results:
            # Extrair recursos (arquivos)
            resources = dataset.get('resources', [])
            
            # Pegar o primeiro recurso como principal
            main_resource = resources[0] if resources else {}
            
            # Determinar formato
            formato = self._detect_format(main_resource.get('format', ''))
            
            # Score de utilidade
            score = self._calculate_score(dataset, resources)
            
            normalized.append({
                'tipo': 'dataset',
                'titulo': dataset.get('title', ''),
                'descricao': dataset.get('notes', '')[:200] + '...' if dataset.get('notes') else '',
                'url': f"https://dados.gov.br/dados/conjuntos-dados/{dataset.get('name', '')}",
                'fonte': 'dados.gov.br',
                'organizacao': dataset.get('organization', {}).get('title', ''),
                'formato': formato,
                'score': score,
                'tags': [tag['name'] for tag in dataset.get('tags', [])[:5]],
                'atualizado': dataset.get('metadata_modified', '')[:10],
                'acessos': dataset.get('tracking_summary', {}).get('recent', 0),
                'download_url': main_resource.get('url', ''),
                'qualidade': self._classify_quality(formato, score)
            })
        
        return normalized
    
    def _detect_format(self, format_str: str) -> str:
        """
        Detecta formato do arquivo
        """
        fmt = format_str.upper()
        
        if fmt in ['CSV']:
            return 'CSV'
        elif fmt in ['JSON']:
            return 'JSON'
        elif fmt in ['XLS', 'XLSX', 'ODS']:
            return 'XLS'
        elif fmt in ['PDF']:
            return 'PDF'
        elif fmt in ['SHP', 'GEOJSON']:
            return 'Geoespacial'
        elif fmt in ['XML', 'XML/RDF']:
            return 'XML'
        elif fmt in ['API']:
            return 'API'
        else:
            return 'Outro'
    
    def _calculate_score(self, dataset: Dict, resources: List[Dict]) -> int:
        """
        Calcula score de utilidade do dataset
        """
        score = 0
        
        # Tem recursos disponiveis
        if resources:
            score += 10
        
        # Formato aberto
        open_formats = ['CSV', 'JSON', 'XLS', 'XLSX']
        for r in resources:
            if r.get('format', '').upper() in open_formats:
                score += 5
                break
        
        # Tem descricao
        if dataset.get('notes'):
            score += 5
        
        # Tags organizadas
        if dataset.get('tags'):
            score += min(len(dataset['tags']), 5)
        
        # Atualizado recentemente
        if dataset.get('metadata_modified'):
            score += 3
        
        # Popularidade (acessos recentes)
        views = dataset.get('tracking_summary', {}).get('recent', 0)
        score += min(views // 10, 10)
        
        return min(score, 100)
    
    def _classify_quality(self, formato: str, score: int) -> str:
        """
        Classifica qualidade baseada em formato e score
        """
        if formato in ['CSV', 'JSON', 'API'] and score >= 50:
            return 'Alta'
        elif formato in ['XLS', 'XLSX'] and score >= 30:
            return 'Alta'
        elif formato == 'PDF':
            return 'Baixa'
        elif score >= 30:
            return 'Media'
        else:
            return 'Baixa'
    
    def get_preview(self, dataset_url: str) -> Dict:
        """
        Tenta obter preview de dados (primeiras linhas)
        AINDA NAO IMPLEMENTADO - requer download e parsing
        """
        return {
            'status': 'em_desenvolvimento',
            'message': 'Preview de dados sera implementado em versao futura'
        }

# Funcao de conveniencia
def search_hibrido(termo: str, catalogo_local: pd.DataFrame = None) -> Dict:
    """
    Busca hibrida: portais locais + datasets do dados.gov.br
    """
    client = DadosGovClient()
    
    print(f"Buscando: '{termo}'...")
    
    # Buscar datasets no dados.gov.br
    datasets = client.search_datasets(query=termo, rows=20)
    
    # Buscar em portais locais se fornecido
    portais = []
    if catalogo_local is not None:
        mask = catalogo_local.apply(
            lambda row: any(termo.lower() in str(val).lower() for val in row),
            axis=1
        )
        portais = catalogo_local[mask].to_dict('records')
    
    return {
        'termo': termo,
        'total_datasets': len(datasets),
        'total_portais': len(portais),
        'datasets': datasets,
        'portais': portais
    }

if __name__ == "__main__":
    # Teste
    client = DadosGovClient()
    
    print("=" * 80)
    print("BUSCA HIBRIDA - DADOS.GOV.BR + CATALOGO LOCAL")
    print("=" * 80)
    
    # Buscar datasets populares
    print("\n--- Datasets Populares ---")
    populares = client.get_popular_datasets(rows=5)
    
    for ds in populares:
        print(f"\n📊 {ds['titulo'][:50]}")
        print(f"   Score: {ds['score']}/100 | Qualidade: {ds['qualidade']}")
        print(f"   Formato: {ds['formato']} | Acessos: {ds['acessos']}")
        print(f"   URL: {ds['url']}")
    
    # Busca especifica
    print("\n" + "=" * 80)
    print("Busca: 'saude'")
    print("=" * 80)
    
    resultados = client.search_datasets(query="saude", rows=5)
    for ds in resultados:
        print(f"\n🏥 {ds['titulo']}")
        print(f"   {ds['descricao'][:100]}...")
        print(f"   Organizacao: {ds['organizacao']}")
