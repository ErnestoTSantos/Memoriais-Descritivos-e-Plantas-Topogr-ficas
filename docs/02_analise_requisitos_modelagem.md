# 2. Analise de Requisitos e Modelagem do Sistema

## 2.1 Requisitos funcionais

`RF-01` Importar coordenadas por `CSV`, `TXT` e `ZIP` contendo shapefile.

`RF-02` Interpretar dados de coordenadas com mapeamento de colunas e validacao de tipos numericos.

`RF-03` Realizar fechamento automatico do poligono quando o ultimo vertice for diferente do primeiro.

`RF-04` Calcular area, perimetro, azimute, rumo e erro de fechamento.

`RF-05` Gerar memorial descritivo padronizado com dados do imovel, confrontacoes e metricas, alinhado a diretrizes INCRA e ao contexto do Provimento CNJ no 65/2017.

`RF-06` Gerar planta baixa vetorial para representacao cartografica do perimetro.

`RF-07` Exportar resultados em `PDF`, `DOCX` e `DXF`.

`RF-08` Disponibilizar exportacao `DWG` como meta de sprint com dependencia de ferramenta de conversao CAD.

`RF-09` Registrar metadados de processamento para consultas posteriores.

`RF-10` Disponibilizar visualizacao interativa do poligono no mapa.

`RF-11` Suportar as modalidades de medicao `ponto a ponto` e `irradiacao` no fluxo de processamento.

## 2.2 Requisitos nao funcionais

`RNF-01` Precisao geometrica: tolerancia de erro conforme regras de validacao tecnica do projeto.

`RNF-02` Desempenho: processamento de arquivos usuais em tempo inferior ao fluxo manual equivalente.

`RNF-03` Portabilidade: execucao por containers Docker.

`RNF-04` Manutenibilidade: separacao por camadas (parsing, geometria, relatorios, interface).

`RNF-05` Rastreabilidade: identificacao de entradas, parametros e artefatos gerados.

`RNF-06` Usabilidade: fluxo unico de importacao, processamento, visualizacao e exportacao.

`RNF-07` Conformidade: estrutura de memorial alinhada a padroes cartoriais, diretrizes INCRA e requisitos documentais do Provimento CNJ no 65/2017.

## 2.3 Estrutura de entrada de dados

- `CSV`: colunas reconhecidas para `X`, `Y` e identificador de vertice.
- `TXT`: linhas no formato `VERTICE, X, Y` ou `X, Y`.
- `TXT/CSV` irradiacao: linhas no formato `VERTICE, AZIMUTE, DISTANCIA` ou `AZIMUTE, DISTANCIA`, com estacao `X/Y` informada no projeto.
- `SHP`: upload em `ZIP` contendo ao menos `.shp`, `.shx` e `.dbf`.

## 2.4 Modelagem conceitual de dados

Entidades principais:

- `Projeto`: identificacao, responsavel, municipio, UF, datum, sistema de coordenadas, data de criacao.
- `Vertice`: codigo, coordenadas `X/Y`, ordem no poligono, vinculo ao projeto.
- `Processamento`: area, perimetro, erro de fechamento, timestamp, status.
- `Artefato`: tipo (`PDF`, `DOCX`, `DXF`, `DWG`), caminho/url, hash, data de geracao.

Relacionamentos:

- Um `Projeto` possui muitos `Vertices`.
- Um `Projeto` possui muitos `Processamentos`.
- Um `Processamento` possui muitos `Artefatos`.

## 2.5 Modelagem logica (PostgreSQL/PostGIS)

Tabelas propostas:

- `projects(id, property_name, owner_name, municipality, state, datum, coordinate_system, created_at)`
- `vertices(id, project_id, vertex_code, x_coord, y_coord, seq, geom geometry(Point, 31983))`
- `process_runs(id, project_id, area_m2, perimeter_m, closure_error_m, executed_at, status)`
- `artifacts(id, process_run_id, format, storage_key, mime_type, checksum, created_at)`

Indices sugeridos:

- `idx_vertices_project_seq` em `(project_id, seq)`.
- `idx_vertices_geom` tipo `GIST` em `geom`.
- `idx_artifacts_process_run` em `(process_run_id)`.

## 2.6 Fluxos UML

Os fluxos de interacao foram adicionados em:

- `docs/uml/use_case.mmd`
- `docs/uml/activity_processamento.mmd`

Os diagramas cobrem casos de uso e atividade do fluxo principal de importacao, processamento e exportacao.
