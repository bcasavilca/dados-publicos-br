# Plano B - Dados de Fortaleza

## 🚨 Situação: CKAN Indisponível

O portal de dados abertos de Fortaleza (`dados.fortaleza.ce.gov.br`) não está respondendo à API CKAN.

## 🔧 Alternativas

### Opção 1: Portal da Transparência (Scraping)
- **URL**: https://transparencia.fortaleza.ce.gov.br/
- **Abordagem**: Scraping de tabelas HTML
- **Complexidade**: Média (requer parsing de HTML)

### Opção 2: Dados.gov.br (Federal com filtro)
- Buscar datasets federais que incluam Fortaleza
- **URL**: https://dados.gov.br/busca?q=fortaleza

### Opção 3: Outro Município (Recomendado para teste)
Se Fortaleza não funcionar, alternativas com CKAN ativo:

| Cidade | Portal CKAN | Status |
|--------|-------------|--------|
| **Recife** | dados.recife.pe.gov.br | ? |
| **Salvador** | dados.salvador.ba.gov.br | ? |
| **São Paulo** | dados.prefeitura.sp.gov.br | Ativo |
| **Curitiba** | dados.curitiba.pr.gov.br | ? |
| **Belo Horizonte** | dados.pbh.gov.br | ? |

### Opção 4: Dados Simulados (Para validar baseline)
Usar distribuição realista baseada em literatura sobre contratos públicos.

## 🎯 Recomendação Imediata

**Testar São Paulo** - CKAN conhecido como estável:
```
https://dados.prefeitura.sp.gov.br/api/3/action/package_list
```

## 📊 Se nenhum funcionar

Vamos para **dados simulados realistas**:
- Baseados em distribuições reais de contratos públicos
- Permitir validar o motor baseline
- Substituir por dados reais quando disponível

## 🚀 Próximo Passo

Escolha uma opção:
1. Tentar scraping do portal de transparência
2. Testar outro município (São Paulo)
3. Usar dados simulados para validar baseline

Me confirme qual caminho seguir!
