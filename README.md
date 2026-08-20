# PET Saúde - Clima Araraquara

Mapa didático do PET Saúde - Clima para explorar a exposição térmica e a proximidade de pontos de risco hidrológico no entorno das unidades de saúde de Araraquara.

## O que o site mostra

- Mapa atual: camada térmica local de 2024, áreas verdes, unidades de saúde, buffers de 300 m e pontos municipais de alagamento, inundação e enxurrada.
- Camadas adicionais opcionais: ilhas de calor UrbVerde 2021 e cicatrizes de fogo anuais do MapBiomas Fogo Coleção 5 (2025), sem participação no IECS.
- Histórico: série anual de 2016 a 2021 da temperatura máxima da superfície por setor da UrbVerde, agregada para cada unidade e para a média da rede.
- Catálogo: 52 unidades analisadas e 2 registros pendentes de validação. O CMS Santa Angelina “Rafael Sorbo” está no mapa como `SUS-042`, com CNES `2063247`.
- Nesta rodada, foram confirmadas e incorporadas a UPA Central, seis unidades básicas, o Espaço Crescer, o CAPS-AD, o CEO e o Centro Municipal de Referência do Autismo. O antigo registro da USF Jardim São Bento foi reconciliado com o `SUS-007`, evitando duplicidade.
- Comparação: o modal “Histórico” combina uma série temporal, comparação entre unidades e proximidade aproximada a pontos hidrológicos mapeados.
- Base de consulta: o modal “Dados de saúde” permite explorar dez anos completos (2016–2025) do SIH/SUS por estabelecimento executante e capítulo CID-10, além da produção ambulatorial SIA/SUS por grupo de procedimento.
- Análise: a base apresenta tendência anual, evolução dos cinco principais capítulos/grupos, concentração por estabelecimento ou grupo e composição do ano selecionado.
- Exportação: os filtros atuais podem ser baixados em CSV ou em XLSX. A planilha XLSX inclui abas de resumo, série anual, detalhamento do ano, perfil de cuidado e notas metodológicas.

Risco térmico e risco hidrológico aparecem lado a lado, mas não são somados automaticamente: são medidas diferentes, com fontes e escalas distintas. A camada “Vegetação” usa a grade UrbVerde 2024 como proxy NDVI observado; ela não representa o limite cadastral de parques ou áreas verdes. A antiga camada de polígonos sem fonte verificável não é carregada pela aplicação.

### Vulnerabilidade social no IECS

A dimensão social participa do cálculo atual com peso de 30%. Ela foi substituída por um índice social-sanitário composto com dados agregados do Censo 2022 do IBGE, calculado por setor censitário e ponderado no buffer de 300 m de cada unidade. A composição usada é: renda mediana inversa (50%), proporção de crianças (20%), proporção de pessoas idosas (20%) e média de moradores por domicílio (10%). Esse valor não é um índice oficial do IBGE; é uma ferramenta analítica do projeto, que deve ser discutida e calibrada pelo grupo antes de orientar uma decisão definitiva.

## Dados

```text
data/
├── unidades_saude_araraquara.json              # catálogo: 52 analisadas + 2 pendentes
├── unidades_sugeridas_araraquara.json          # backlog de validação das 2 pendências
├── unidades_saude_araraquara.geojson            # 52 pontos usados na análise espacial
├── unidades_saude_analise_araraquara.geojson   # 52 pontos com IECS e métricas de 2024
├── ranking_risco_termico.csv                   # ranking térmico atual
├── censo_2022_vulnerabilidade_araraquara.geojson # setores e índice social-sanitário composto
├── sensibilidade_iecs_araraquara.json           # cenários alternativos de pesos do IECS
├── desfechos_saude_araraquara.json              # SIH/SUS agregado por mês e município de residência
├── dados_historicos_saude_araraquara.json       # SIH/SUS e SIA/SUS, 2016–2025, para consulta no site
├── historico_risco_termico_araraquara.json     # UrbVerde 2016–2021 por unidade
├── pontos_risco_hidrologico_araraquara.geojson  # 23 pontos da Defesa Civil municipal
├── urbverde_araraquara.geojson                  # camada térmica local usada no mapa atual
├── urbverde_ilhas_calor_2021_araraquara.geojson  # camada adicional UrbVerde 2021
├── mapbiomas_fogo_araraquara_2025.geojson        # cicatrizes anuais MapBiomas Fogo
├── areas_verdes_araraquara.geojson              # legado sem fonte verificável; não carregado pela aplicação
└── fontes_publicas_saude_araraquara.json       # fontes e usos de cada cruzamento
```

### Nota sobre a UrbVerde

A plataforma disponibiliza o indicador `rinunda` — risco climático a inundações — por setor censitário em 2024. A camada foi conferida durante esta atualização, mas seus tiles públicos não retornaram setores para Araraquara. Para não transformar ausência de dado em “baixo risco”, o site usa os 23 pontos locais publicados pela Prefeitura/Defesa Civil e sinaliza que 20 possuem posição aproximada no mapa.

## Como executar

Requer Python 3.10+ e um navegador moderno.

```bash
pip install -r requirements.txt
python -m http.server 8000
```

Acesse `http://localhost:8000`.

Para atualizar os dados derivados depois de validar novas unidades:

```bash
python scripts/promote_confirmed_units.py
python scripts/build_census_social.py --cache-dir C:/Temp/pet-clima-ibge
python scripts/spatial_analysis.py
python scripts/fetch_health_outcomes.py --cache-dir C:/Temp/pet-clima-datasus-sih
python scripts/fetch_tabnet_saude.py
python scripts/enrich_health_catalog.py
python scripts/build_historical_risk.py
python scripts/build_hydrology_points.py
python scripts/sync_index.py
```

## Interpretação responsável

O círculo de 300 m é um buffer geométrico, não uma distância de caminhada. A temperatura é de superfície, não do ar. O IECS é relativo ao conjunto analisado e deve ser recalculado quando unidades entrarem ou saírem do recorte. O componente social usa `census_population`, `census_income_median`, `census_share_children`, `census_share_elderly`, `census_crowding` e `vulnerability_score_5` do Censo 2022. O componente social do Censo é um índice composto deste projeto, não um indicador oficial do IBGE.

A janela “Fontes” mostra a auditoria do catálogo: correspondência entre geometria e coordenada, endereço e CNES informados, cobertura UrbVerde, cobertura do Censo e registros marcados para revisão. Duas unidades rurais têm coordenadas confirmadas no mapa oficial da Secretaria Municipal de Saúde, mas ficam fora da grade UrbVerde 2024 publicada; seus valores climáticos usam fallback técnico e aparecem sinalizadas na ficha.

O bloco de saúde usa a base histórica `dados_historicos_saude_araraquara.json`, extraída do TABNET/DATASUS para dez anos completos (2016–2025). No SIH/SUS, o recorte é por município de residência: a tabela por unidade mostra o estabelecimento executante, que pode estar em outro município quando o residente foi internado fora de Araraquara. Ela não descreve o itinerário completo do usuário na APS, regulação, transporte ou acesso especializado, não prova causalidade, não representa atendimentos privados e não inclui dados identificáveis.

A produção ambulatorial do SIA/SUS permanece separada porque `Qtd.aprovada` é uma quantidade de produção, não número de pessoas ou internações. Nesta extração pública, ela está disponível por grupo de procedimento, mas não por unidade executante na mesma tabulação; portanto, não é distribuída artificialmente pelas unidades do mapa. Os valores podem sofrer atualização retroativa no DATASUS, e o campo `generated_at` registra a data de cada coleta.

### Gráficos recomendados para o GAT 4

- **Tendência anual:** mostra crescimento, queda e quebras de série na demanda registrada; deve ser lida junto com mudanças de oferta, financiamento e registro.
- **Evolução do perfil de cuidado:** compara os capítulos CID-10 ou grupos de procedimento mais frequentes ao longo dos anos.
- **Concentração da rede:** evidencia dependência de poucos estabelecimentos e possíveis pontos críticos para referência, transporte e continuidade do cuidado.
- **Composição da produção:** ajuda a separar o volume ambulatorial por grupo de procedimento, sem confundir quantidade aprovada com número de pessoas.

Esses gráficos são descritivos. Eles ajudam a formular hipóteses sobre integralidade, acesso e rede, mas não demonstram sozinhos que um evento climático causou um desfecho de saúde.

Os pontos hidrológicos são registros municipais de locais de atenção. Não representam uma mancha contínua, profundidade de água ou probabilidade de inundação. As coordenadas aproximadas servem para orientação e triagem; decisões de obra devem usar a fonte técnica original e vistoria local.

## Fontes principais

- [UrbVerde](https://urbverde.iau.usp.br/) — séries térmicas e indicadores socioambientais.
- [Prefeitura / Defesa Civil: áreas de risco](https://www.araraquara.sp.gov.br/atualizacao-das-areas-de-risco-de-alagamento-inundacao-e-enxurrada-e-dados-sobre-incendios-e-queimadas-de-araraquara) — 23 pontos municipais.
- [CNES / DATASUS](https://dadosabertos.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude) — cadastro e gestão das unidades.
- [IBGE — Censo Demográfico 2022](https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html) — agregados por setor censitário e variáveis sociais usadas no índice composto.
- [Ministério da Saúde — SIH/SUS por residência](https://tabnet.datasus.gov.br/cgi/deftohtm.exe?sih/cnv/nrSP.def) — fonte da série municipal de internações agregadas de 2024.
- [Ministério da Saúde — SIA/SUS por grupo de procedimento](https://tabnet.datasus.gov.br/cgi/deftohtm.exe?SIA/CNV/QASP.DEF) — fonte da série ambulatorial agregada de 2016–2025.
- [SheetJS Community Edition — exportação XLSX](https://docs.sheetjs.com/docs/api/write-options/) — biblioteca fixada na versão 0.20.3 para gerar a planilha no navegador.
- [Ministério da Saúde — SIH/SIA e TABNET](https://www.gov.br/saude/pt-br/acesso-a-informacao/sic/dados-em-transparencia-ativa/saes) — documentação institucional para desfechos agregados e futura camada ambulatorial.
- [INMET — avisos meteorológicos](https://portal.inmet.gov.br/noticias/inmet-aprimora-interface-de-avisos-meteorol%C3%B3gicos) — referência para um modo operacional de alertas de calor, baixa umidade e chuva.
- [Prefeitura — Atenção Básica](https://webnetserver.com.br/araraquara/secretarias/saude/sobre-a-secretaria-saude/atencao-basica) e [mapa oficial das unidades](https://www.google.com/maps/d/viewer?hl=pt-BR&ll=-21.79175544415152%2C-48.1768535&mid=1z547XaGQ4BgR__QfAc0f3a1bM55Xja3v&z=12) — nomes, endereços e coordenadas das unidades básicas.
- [Prefeitura — Atenção Especializada](https://webnetserver.com.br/araraquara/secretarias/saude/sobre-a-secretaria-saude/atencao-especializada/atencao-especializada) — CAPS-AD, Espaço Crescer e Centro do Autismo.
- [Prefeitura — Atendimento Odontológico](https://webnetserver.com.br/araraquara/servicos/guia-de-servicos/saude/atendimento-odontologico) — CEO municipal.
- [CMS Santa Angelina no CNES](https://cnes2.datasus.gov.br/Mod_Ind_Especialidades_Listar.asp?VAmbu=&VAmbuSUS=&VClassificacao=&VComp=201702&VEstado=35&VHosp=&VHospSus=&VListar=1&VMun=350320&VServico=&VTerc=&VTipo=141) — confirmação do CNES `2063247`.

## Verificações

```bash
python -m unittest discover -s tests -v
node --check js/app.js
git diff --check
```
