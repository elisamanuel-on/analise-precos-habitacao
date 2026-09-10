# Análise de Preços de Habitação em Portugal

Dashboard interativo com dados **reais e oficiais do INE** (Instituto
Nacional de Estatística) sobre o mercado de habitação em Portugal:

- **Vendas de alojamentos familiares (€/m²)**, por concelho e por região
  (NUTS I/II/III), desde 2022 — inclui os 308 concelhos do país, por
  quartil de preço.
- **Índice de Preços da Habitação**, nacional, trimestral, desde 2009 —
  mostra a evolução do mercado ao longo de mais de 15 anos (incluindo a
  crise da dívida de 2011-2013 e a subida acentuada desde 2015).

Nenhum dos dois conjuntos de dados é simulado — vêm diretamente da
[API pública do INE](https://www.ine.pt/xurl/indx/0013042/PT), sem
necessidade de chave de acesso.

Projeto de portefólio de [Elisama Manuel](https://elisamanuel-on.github.io/portfolio.html).

## Porque existe

Mostra, de forma visual e interativa, como os preços da habitação variam
muito entre regiões de Portugal (de ~245 €/m² em Sernancelhe a quase
4900 €/m² em Lisboa) e como evoluíram ao longo do tempo a nível nacional.

## Arquitetura

```
app.py                          # a app Dash (interface + gráficos)
assets/style.css                # estilos (Dash carrega automaticamente)
dados/
  mapa_geografico.csv           # geocod -> região/nível (estático, do INE)
  precos_regionais.csv          # €/m² por concelho/região, 2022-2025
  indice_nacional.csv           # índice nacional trimestral, desde 2009
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

Os dois indicadores usados:

- [`0013042`](https://www.ine.pt/xurl/indx/0013042/PT) — Vendas de
  alojamentos familiares (Metodologia 2022 - €/m²), por localização
  geográfica e quartis, anual.
- [`0009201`](https://www.ine.pt/xurl/indx/0009201/PT) — Índice de preços
  da habitação (Base - 2015), por categoria do alojamento, trimestral.

Não é preciso nenhuma chave de API — é um serviço público e gratuito do
INE. O mapa geográfico (`dados/mapa_geografico.csv`, que traduz os códigos
do INE para nomes de concelhos/regiões) é estável ao longo do tempo, por
isso fica gravado no repositório em vez de ser pedido em cada atualização.

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
qualidade dos dados (`test_dados.py`, que confirmam que os CSVs gravados no
repositório continuam com a forma que a app espera).

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
