# Manual de Uso Rapido (MVP)

## Objetivo

Executar o fluxo completo de geracao de memorial descritivo e planta baixa pelo navegador, sem necessidade de software CAD instalado no computador do usuario.

## Pre-requisitos

- Ambiente do projeto em execucao (`docker compose up --build`).
- Navegador web moderno.

## Passo a passo (fluxo principal)

1. Acesse `http://localhost:8000`.
2. Preencha os dados do imovel (nome, proprietario, municipio, UF, datum e sistema).
3. Selecione a modalidade de medicao:
   - `Ponto a ponto`: entrada por `Vertice, X, Y`;
   - `Irradiacao`: entrada por `Vertice, Azimute, Distancia` e informe `Estacao X/Y`.
4. Informe os dados por:
   - texto, ou
   - upload de arquivo (`CSV/TXT` para ambas as modalidades e `ZIP` com shapefile para ponto a ponto).
5. Clique em `Processar Poligono`.
6. Revise os resultados exibidos na tela:
   - area, perimetro e erro de fechamento;
   - geometria no mapa interativo;
   - memorial descritivo e tabela de segmentos.
7. Exporte os artefatos conforme necessidade:
   - `PDF` e `DOCX` (memorial);
   - `DXF` e `DWG` (planta).

## Resultado esperado

- Fluxo completo executado apenas pela interface web.
- Geracao de arquivos tecnicos sem etapa manual de calculo geometrico.
- Reducao de retrabalho de transcricao em comparacao ao processo manual.

## Observacao de escopo do MVP

No ambiente atual, a entrega `DWG` atende ao fluxo operacional da plataforma para intercambio de planta no processo do sistema.
