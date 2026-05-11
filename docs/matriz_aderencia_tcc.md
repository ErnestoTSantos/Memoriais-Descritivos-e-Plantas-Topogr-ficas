# Matriz de Aderência ao TCC

Data da revisão: 23/04/2026.

## Situação geral

| Item | Situação anterior | Ajuste aplicado | Situação atual |
|---|---|---|---|
| Pesquisa teorica e revisao bibliografica | Nao formalizado em artefato dedicado | Documento de revisao bibliografica consolidado com base tecnica e normativa | Atendido |
| Entrada CSV/TXT/Shapefile | Atendido | Requisito formalizado em documentação de requisitos | Atendido |
| Processamento e fechamento do polígono | Atendido | Critérios técnicos e regras de validação documentados | Atendido |
| Geração de memorial e planta baixa | Atendido | Fluxo funcional detalhado em UML | Atendido |
| Exportação PDF/DOCX/DWG/DXF | Parcial (PDF/DOCX/DXF) | Fluxo de exportacao completo com fallback DWG documentado e validado por script | Parcial no MVP (DWG via fallback) |
| Modelagem conceitual e lógica de banco | Não atendido | Modelo conceitual/lógico definido em documento técnico | Atendido em modelagem |
| Diagramas UML (casos de uso e atividades) | Não atendido | Diagramas Mermaid adicionados em `docs/uml` | Atendido |
| Metodologia ágil (Scrum) | Parcial | Plano de sprints e critérios de aceite definidos | Atendido em planejamento |
| Ambiente Docker integrado | Parcial (app isolado) | Stack integrada em `docker-compose` com web, PostGIS e S3 compativel (MinIO) | Atendido |
| Validação (precisão, tempo, conformidade, usabilidade) | Não atendido formalmente | Script de validacao pratica + testes automatizados + relatorio de evidencias | Atendido |
| Armazenamento em nuvem e consultas posteriores | Não atendido | Upload/listagem de artefatos via `default_storage` com S3 compativel e endpoint de consulta | Atendido |

## Observações de escopo

- O repositorio mantem o MVP funcional com requisitos tecnicos obrigatorios implementados.
- O requisito de `DWG` permanece com fallback operacional (conteudo DXF com extensao DWG) enquanto conversao CAD nativa nao e integrada.
- A validacao pratica passou a ter execucao repetivel com evidencias em artefatos versionados.
- O legado FastAPI foi removido para reduzir manutencao e manter arquitetura unica em Django.
