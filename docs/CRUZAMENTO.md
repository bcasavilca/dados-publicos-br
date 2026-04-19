# 🎯 Cruzamento de Dados - Detecção de Padrões Suspeitos

## O que é?

Sistema que cruza dados de múltiplas fontes para detectar padrões suspeitos de corrupção.

## 🔗 Fontes Cruzadas

| Fonte | Dados | Uso |
|-------|-------|-----|
| **TSE** | Candidatos, doações, bens | Quem recebeu dinheiro? |
| **Compras.gov** | Licitações, contratos | Quem recebeu contratos? |
| **Receita Federal** | Empresas, sócios | Quem são os fornecedores? |
| **Transparência** | Gastos públicos | Onde o dinheiro foi gasto? |

## 🚨 Padrões Detectados

### 1. Concentração de Fornecedor
> Empresa X ganhou 40% dos contratos do órgão Y

### 2. Financiamento + Contrato
> Empresa que doou para campanha ganhou contrato depois

### 3. Valores Anômalos
> Contrato 10x acima da média para aquele tipo de serviço

### 4. Empresa de Fachada
> CNPJ ativo mas sem funcionários, recebendo milhões

## 🚀 Como Usar

### Analisar órgão:
```
GET /cruzamento/analisar?orgao=Fortaleza
```

### Analisar empresa:
```
GET /cruzamento/empresa?cnpj=00000000000191
```

## 📊 Exemplo de Retorno

```json
{
  "orgao_analisado": "Fortaleza",
  "total_alertas": 2,
  "alertas": [
    {
      "tipo": "concentracao_fornecedor",
      "descricao": "Empresa X ganhou 40% dos contratos",
      "gravidade": "alta"
    },
    {
      "tipo": "financiamento_politico",
      "descricao": "Dona da empresa X doou R$ 50k",
      "gravidade": "media"
    }
  ],
  "recomendacao": "Investigar relação entre empresa e candidato"
}
```

---

*Este é um protótipo. Dados reais exigiriam acesso às APIs oficiais.*
