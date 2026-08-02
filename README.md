# PET Clima Araraquara

Mapa didático para explorar a exposição térmica no entorno das unidades de saúde de Araraquara e transformar o ranking em hipóteses de ação pública.

## O que mudou

- `index.html` e `mapa_interativo_araraquara.html` agora usam o mesmo app e carregam os dados externos em tempo de execução.
- O recorte padrão é a rede pública municipal. Hospitais privados, filantrópicos e unidades estaduais/universitárias podem ser comparados separadamente.
- O catálogo principal passou a ter 55 registros: 41 analisados + 14 candidatas a validar. As candidatas têm `record_status: "pendente_validacao"`, não possuem coordenadas artificiais e não entram no ranking.
- O ranking continua sendo calculado apenas a partir de `data/unidades_saude_analise_araraquara.geojson` e `data/ranking_risco_termico.csv`.
- A interface mostra fontes públicas para validar CNES, endereço, gestão, população, vegetação e alertas de calor.

## Arquivos de dados

```text
data/
├── unidades_saude_araraquara.json              # catálogo humano: 41 analisadas + 14 pendentes
├── unidades_sugeridas_araraquara.json          # backlog de validação das 14 candidatas
├── metadata_unidades_saude_araraquara.json     # escopo da rede e qualidade do cadastro atual
├── unidades_saude_araraquara.geojson            # 41 pontos com coordenadas usados na análise
├── unidades_saude_analise_araraquara.geojson   # 41 pontos com IECS e métricas do entorno
├── ranking_risco_termico.csv                   # ranking tabular atual
├── resumo_estatistico.json                      # métricas agregadas atuais
└── fontes_publicas_saude_araraquara.json       # referências para atualização do cadastro
```

## Como executar

Requer Python 3.10+ e um navegador moderno.

```bash
pip install -r requirements.txt
python -m http.server 8000
```

Acesse `http://localhost:8000`.

Para recalcular o ranking depois de adicionar unidades validadas ao GeoJSON:

```bash
python scripts/spatial_analysis.py
python scripts/generate_charts.py
python scripts/enrich_health_catalog.py
```

O catálogo pode ser enriquecido novamente sem alterar o GeoJSON analisado:

```bash
python scripts/enrich_health_catalog.py
```

## Interpretação responsável

O círculo de 300 m é um buffer geométrico ao redor do ponto, não uma distância de caminhada. A temperatura exibida é temperatura de superfície, não temperatura do ar. O IECS é relativo ao conjunto analisado; ao incluir novos pontos é necessário recalcular todas as unidades para manter a comparação coerente.

As 14 candidatas foram documentadas para orientar a validação, mas permanecem fora do ranking até que o CNES, o endereço e a coordenada sejam confirmados. A lista inclui a UPA Central, a base do SAMU, unidades básicas, serviços de saúde mental e atenção especializada.

## Próximas evoluções recomendadas

1. Incorporar os campos `CNES`, natureza jurídica, gestão e situação cadastral a partir do CNES.
2. Cruzar população, domicílios, idosos e crianças por setor censitário do IBGE.
3. Acrescentar um modo operacional com previsão e alertas do INMET para ondas de calor e baixa umidade.
4. Atualizar a camada de vegetação com séries do MapBiomas e documentar a versão do UrbVerde utilizada.
5. Validar os pontos rurais de Bela Vista e Monte Alegre com uma área de influência adequada ao acesso real, em vez de assumir automaticamente 300 m.

## Verificações

```bash
python -m unittest discover -s tests -v
node --check js/app.js
```
