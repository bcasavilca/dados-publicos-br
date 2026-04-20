#!/usr/bin/env python3
"""
Crawler para dados.gov.br
Busca e indexa datasets da API CKAN
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict

class DadosGovCrawler:
    """
    Crawler para API CKAN do dados.gov.br
    """
    
    BASE_URL = "https://dados.gov.br/api/3/action"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DadosPublicosBR-Crawler/1.0'
        })
        self.datasets = []
    
    def crawl_all(self, limit: int = 1000) -> List[Dict]:
        """
        Busca todos os datasets disponíveis
        """
        print(f"[Crawler] Iniciando busca de até {limit} datasets...")
        
        datasets = []
        offset = 0
        batch_size = 100
        
        while len(datasets) < limit:
            try:
                url = f"{self.BASE_URL}/package_search"
                params = {
                    'rows': min(batch_size, limit - len(datasets)),
                    'start': offset,
                    'sort': 'score desc'
                }
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                if not data.get('success'):
                    print(f"[Crawler] Erro na API: {data}")
                    break
                
                results = data['result']['results']
                
                if not results:
                    print(f"[Crawler] Nenhum resultado na página {offset}")
                    break
                
                for dataset in results:
                    normalized = self._normalize_dataset(dataset)
                    if normalized:
                        datasets.append(normalized)
                
                offset += len(results)
                print(f"[Crawler] Coletados {len(datasets)} datasets...")
                
                # Delay para não sobrecarregar API
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[Crawler] Erro: {e}")
                break
        
        print(f"[Crawler] Total coletado: {len(datasets)} datasets")
        return datasets
    
    def search_datasets(self, query: str, rows: int = 50) -> List[Dict]:
        """
        Busca específica por termo
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
                return [self._normalize_dataset(d) for d in results if self._normalize_dataset(d)]
            
            return []
            
        except Exception as e:
            print(f"[Crawler] Erro na busca: {e}")
            return []
    
    def _normalize_dataset(self, dataset: Dict) -> Dict:
        """
        Normaliza dataset do CKAN para formato padronizado
        """
        try:
            # Extrair recursos
            resources = dataset.get('resources', [])
            main_resource = resources[0] if resources else {}
            
            # Determinar formato
            formato = self._detect_format(main_resource.get('format', ''))
            
            # Calcular score
            score = self._calculate_score(dataset, resources)
            
            # Extrair tags
            tags = [t['name'] for t in dataset.get('tags', [])[:10]]
            
            # Determinar qualidade
            qualidade = self._classify_quality(formato, score)
            
            return {
                'tipo': 'dataset',
                'id': dataset.get('id', ''),
                'titulo': dataset.get('title', ''),
                'descricao': dataset.get('notes', '')[:500] if dataset.get('notes') else '',
                'url': f"https://dados.gov.br/dados/conjuntos-dados/{dataset.get('name', '')}",
                'fonte': 'dados.gov.br',
                'organizacao': dataset.get('organization', {}).get('title', 'Desconhecida'),
                'formato': formato,
                'score': score,
                'qualidade': qualidade,
                'tags': tags,
                'atualizado': dataset.get('metadata_modified', '')[:10],
                'criado': dataset.get('metadata_created', '')[:10],
                'acessos_recentes': dataset.get('tracking_summary', {}).get('recent', 0),
                'total_acessos': dataset.get('tracking_summary', {}).get('total', 0),
                'download_url': main_resource.get('url', ''),
                'licenca': dataset.get('license_title', 'Não especificada'),
                'total_recursos': len(resources)
            }
            
        except Exception as e:
            print(f"[Crawler] Erro ao normalizar: {e}")
            return None
    
    def _detect_format(self, format_str: str) -> str:
        """Detecta formato do arquivo"""
        fmt = format_str.upper() if format_str else ''
        
        formatos = {
            'CSV': 'CSV',
            'JSON': 'JSON',
            'XLS': 'XLS',
            'XLSX': 'XLS',
            'PDF': 'PDF',
            'API': 'API',
            'SHP': 'Geoespacial',
            'GEOJSON': 'Geoespacial',
            'XML': 'XML',
            'HTML': 'HTML'
        }
        
        return formatos.get(fmt, 'Outro')
    
    def _calculate_score(self, dataset: Dict, resources: List) -> int:
        """Calcula score de utilidade"""
        score = 0
        
        # Tem recursos
        if resources:
            score += 15
        
        # Formato aberto
        open_formats = ['CSV', 'JSON', 'XLS', 'XLSX', 'API']
        for r in resources:
            if r.get('format', '').upper() in open_formats:
                score += 10
                break
        
        # Tem descrição detalhada
        desc = dataset.get('notes', '')
        if desc and len(desc) > 100:
            score += 10
        elif desc:
            score += 5
        
        # Tags organizadas
        tags = dataset.get('tags', [])
        score += min(len(tags) * 2, 15)
        
        # Atualizado recentemente
        if dataset.get('metadata_modified'):
            score += 5
        
        # Popularidade
        views = dataset.get('tracking_summary', {}).get('recent', 0)
        score += min(views // 20, 20)
        
        # Tem licença aberta
        license = dataset.get('license_id', '')
        if 'cc' in license.lower() or 'open' in license.lower():
            score += 5
        
        return min(score, 100)
    
    def _classify_quality(self, formato: str, score: int) -> str:
        """Classifica qualidade"""
        if formato in ['CSV', 'JSON', 'API'] and score >= 60:
            return 'Alta'
        elif formato in ['XLS', 'XLSX'] and score >= 50:
            return 'Alta'
        elif formato == 'PDF':
            return 'Baixa'
        elif score >= 40:
            return 'Media'
        else:
            return 'Baixa'
    
    def save_to_json(self, datasets: List[Dict], filename: str = 'datasets_cache.json'):
        """Salva datasets em cache JSON"""
        filepath = f"data/{filename}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(datasets),
                'atualizado': datetime.now().isoformat(),
                'datasets': datasets
            }, f, ensure_ascii=False, indent=2)
        
        print(f"[Crawler] Salvo em {filepath}")
    
    def load_from_json(self, filename: str = 'datasets_cache.json') -> List[Dict]:
        """Carrega datasets do cache"""
        try:
            filepath = f"data/{filename}"
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('datasets', [])
        except:
            return []


if __name__ == "__main__":
    crawler = DadosGovCrawler()
    
    # Teste: buscar datasets populares
    print("=" * 80)
    print("CRAWLER DADOS.GOV.BR - TESTE")
    print("=" * 80)
    
    # Buscar por termo
    print("\nBuscando 'saude'...")
    datasets = crawler.search_datasets("saude", rows=10)
    
    for ds in datasets:
        print(f"\n📊 {ds['titulo'][:60]}")
        print(f"   Score: {ds['score']} | Qualidade: {ds['qualidade']}")
        print(f"   Formato: {ds['formato']} | Org: {ds['organizacao']}")
        print(f"   Tags: {', '.join(ds['tags'][:5])}")
    
    print(f"\n{'=' * 80}")
    print(f"Total encontrado: {len(datasets)} datasets")
    print("=" * 80)
