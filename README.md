# Análise de Preços de Habitação em Portugal

Dashboard interativo com dados **reais e oficiais do INE** (Instituto
Nacional de Estatística) sobre o mercado de habitação em Portugal:

- **Vendas de alojamentos familiares (€/m²)**, por concelho e por região
  (NUTS I/II/III), desde 2022 — inclui os 308 concelhos do país, por
  quartil de preço.
- **Rendas de novos contratos de arrendamento (€/m²/mês)**, com a mesma
  desagregação geográfica e por quartil — a série que o INE suspendeu entre
  outubro de 2025 e junho de 2026 e voltou a publicar com metodologia
  revista.
- **Índice de Preços da Habitação** (vendas), nacional, trimestral, desde
  2009 — mostra a evolução do mercado ao longo de mais de 15 anos (incluindo
  a crise da dívida de 2011-2013 e a subida acentuada desde 2015).
- **Mapa de Portugal por concelho**, com os 308 concelhos coloridos por
  preço/renda, para o ano/quartil selecionado.

Nenhum dos conjuntos de dados é simulado — vêm diretamente da
[API pública do INE](https://www.ine.pt/xurl/indx/0013042/PT), sem
necessidade de chave de acesso.

Projeto de portefólio de [Elisama Manuel](https://elisamanuel-on.github.io/portfolio.html).

## Porque existe

Mostra, de forma visual e interativa, como os preços de venda e as rendas
da habitação variam muito entre regiões de Portugal (de ~245 €/m² em
Sernancelhe a quase 4900 €/m² em Lisboa, no caso das vendas) e como
evoluíram ao longo do tempo a nível nacional.

Anúncios individuais de venda/arrendamento (como os de portais como
Idealista ou Imovirtual) ficaram fora do projeto: nenhum destes sites tem
uma API pública de acesso imediato e gratuito — a da Idealista exige um
pedido aprovado ao negócio, sem garantia de resposta nem de ser gratuita, e
as restantes não têm API pública (o mesmo tipo de bloqueio encontrado no
projeto [Monitor de Vagas & Notícias](https://github.com/elisamanuel-on/monitor-vagas-noticias)
ao tentar o Net-Empregos). Em vez disso, optámos pelos dados oficiais e
gratuitos do próprio INE, que cobrem o mesmo tipo de informação (valores
reais de mercado) de forma agregada por região.

## Arquitetura

```
app.py                          # a app Dash (interface + gráficos + mapa)
assets/style.css                # estilos (Dash carrega automaticamente)
dados/
  mapa_geografico.csv           # geocod -> região/nível (estático, do INE)
  precos_regionais.csv          # €/m² (venda) por concelho/região, 2022-2025
  rendas_regionais.csv          # €/m²/mês (arrendamento) por concelho/região, 2022-2025
  indice_nacional.csv           # índice nacional de vendas, trimestral, desde 2009
  concelhos.geojson             # fronteiras dos 308 concelhos (fonte: E-REDES/OpenDataSoft)
  concelhos_geojson_crosswalk.csv  # geocod do INE -> código do concelho no geojson
scripts/
  atualizar_dados.py            # vai buscar dados novos à API do INE
tests/                          # testes com respostas simuladas + testes de qualidade dos dados
.github/workflows/
  atualizar_dados.yml           # atualiza os dados uma vez por mês (automático)
  tests.yml                     # corre os testes em cada push/PR
```

A app (`app.py`) só lê os CSVs em `dados/` — nunca faz pedidos à internet
enquanto está a correr. Isso torna-a rápida e não depende da disponibilidade
do site do INE a cada visita. Os dados são atualizados à parte, pelo robô
(`scripts/atualizar_dados.py`), que corre uma vez por mês via GitHub Actions
e só faz commit se algo tiver mudado.

## Fonte dos dados (API do INE)

Os três indicadores usados:

- [`0013042`](https://www.ine.pt/xurl/indx/0013042/PT) — Vendas de
  alojamentos familiares (Metodologia 2022 - €/m²), por localização
  geográfica e quartis, anual.
- [`0014711`](https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_indicadores&indOcorrCod=0014711&contexto=bd&selTab=tab2) —
  Rendas de novos contratos de arrendamento de alojamentos familiares
  (Metodologia 2026 - €/m²), por localização geográfica e quartis, anual.
- [`0009201`](https://www.ine.pt/xurl/indx/0009201/PT) — Índice de preços
  da habitação (Base - 2015), por categoria do alojamento, trimestral.

Não é preciso nenhuma chave de API — é um serviço público e gratuito do
INE. O mapa geográfico (`dados/mapa_geografico.csv`, que traduz os códigos
do INE para nomes de concelhos/regiões) é estável ao longo do tempo, por
isso fica gravado no repositório em vez de ser pedido em cada atualização.

O ficheiro `dados/concelhos.geojson` (fronteiras dos concelhos, para o
mapa) vem do dataset público
["Municipalities - Portugal" da E-REDES](https://e-redes.opendatasoft.com/explore/dataset/municipalities-portugal/)
(licença aberta, via OpenDataSoft) — é estático como o mapa geográfico, por
isso também fica gravado no repositório. Como os nomes de concelhos nesse
dataset nem sempre coincidem exatamente com os do INE (ex: dois concelhos
diferentes chamados "Calheta", um nos Açores e outro na Madeira),
`dados/concelhos_geojson_crosswalk.csv` faz a ligação entre os códigos dos
dois, um por um, confirmada manualmente para os 308 concelhos.

## Correr localmente

```bash
pip install -r requirements-dev.txt

# (opcional) ir buscar os dados mais recentes do INE
python -m scripts.atualizar_dados

# arrancar o dashboard
python app.py
# abre http://localhost:8050
```

## Testes

```bash
pytest -v
```

Há dois tipos de testes: os do robô de atualização (`test_atualizar_dados.py`,
com respostas simuladas da API do INE — não fazem pedidos reais) e os de
qualidade dos dados (`test_dados.py`, que confirmam que os CSVs e o
`concelhos.geojson` gravados no repositório continuam com a forma que a app
espera, incluindo que todos os 308 concelhos têm correspondência entre o
INE e o geojson do mapa).

## Deployment

- **Dashboard**: `render.yaml` configura o deploy no [Render](https://render.com)
  (plano gratuito), a correr a cada push para `main`.
- **Atualização dos dados**: `.github/workflows/atualizar_dados.yml` corre
  automaticamente no dia 1 de cada mês (os dados do INE são trimestrais ou
  anuais, por isso não faz sentido correr com mais frequência), e também
  pode ser corrido manualmente a partir do separador "Actions" do
  repositório ("Run workflow"). Quando há dados novos, o robô faz commit
  automático — isso dispara um novo deploy no Render.

## Notas de design

- **Sem base de dados** — os dados cabem confortavelmente em CSVs
  (poucas centenas de KB), por isso não há necessidade de MongoDB ou
  semelhante; os ficheiros vivem no próprio repositório.
- **A app nunca depende do INE estar disponível**: lê sempre os CSVs
  locais. Só o robô de atualização (que corre à parte, uma vez por mês)
  fala com a API do INE.
- **Dados reais desde o primeiro dia**: nenhuma parte da app usa dados de
  exemplo — os CSVs em `dados/` vêm diretamente da API oficial do INE.
- **Mapa sem chave de API**: o mapa usa `go.Choroplethmap` (baseado em
  MapLibre) com `map_style="carto-positron"`, um dos estilos de mapa base do
  Plotly que não precisa de token do Mapbox.
- **Download dos dados filtrados**: o botão "Descarregar CSV" exporta
  exatamente os dados por trás do gráfico de comparação atual (tipo, nível,
  ano e quartil selecionados), não o ficheiro completo.
