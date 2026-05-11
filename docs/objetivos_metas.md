# Objetivos e Metas

## Objetivo geral

Desenvolver um sistema web capaz de automatizar a geracao de memoriais descritivos e plantas baixas a partir de coordenadas georreferenciadas.

## Objetivos especificos (metas)

| Meta | Status no MVP | Encaminhamento |
|---|---|---|
| Importar arquivos `CSV`, `TXT` e shapefile | Atendido | Manter cobertura com testes de regressao |
| Processar e identificar limites do poligono | Atendido | Evoluir validacoes topologicas |
| Gerar memorial padronizado (cartorio/INCRA) | Atendido | Manter checklist de conformidade tecnica nos testes |
| Exportar relatorios em `PDF/Word` | Atendido | Padronizar templates por comarca |
| Exportar plantas em `DWG/DXF` | Parcial no MVP (`DXF` nativo + `DWG` por fallback) | Evoluir para conversao CAD nativa quando necessario |
| Armazenamento em nuvem e consultas posteriores | Atendido | Monitorar retencao e politica de acesso dos artefatos |

## Indicadores de resultado

- Tempo medio por processo (manual x automatizado).
- Taxa de retrabalho por erro de digitacao/formatacao.
- Percentual de processos aprovados sem ajuste de forma.
- Tempo de resposta da aplicacao para processamento e exportacao.
