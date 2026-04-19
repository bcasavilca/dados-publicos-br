# 📍 Fontes de Dados Reais - Fortaleza

## Portal Oficial
- **URL**: https://transparencia.fortaleza.ce.gov.br/
- **Tipo**: Portal de transparência completo
- **Dados**: Despesas, receitas, contratos, licitações

## CKAN/Dados Abertos
- **URL**: http://dados.fortaleza.ce.gov.br/
- **API**: `http://dados.fortaleza.ce.gov.br/api/3/action/`
- **Formato**: JSON/CSV via API

## Endpoints CKAN Úteis

### Listar datasets
```
GET http://dados.fortaleza.ce.gov.br/api/3/action/package_list
```

### Buscar despesas
```
GET http://dados.fortaleza.ce.gov.br/api/3/action/package_search?q=despesa
```

### Dataset específico (exemplo)
```
GET http://dados.fortaleza.ce.gov.br/api/3/action/package_show?id=despesas-2024
```

## 📊 Dados Disponíveis (tipicamente)

| Categoria | Formato | Frequência |
|-----------|---------|------------|
| Despesas | CSV/JSON | Mensal |
| Receitas | CSV/JSON | Mensal |
| Contratos | CSV/JSON | Atualização variável |
| Licitações | CSV/JSON | Evento a evento |
| Folha de pagamento | CSV/JSON | Mensal |

## 🔧 Script de Exemplo

```python
import requests

# Buscar datasets de despesas
url = "http://dados.fortaleza.ce.gov.br/api/3/action/package_search"
params = {"q": "despesa", "rows": 10}

resp = requests.get(url, params=params)
data = resp.json()

# Extrair URLs de download
for result in data.get('result', {}).get('results', []):
    print(f"Dataset: {result['title']}")
    for resource in result.get('resources', []):
        print(f"  Download: {resource['url']}")
```

## ⚠️ Observações

1. **API pode ter rate limit** - usar delays entre requests
2. **Dados podem estar desatualizados** - verificar data da última atualização
3. **Formato CSV pode variar** - normalização necessária
4. **Colunas podem mudar** - validação de schema

## 📞 Alternativa: Dados.gov.br

Se CKAN de Fortaleza não funcionar:
```
https://dados.gov.br/api/3/action/package_search?q=fortaleza
```

## 🎯 Próximo Passo

1. Testar CKAN de Fortaleza
2. Identificar datasets de despesas/contratos
3. Baixar 12 meses de dados
4. Normalizar para formato do baseline
