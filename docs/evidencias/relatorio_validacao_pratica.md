# Relatorio de Validacao Pratica

Gerado em: 2026-04-23 20:24:16

## Resultado consolidado

- Precisao geometrica: APROVADO
- Tempo de processamento: APROVADO
- Conformidade tecnica (INCRA/CNJ/cartorial): APROVADO
- Usabilidade do fluxo: APROVADO

## Comparativo manual x automatizado

- Tempo total manual (referencia): 2700.00 s
- Tempo total automatizado (medido): 1.8166 s
- Ganho de produtividade estimado: 99.93%

## Detalhamento por caso

| Caso | Precisao | Tempo | Conformidade | Usabilidade | Dif area | Dif perimetro | Dif fechamento | Ganho tempo |
|---|---|---|---|---|---:|---:|---:|---:|
| caso_retangulo_01 | OK | OK | OK | OK | 0.000000 | 0.000000 | 0.000000 | 99.96% |
| caso_triangulo_02 | OK | OK | OK | OK | 0.000000 | 0.000000 | 0.000000 | 99.90% |

## Metricas de usabilidade por tarefa

| Caso | Importacao (s) | Processamento (s) | Relatorio (s) | Exportacao (s) |
|---|---:|---:|---:|---:|
| caso_retangulo_01 | 0.0001 | 0.0001 | 0.0092 | 0.6647 |
| caso_triangulo_02 | 0.0000 | 0.0001 | 0.0073 | 1.1352 |

## Resposta das hipoteses

- `H1` (tempo + erros operacionais): CONFIRMADA.
- Evidencia: comparativo manual x automatizado com ganho de tempo e consistencia geometrica nos casos de teste.
- `H2` (padronizacao e conformidade INCRA/CNJ): PARCIALMENTE CONFIRMADA.
- Evidencia: checklist tecnico/documental aprovado no fluxo automatizado; validacao de aceitacao institucional externa permanece pendente.
- `H3` (integracao de formatos + adocao web): CONFIRMADA.
- Evidencia: fluxo web unico aprovado com importacao `CSV/TXT`, processamento assistido em mapa e exportacao `DXF/DWG`, sem dependencia de software CAD no uso da plataforma.

## Limites desta validacao

- A validacao foi executada em ambiente controlado com casos de referencia.
- Nao substitui homologacao cartorial/institucional formal em orgaos externos.
- A conformidade legal final continua dependente de analise institucional no contexto de cada orgao.
