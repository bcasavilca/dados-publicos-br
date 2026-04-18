#!/usr/bin/env python3
"""
Sistema de monitoramento de portais públicos
Verifica uptime, latência e confiabilidade
"""

import requests
import csv
import time
import json
from datetime import datetime
from typing import Dict, List
import concurrent.futures

class PortalMonitor:
    """
    Monitora disponibilidade de portais de dados públicos
    """
    
    def __init__(self, csv_path: str = '../data/catalogos.csv'):
        self.csv_path = csv_path
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DadosPublicosBR-Monitor/1.0'
        })
    
    def load_portais(self) -> List[Dict]:
        """Carrega lista de portais do CSV"""
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception as e:
            print(f"[Erro] Carregar CSV: {e}")
            return []
    
    def check_portal(self, portal: Dict) -> Dict:
        """
        Verifica status de um portal
        """
        url = portal.get('URL', '')
        if not url:
            return None
        
        resultado = {
            'titulo': portal.get('Titulo', ''),
            'url': url,
            'uf': portal.get('UF', ''),
            'municipio': portal.get('Municipio', ''),
            'checked_at': datetime.now().isoformat(),
            'status': 'unknown',
            'latency_ms': None,
            'error': None
        }
        
        try:
            start = time.time()
            response = self.session.get(
                url, 
                timeout=10,
                allow_redirects=True,
                verify=False  # Alguns certificados são inválidos
            )
            elapsed = (time.time() - start) * 1000
            
            resultado['latency_ms'] = round(elapsed, 2)
            
            if response.status_code == 200:
                resultado['status'] = 'online'
            elif response.status_code in [301, 302, 307, 308]:
                resultado['status'] = 'redirect'
            elif response.status_code >= 500:
                resultado['status'] = 'server_error'
            else:
                resultado['status'] = f'http_{response.status_code}'
                
        except requests.exceptions.Timeout:
            resultado['status'] = 'timeout'
            resultado['error'] = 'Timeout apos 10s'
        except requests.exceptions.ConnectionError:
            resultado['status'] = 'connection_error'
            resultado['error'] = 'Nao foi possivel conectar'
        except Exception as e:
            resultado['status'] = 'error'
            resultado['error'] = str(e)
        
        return resultado
    
    def check_all(self, max_workers: int = 10) -> List[Dict]:
        """
        Verifica todos os portais em paralelo
        """
        portais = self.load_portais()
        print(f"[Monitor] Verificando {len(portais)} portais...")
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_portal = {
                executor.submit(self.check_portal, portal): portal 
                for portal in portais
            }
            
            for future in concurrent.futures.as_completed(future_to_portal):
                result = future.result()
                if result:
                    results.append(result)
                    status = result['status']
                    lat = result.get('latency_ms', 'N/A')
                    print(f"  {result['titulo'][:40]:40} | {status:15} | {lat}ms")
        
        self.results = results
        return results
    
    def generate_report(self) -> Dict:
        """
        Gera relatório de status
        """
        if not self.results:
            return {}
        
        total = len(self.results)
        online = len([r for r in self.results if r['status'] == 'online'])
        offline = len([r for r in self.results if r['status'] in ['timeout', 'connection_error']])
        degraded = total - online - offline
        
        # Latência média dos online
        latencies = [r['latency_ms'] for r in self.results if r.get('latency_ms')]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_portais': total,
            'online': online,
            'offline': offline,
            'degraded': degraded,
            'online_percentage': round(online / total * 100, 1) if total else 0,
            'avg_latency_ms': round(avg_latency, 2),
            'results': self.results
        }
        
        return report
    
    def save_report(self, filename: str = '../data/monitor_report.json'):
        """Salva relatório em JSON"""
        report = self.generate_report()
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"[Monitor] Relatório salvo em {filename}")
        except Exception as e:
            print(f"[Erro] Salvar relatório: {e}")
    
    def print_summary(self):
        """Mostra resumo no console"""
        report = self.generate_report()
        
        print("\n" + "=" * 80)
        print("RELATÓRIO DE MONITORAMENTO")
        print("=" * 80)
        print(f"Gerado em: {report['generated_at']}")
        print(f"Total de portais: {report['total_portais']}")
        print(f"Online: {report['online']} ({report['online_percentage']}%)")
        print(f"Offline: {report['offline']}")
        print(f"Degradados: {report['degraded']}")
        print(f"Latência média: {report['avg_latency_ms']}ms")
        print("=" * 80)
        
        # Lista de offline
        offline_list = [r for r in self.results if r['status'] in ['timeout', 'connection_error']]
        if offline_list:
            print("\n⚠️ PORTAIS OFFLINE:")
            for r in offline_list:
                print(f"  - {r['titulo']} ({r['uf']})")
                print(f"    Erro: {r.get('error', 'N/A')}")


if __name__ == "__main__":
    monitor = PortalMonitor()
    
    # Verificar todos
    monitor.check_all(max_workers=5)
    
    # Mostrar resumo
    monitor.print_summary()
    
    # Salvar relatório
    monitor.save_report()
