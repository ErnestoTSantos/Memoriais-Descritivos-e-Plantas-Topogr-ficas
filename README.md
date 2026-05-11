# GeoMemorial - TCC

Sistema web para automatizar a geração de memorial descritivo e planta baixa a partir de coordenadas georreferenciadas.

## Requisitos atendidos

- Backend em `Django (Python)` para parsing, processamento geométrico e geração de relatórios.
- Frontend em `HTML`, `CSS`, `JavaScript` e `Leaflet` para visualização do polígono.
- Fluxos de medicao `ponto a ponto` e `irradiacao` no mesmo pipeline de processamento.
- Banco `PostgreSQL` com extensão `PostGIS` para dados espaciais.
- Armazenamento em nuvem via `S3` (compatível), usando `MinIO` no ambiente local.
- Ambiente completo em containers Docker com serviços integrados.

## Arquitetura (Clean Code + Strategy)

- `app/services/processing.py`: serviço de aplicação com regras de processamento geométrico e geração de memorial.
- `app/services/strategies/parsing.py`: estratégias de parsing por tipo de entrada (`text`, `csv/txt`, `zip/shp`).
- `app/services/strategies/export.py`: estratégias de exportação por formato (`pdf`, `docx`, `dxf`, `dwg`).
- `core/views.py`: camada HTTP fina, responsável por orquestrar request/response e delegar regras para os serviços.
- `app/services/parsing.py`: wrappers compatíveis para manter contrato legado dos testes/scripts.

## Executar com Docker Compose

```bash
docker compose up --build
```

Serviços:

- Aplicação: `http://localhost:8000`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

Credenciais padrão (desenvolvimento):

- MinIO usuário: `minioadmin`
- MinIO senha: `minioadmin`

## Endpoints principais

- `POST /api/process`: processa coordenadas por texto/arquivo.
  - `ponto a ponto`: `CSV`, `TXT`, `ZIP` com `SHP`.
  - `irradiacao`: `CSV` ou `TXT` com `vertice, azimute, distancia` + coordenadas da estacao.
    - `azimute` aceita decimal ou `GMS` (ex.: `123°34'56"`).
- Segmentos retornam azimute em decimal (`azimuth_deg`) e em `GMS` (`azimuth_dms`).
- `POST /api/export/{format}`: exporta em `pdf`, `docx`, `dxf` e `dwg`.
- `GET /api/artifacts`: lista artefatos gerados e armazenados.

## Testes e validacao

Executar testes automatizados:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Executar validacao pratica (precisao, tempo, conformidade e usabilidade) e gerar relatorio:

```bash
python -m scripts.validar_requisitos
```

Saidas:

- Relatorio: `docs/evidencias/relatorio_validacao_pratica.md`
- Artefatos de validacao: `outputs/validacao/`

## Documentacao por etapa do TCC

- `docs/01_pesquisa_teorica_revisao_bibliografica.md`
- `docs/02_analise_requisitos_modelagem.md`
- `docs/03_desenvolvimento.md`
- `docs/04_testes_validacao.md`
- `docs/manual_usuario_mvp.md`
- `docs/matriz_aderencia_tcc.md`
- `docs/objetivos_metas.md`

## Observacao sobre exportacao DWG

- No MVP, `DXF` e gerado nativamente.
- A exportacao `DWG` e disponibilizada por fallback operacional (arquivo com conteudo CAD equivalente ao fluxo `DXF`) enquanto conversao DWG nativa nao for integrada.
- O fallback de `DWG` foi encapsulado em estratégia dedicada para permitir troca futura por conversão nativa sem alterar os endpoints.

## Estrutura do ambiente

- `web`: Django app.
- `db`: PostgreSQL + PostGIS.
- `minio`: armazenamento S3 compatível.
- `minio-init`: bootstrap automático do bucket `geomemorial`.
