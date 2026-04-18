#!/usr/bin/env python3
"""
Portal Discovery - Descobridor automático de portais de transparência
Mapeia órgãos públicos e descobre seus portais de dados/transparência
"""

import requests
import csv
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

@dataclass
class OrgaoPublico:
    """Representa um órgão público"""
    nome: str
    tipo: str  # prefeitura, governo_estadual, camara, tcm, etc.
    esfera: str  # municipal, estadual, federal
    uf: str
    municipio: Optional[str] = None
    populacao: Optional[int] = None
    
    # Portais descobertos
    portal_transparencia: Optional[str] = None
    dados_abertos: Optional[str] = None
    api: Optional[str] = None
    
    # Status
    status_transparencia: str = "nao_verificado"  # online, offline, nao_encontrado
    status_dados: str = "nao_verificado"
    
    # Metadados
    descoberto_em: Optional[str] = None
    ultima_verificacao: Optional[str] = None

class PortalDiscovery:
    """
    Descobre portais de transparência e dados abertos para órgãos públicos
    """
    
    # Padrões comuns de URL para diferentes tipos de órgãos
    PADROES = {
        'prefeitura': [
            "https://transparencia.{slug}.gov.br",
            "https://transparencia.{slug}.rn.gov.br",
            "https://{slug}.gov.br/transparencia",
            "https://{slug}.rn.gov.br/transparencia",
            "https://portaltransparencia.{slug}.gov.br",
            "https://dados.{slug}.gov.br",
            "https://{slug}.gov.br/dados-abertos",
            "https://transparencia.{slug}.leg.br",
        ],
        'camara': [
            "https://{slug}.leg.br/transparencia",
            "https://transparencia.{slug}.leg.br",
            "https://{slug}.camara.gov.br/transparencia",
        ],
        'governo_estadual': [
            "https://transparencia.{slug}.gov.br",
            "https://dados.{slug}.gov.br",
            "https://transparencia.{slug}.leg.br",
            "https://www.tcm.{slug}.gov.br",
            "https://tcm.{slug}.gov.br",
        ]
    }
    
    def __init__(self, timeout: int = 10, max_workers: int = 5):
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (DadosPublicosBR-Discovery/1.0)'
        })
        self.resultados = []
    
    def slugify(self, nome: str) -> str:
        """Converte nome em slug para URL"""
        # Remove acentos e caracteres especiais
        slug = nome.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')
    
    def verificar_url(self, url: str) -> Dict:
        """
        Verifica se URL existe e é um portal válido
        """
        resultado = {
            'url': url,
            'status': 'erro',
            'http_code': None,
            'tempo_ms': None,
            'titulo': None,
            'erro': None
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
                # Verificar se é realmente um portal de transparência
                conteudo = response.text.lower()
                palavras_chave = [
                    'transparência', 'transparencia', 'dados abertos',
                    'diárias', 'despesas', 'licitações', 'contratos',
                    'gastos', 'verbas', 'cotas', 'remuneração'
                ]
                
                if any(p in conteudo for p in palavras_chave):
                    resultado['status'] = 'online_valido'
                else:
                    resultado['status'] = 'online_invalido'
                    
                # Extrair título
                import re
                titulo_match = re.search(r'<title>([^&lt;]+)&lt;/title>', response.text, re.IGNORECASE)
                if titulo_match:
                    resultado['titulo'] = titulo_match.group(1).strip()
                    
            elif response.status_code in [301, 302, 307, 308]:
                resultado['status'] = 'redirect'
            else:
                resultado['status'] = f'http_{response.status_code}'
                
        except requests.exceptions.Timeout:
            resultado['status'] = 'timeout'
            resultado['erro'] = 'Timeout'
        except requests.exceptions.ConnectionError:
            resultado['status'] = 'connection_error'
            resultado['erro'] = 'Nao foi possivel conectar'
        except Exception as e:
            resultado['status'] = 'erro'
            resultado['erro'] = str(e)[:100]
        
        return resultado
    
    def descobrir_orgao(self, orgao: OrgaoPublico) -> OrgaoPublico:
        """
        Tenta descobrir portais para um órgão específico
        """
        orgao.descoberto_em = datetime.now().isoformat()
        
        # Gerar slug
        slug = self.slugify(orgao.nome)
        
        # Determinar padrões baseados no tipo
        padroes = self.PADROES.get(orgao.tipo, self.PADROES['prefeitura'])
        
        # URLs para testar
        urls_testar = []
        for padrao in padroes:
            url = padrao.format(slug=slug)
            urls_testar.append(url)
        
        # Adicionar variantes sem acentos
        urls_sem_acento = []
        for url in urls_testar:
            # Remover acentos do slug
            url_sem_acento = url.replace('á', 'a').replace('ã', 'a').replace('â', 'a')
            url_sem_acento = url_sem_acento.replace('é', 'e').replace('ê', 'e')
            url_sem_acento = url_sem_acento.replace('í', 'i').replace('ó', 'o')
            url_sem_acento = url_sem_acento.replace('õ', 'o').replace('ô', 'o')
            url_sem_acento = url_sem_acento.replace('ú', 'u').replace('ç', 'c')
            if url_sem_acento not in urls_testar:
                urls_sem_acento.append(url_sem_acento)
        
        urls_testar.extend(urls_sem_acento)
        
        # Verificar cada URL
        for url in urls_testar:
            resultado = self.verificar_url(url)
            
            if resultado['status'] == 'online_valido':
                if 'transparencia' in url.lower() and not orgao.portal_transparencia:
                    orgao.portal_transparencia = url
                    orgao.status_transparencia = 'online'
                    
                elif 'dados' in url.lower() and not orgao.dados_abertos:
                    orgao.dados_abertos = url
                    orgao.status_dados = 'online'
            
            # Delay para não sobrecarregar
            time.sleep(0.5)
        
        orgao.ultima_verificacao = datetime.now().isoformat()
        return orgao
    
    def carregar_base_nordeste(self) -> List[OrgaoPublico]:
        """
        Carrega base inicial: estados, capitais e principais municípios
        """
        orgaos = []
        
        # Estados
        estados = [
            ('Ceará', 'CE'), ('Rio Grande do Norte', 'RN'), ('Paraíba', 'PB'),
            ('Pernambuco', 'PE'), ('Bahia', 'BA'), ('Sergipe', 'SE'),
            ('Maranhão', 'MA'), ('Piauí', 'PI'), ('Alagoas', 'AL')
        ]
        
        for nome, uf in estados:
            orgaos.append(OrgaoPublico(
                nome=f"Governo do {nome}",
                tipo='governo_estadual',
                esfera='estadual',
                uf=uf
            ))
        
        # Capitais
        capitais = [
            ('Fortaleza', 'CE'), ('Natal', 'RN'), ('João Pessoa', 'PB'),
            ('Recife', 'PE'), ('Salvador', 'BA'), ('Aracaju', 'SE'),
            ('São Luís', 'MA'), ('Teresina', 'PI'), ('Maceió', 'AL')
        ]
        
        for nome, uf in capitais:
            # Prefeitura
            orgaos.append(OrgaoPublico(
                nome=f"Prefeitura de {nome}",
                tipo='prefeitura',
                esfera='municipal',
                uf=uf,
                municipio=nome
            ))
            # Câmara
            orgaos.append(OrgaoPublico(
                nome=f"Câmara Municipal de {nome}",
                tipo='camara',
                esfera='municipal',
                uf=uf,
                municipio=nome
            ))
        
        return orgaos
    
    def executar_busca(self, orgaos: List[OrgaoPublico] = None) -> List[OrgaoPublico]:
        """
        Executa descoberta para todos os órgãos
        """
        if orgaos is None:
            orgaos = self.carregar_base_nordeste()
        
        print(f"[Discovery] Iniciando busca para {len(orgaos)} órgãos...")
        print(f"[Discovery] Timeout: {self.timeout}s | Workers: {self.max_workers}")
        
        resultados = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.descobrir_orgao, orgao): orgao for orgao in orgaos}
            
            for future in as_completed(futures):
                orgao = futures[future]
                try:
                    resultado = future.result()
                    resultados.append(resultado)
                    
                    status_t = "OK" if resultado.portal_transparencia else "--"
                    status_d = "OK" if resultado.dados_abertos else "--"
                    
                    print(f"  {resultado.nome[:40]:40} | T:{status_t} D:{status_d}")
                    
                except Exception as e:
                    print(f"  Erro em {orgao.nome}: {e}")
        
        self.resultados = resultados
        return resultados
    
    def exportar_csv(self, filename: str = 'data/portais_descobertos.csv'):
        """Exporta resultados para CSV"""
        if not self.resultados:
            print("[Discovery] Nenhum resultado para exportar")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'nome', 'tipo', 'esfera', 'uf', 'municipio',
                'portal_transparencia', 'dados_abertos', 'api',
                'status_transparencia', 'status_dados',
                'descoberto_em'
            ])
            
            for orgao in self.resultados:
                writer.writerow([
                    orgao.nome, orgao.tipo, orgao.esfera, orgao.uf, orgao.municipio,
                    orgao.portal_transparencia, orgao.dados_abertos, orgao.api,
                    orgao.status_transparencia, orgao.status_dados,
                    orgao.descoberto_em
                ])
        
        print(f"[Discovery] Exportados {len(self.resultados)} resultados para {filename}")
    
    def gerar_resumo(self) -> Dict:
        """Gera resumo da descoberta"""
        total = len(self.resultados)
        com_transparencia = len([o for o in self.resultados if o.portal_transparencia])
        com_dados = len([o for o in self.resultados if o.dados_abertos])
        
        return {
            'total_orgaos': total,
            'com_transparencia': com_transparencia,
            'com_dados_abertos': com_dados,
            'porcentagem_transparencia': round(com_transparencia / total * 100, 1) if total else 0,
            'porcentagem_dados': round(com_dados / total * 100, 1) if total else 0
        }


if __name__ == "__main__":
    print("=" * 80)
    print("PORTAL DISCOVERY - MAPEADOR DE TRANSPARÊNCIA PÚBLICA")
    print("=" * 80)
    
    discovery = PortalDiscovery(timeout=10, max_workers=3)
    
    # Carregar base
    orgaos = discovery.carregar_base_nordeste()
    print(f"\n[Base] Carregados {len(orgaos)} órgãos do Nordeste")
    
    # Executar descoberta
    print("\n[Discovery] Iniciando descoberta de portais...")
    resultados = discovery.executar_busca(orgaos)
    
    # Gerar resumo
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)
    resumo = discovery.gerar_resumo()
    print(f"Total de órgãos: {resumo['total_orgaos']}")
    print(f"Com transparência: {resumo['com_transparencia']} ({resumo['porcentagem_transparencia']}%)")
    print(f"Com dados abertos: {resumo['com_dados_abertos']} ({resumo['porcentagem_dados']}%)")
    
    # Exportar
    discovery.exportar_csv()
    
    print("=" * 80)
