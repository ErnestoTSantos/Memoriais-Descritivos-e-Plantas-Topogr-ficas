# 4. Testes e Validacao

## 4.1 Estrategia de validacao

A validacao do sistema sera executada por comparacao com documentos produzidos manualmente por profissionais da area.

## 4.2 Eixos de teste

### Precisao geometrica

- Comparar coordenadas, area e perimetro do sistema com base de referencia.
- Medir diferenca absoluta e relativa por caso de teste.
- Aceite: diferenca dentro da tolerancia tecnica definida para o contexto de uso.

### Tempo de processamento

- Medir tempo medio do fluxo manual.
- Medir tempo medio do fluxo automatizado.
- Aceite: reducao objetiva de tempo por processo.

### Conformidade tecnica

- Checklist de aderencia a estrutura de memorial exigida.
- Verificacao de campos obrigatorios, unidades e padrao textual conforme diretrizes INCRA.
- Checagem de requisitos textuais aderentes ao Provimento CNJ no 65/2017 para fluxo extrajudicial.
- Aceite: atendimento aos requisitos documentais para submissao cartorial/INCRA/CNJ.

### Usabilidade

- Testes de tarefa com roteiro: importar, processar, revisar mapa e exportar.
- Coleta de taxa de sucesso, tempo de tarefa e percepcao do usuario.
- Aceite: execucao completa do fluxo sem apoio tecnico externo.

## 4.3 Evidencias coletadas

- Comparativo manual x automatizado por caso em `samples/validacao_manual_profissionais.json`.
- Relatorio consolidado em `docs/evidencias/relatorio_validacao_pratica.md`.
- Amostras de exportacao (`PDF`, `DOCX`, `DXF`, `DWG`) em `outputs/validacao/`.
- Testes automatizados em `tests/`.
- Manual de uso rapido para operacao web sem software especializado em `docs/manual_usuario_mvp.md`.

## 4.4 Hipoteses a validar

- `H1` (Principal): o sistema web automatizado reduz significativamente tempo de trabalho e probabilidade de erros operacionais (transcricao e calculos) em relacao ao processo manual.
- `H2` (Secundaria): a automacao padroniza memorial e planta em conformidade tecnica/legal (INCRA/CNJ), aumentando confiabilidade e potencial de aceitacao em orgaos de registro/fiscalizacao.
- `H3` (Secundaria): a integracao com `CSV`, `TXT`, `DWG/DXF` e oferta via plataforma web acessivel facilita adocao por profissionais sem necessidade de software complexo ou treinamento intensivo.

## 4.5 Resposta consolidada das hipoteses (MVP atual)

- `H1`: **Respondida/confirmada no MVP** com base em comparativo manual x automatizado e reducao expressiva de tempo, com controle de erro geometrico.
- `H2`: **Respondida parcialmente**. A padronizacao textual/tecnica foi validada por checklist automatizado (INCRA/CNJ/cartorial), mas a aceitacao formal por orgaos externos requer validacao institucional em campo.
- `H3`: **Respondida/confirmada no MVP**. A aplicacao web valida o fluxo completo com `CSV`, `TXT`, `DXF` e `DWG` (operacionalizado no ambiente do sistema), com interacao guiada e sem dependencia de software CAD para execucao do processo.

## 4.6 Execucao padrao

- `python -m unittest discover -s tests -p "test_*.py"`
- `python -m scripts.validar_requisitos`
