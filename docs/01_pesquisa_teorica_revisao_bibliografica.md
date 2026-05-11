# 1. Pesquisa Teorica e Revisao Bibliografica

## 1.1 Objetivo da etapa

Consolidar a base tecnica, normativa e tecnologica necessaria para o desenvolvimento de um sistema web de geracao automatizada de memorial descritivo e planta baixa a partir de coordenadas georreferenciadas.

## 1.2 Fundamentos tecnicos

### Topografia e georreferenciamento de imoveis

- Conceitos de levantamento planimetrico e representacao de perimetros.
- Estruturacao de vertices, segmentos, azimutes, rumos, perimetro e area.
- Fechamento de poligono e controle de consistencia geometrica.

### Normas tecnicas e legais aplicaveis

- Diretrizes do INCRA para georreferenciamento de imoveis rurais, padrao de memorial e estrutura de informacoes tecnicas.
- Provimento CNJ no 65/2017 como base normativa para contexto registral extrajudicial e requisitos documentais de regularizacao.
- Padroes cartoriais para textualizacao de confrontacoes e identificacao do imovel.

### SIG e dados vetoriais

- Uso de conceitos de Sistema de Informacao Geografica (SIG) para tratamento de geometrias e metadados espaciais.
- Integracao com formatos vetoriais usados no fluxo tecnico: `DWG`, `DXF` e `shapefile`.
- Compatibilidade de entrada com arquivos tabulares (`CSV`, `TXT`) para operacionalizar importacao de campo/escritorio.

### Ferramentas e linguagens para aplicacoes web de geoprocessamento

- `Python` e `Django` para backend e servicos de processamento.
- `Leaflet` para visualizacao cartografica interativa no frontend web.
- `Shapely` e `GDAL` como referencias bibliograficas para processamento geoespacial e interoperabilidade de dados.
- No MVP atual, o parsing vetorial prioriza `pyshp` e a geracao CAD prioriza `ezdxf`, mantendo `Shapely/GDAL` como trilha de evolucao tecnica.

## 1.3 Sintese de contribuicao para o projeto

A revisao confirma que a automacao proposta e tecnicamente viavel e aderente ao contexto de engenharia e agrimensura, desde que o sistema mantenha:

- Rastreabilidade dos dados de entrada e dos artefatos gerados.
- Validacao geometrica minima (consistencia do perimetro e fechamento).
- Estrutura documental alinhada as diretrizes INCRA e ao contexto normativo do CNJ.
- Capacidade de exportacao para formatos aceitos no fluxo tecnico-operacional.

## 1.4 Referencias base da revisao

- BRASIL. Conselho Nacional de Justica. Provimento no 65, de 14 de dezembro de 2017.
- BRASIL. Instituto Nacional de Colonizacao e Reforma Agraria (INCRA). Normativos tecnicos vigentes para georreferenciamento de imoveis rurais.
- LONGLEY, P. et al. Geographic Information Systems and Science.
- BURROUGH, P.; MCDONNELL, R. Principles of Geographical Information Systems.
- Documentacao oficial: Django, Leaflet, Shapely e GDAL/OGR.
