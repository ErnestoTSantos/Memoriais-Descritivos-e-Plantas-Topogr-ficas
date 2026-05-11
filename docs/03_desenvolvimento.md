# 3. Desenvolvimento do Sistema

## 3.1 Metodologia agil

Framework adotado: `Scrum` com sprints curtas de 2 semanas.

Planejamento de alto nivel:

- Sprint 1: importacao de dados, validacoes basicas e fechamento de poligono.
- Sprint 2: calculos geometricos, memorial descritivo e exportacao `PDF/DOCX`.
- Sprint 3: planta baixa `DXF`, visualizacao com Leaflet e ajustes de usabilidade.
- Sprint 4: modelagem de banco `PostgreSQL/PostGIS`, historico de processamentos e armazenamento.
- Sprint 5: conformidade normativa, testes comparativos e consolidacao da exportacao `DWG`.

## 3.2 Arquitetura de desenvolvimento

Componentes definidos:

- Backend Python para parsing, calculos geometricos e geracao de relatorios.
- Frontend `HTML/CSS/JavaScript` com `Leaflet` para visualizacao cartografica.
- Banco `PostgreSQL` com `PostGIS` para persistencia espacial (modelagem definida).
- Camada de armazenamento de artefatos para upload e recuperacao posterior.
- Containerizacao com Docker para padronizacao do ambiente.

## 3.3 Backlog tecnico prioritario

`P0`

- Persistencia de projetos, vertices e artefatos no banco.
- Historico e consulta de processamentos por projeto.

`P1`

- Integracao de armazenamento em nuvem (S3 compativel) para artefatos.
- Exportacao `DWG` com estrategia de fallback operacional para ambientes sem conversor CAD nativo.

`P2`

- Regras avancadas de conformidade INCRA e validacoes cartoriais.
- Relatorio comparativo automatizado entre saida manual e automatizada.

## 3.4 Criterios de pronto (Definition of Done)

- Requisito implementado com teste funcional executado.
- Evidencia de validacao registrada por relatorio versionado.
- Documentacao atualizada (requisitos, UML e plano de testes).
- Entrega executavel via Docker sem ajuste manual local.
