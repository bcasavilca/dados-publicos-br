#!/usr/bin/env python3
"""
Verificador de status de portais
Atualiza o CSV com informação de online/offline
"""

import csv
import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class VerificadorPortais:
    """
    Verifica quais portais estão online
    """
    
    def __init__(self, timeout=10, max_workers=5):
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (DadosPublicosBR-Check/1.0)'
        })
    
    def verificar_portal(self, url: str) -> dict:
        """
        Verifica se um portal está online
        """
        resultado = {
            'url': url,
            'status': 'offline',
            'http_code': None,
            'tempo_ms': None,
            'erro': None,
            'verificado_em': datetime.now().isoformat()
        }
        
        try:
            inicio = time.time()
            response = self.session.get(
                url, 
                timeout=self.timeout,
                allow_redirects=True,
                verify=False
            )
            tempo = (time.time() - inicio) * 1000
            
            resultado['http_code'] = response.status_code
            resultado['tempo_ms'] = round(tempo, 2)
            
            if response.status_code == 200:
                resultado['status'] = 'online'
            else:
                resultado['status'] = f'http_{response.status_code}'
                
        except requests.exceptions.Timeout:
            resultado['status'] = 'timeout'
            resultado['erro'] = 'Timeout'
        except requests.exceptions.ConnectionError:
            resultado['status'] = 'connection_error'
            resultado['erro'] = 'Nao conectou'
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erro'] = str(e)[:50]
        
        return resultado
    
    def verificar_todos(self, csv_path='data/catalogos.csv') -> list:
        """
        Verifica todos os portais do CSV
        """
        print(f"[Verificador] Carregando portais de {csv_path}...")
        
        # Carregar CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            portais = list(reader)
        
        print(f"[Verificador] {len(portais)} portais carregados")
        print(f"[Verificador] Timeout: {self.timeout}s | Workers: {self.max_workers}")
        print()
        
        resultados = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter todas as verificações
            future_to_portal = {
                executor.submit(self.verificar_portal, p['URL']): p 
                for p in portais
            }
            
            # Processar resultados
            for future in as_completed(future_to_portal):
                portal = future_to_portal[future]
                try:
                    verificacao = future.result()
                    
                    # Adicionar ao portal
                    portal['Status'] = verificacao['status']
                    portal['HTTP_Code'] = verificacao['http_code']
                    portal['Tempo_MS'] = verificacao['tempo_ms']
                    portal['Verificado_Em'] = verificacao['verificado_em']
                    
                    resultados.append(portal)
                    
                    status_icon = "OK" if verificacao['status'] == 'online' else "OFF"
                    print(f"  [{status_icon}] {portal['Titulo'][:45]:45} | {verificacao['status']}")
                    
                    # Delay para não sobrecarregar
                    time.sleep(0.3)
                    
                except Exception as e:
                    print(f"  [ERRO] Em {portal['Titulo']}: {e}")
        
        return resultados
    
    def salvar_resultados(self, portais: list, csv_path='data/catalogos.csv'):
        """
        Salva resultados de volta no CSV
        """
        # Definir campos (incluindo novos de status)
        campos = [
            'Titulo', 'URL', 'Municipio', 'UF', 'Esfera', 'Poder',
            'TipoFonte', 'TipoAcesso', 'Formato', 'Qualidade', 
            'Atualizacao', 'Categoria', 'Status', 'HTTP_Code', 
            'Tempo_MS', 'Verificado_Em'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            
            for portal in portais:
                # Garantir que todos os campos existam
                linha = {campo: portal.get(campo, '') for campo in campos}
                writer.writerow(linha)
        
        print(f"\n[Verificador] Resultados salvos em {csv_path}")
    
    def gerar_resumo(self, portais: list) -> dict:
        """
        Gera resumo da verificação
        """
        total = len(portais)
        online = len([p for p in portais if p.get('Status') == 'online'])
        offline = total - online
        
        # Por região
        por_uf = {}
        for p in portais:
            uf = p.get('UF', 'N/A')
            if uf not in por_uf:
                por_uf[uf] = {'total': 0, 'online': 0}
            por_uf[uf]['total'] += 1
            if p.get('Status') == 'online':
                por_uf[uf]['online'] += 1
        
        return {
            'total': total,
            'online': online,
            'offline': offline,
            'porcentagem_online': round(online / total * 100, 1) if total else 0,
            'por_uf': por_uf
        }


if __name__ == "__main__":
    print("=" * 80)
    print("VERIFICADOR DE PORTAIS - STATUS ONLINE/OFFLINE")
    print("=" * 80)
    
    verificador = VerificadorPortais(timeout=10, max_workers=3)
    
    # Verificar todos
    portais = verificador.verificar_todos()
    
    # Gerar resumo
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)
    resumo = verificador.gerar_resumo(portais)
    print(f"Total: {resumo['total']}")
    print(f"Online: {resumo['online']} ({resumo['porcentagem_online']}%)")
    print(f"Offline: {resumo['offline']}")
    print()
    
    # Por estado (top 10)
    print("Por Estado:")
    for uf, dados in sorted(resumo['por_uf'].items(), 
                           key=lambda x: x[1]['online'], reverse=True)[:10]:
        print(f"  {uf}: {dados['online']}/{dados['total']} online")
    
    # Salvar
    verificador.salvar_resultados(portais)
    
    print("=" * 80)
