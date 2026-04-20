# PLANO DE REESTRUTURAÇÃO — DADOS-PUBLICOS-BR

## FASE 2: NOVA ESTRUTURA

```
dados-publicos-br/
├── core/                          # MOTOR DE INVESTIGAÇÃO
│   ├── engine/
│   │   ├── motor_regras.py
│   │   ├── motor_regras_v2.py
│   │   └── __init__.py
│   ├── analysis/
│   │   ├── cruzador.py
│   │   ├── cerebro_digital.py
│   │   └── temporal.py
│   └── graph/
│       ├── graph_engine.py (consolidado de .sh)
│       └── __init__.py
│
├── data/                          # PIPELINE DE DADOS
│   ├── raw/
│   ├── processed/
│   ├── pipelines/
│   │   └── etl_sp.py (consolidado)
│   └── scrapers/
│       ├── __init__.py
│       ├── amostra_csv.py
│       ├── buscar_sp_datasets.py
│       ├── fortaleza_scraper.py
│       └── portal_discovery.py
│
├── api/                           # APIS (unificado)
│   ├── catalog/                   # API de catálogo
│   │   ├── __init__.py
│   │   ├── buscar.py
│   │   └── index.py
│   ├── investigation/             # API de investigação
│   │   ├── __init__.py
│   │   ├── cerebro.py
│   │   └── search.py
│   └── gateway.py                 # Roteador unificado
│
├── frontend/                      # INTERFACE (mantém)
│   ├── v1/
│   ├── v2/
│   └── dashboard/
│
├── experiments/                   # CÓDIGO EXPERIMENTAL
│   ├── v32/
│   ├── v33/
│   ├── v34/
│   ├── v37/
│   ├── v40/
│   ├── v41/
│   └── simulations/
│
├── legacy/                        # ARQUIVO (não apaga)
│   ├── api_search_simples.py
│   ├── api_search.py
│   └── old_scripts/
│
├── deploy/                        # CONFIGURAÇÕES
│   ├── railway/
│   ├── vercel/
│   └── render/
│
├── docs/                          # DOCUMENTAÇÃO
├── scripts/                       # UTILITÁRIOS
│   └── utils/
│
└── tests/                         # TESTES
    ├── unit/
    └── integration/
```

## REGRAS DE MIGRAÇÃO

1. **COPIAR**, nunca mover direto
2. Criar `__init__.py` em cada módulo
3. Manter imports funcionando (adapters se necessário)
4. Commit por etapa
5. Testar antes de apagar originais

## CHECKLIST

- [ ] Backup completo
- [ ] Criar estrutura core/
- [ ] Criar estrutura data/
- [ ] Criar estrutura api/ (unificado)
- [ ] Mover experiments/
- [ ] Mover legacy/
- [ ] Atualizar imports
- [ ] Testar catálogo
- [ ] Testar investigação
- [ ] Deploy seguro
