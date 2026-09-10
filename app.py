"""
Análise de Preços de Habitação em Portugal — dashboard interativo com dados
reais e oficiais do INE (Instituto Nacional de Estatística).

Fontes (ver scripts/atualizar_dados.py):
- Vendas de alojamentos por concelho/região (€/m²), 2022-2025.
- Rendas (arrendamento) de novos contratos por concelho/região (€/m²/mês), 2022-2025.
- Índice de preços da habitação (vendas), nacional, trimestral, desde 2009.

O mapa usa a fronteira geográfica dos concelhos (dados/concelhos.geojson,
fonte E-REDES/OpenDataSoft — dados abertos, sem necessidade de chave) e um
cruzamento de códigos (dados/concelhos_geojson_crosswalk.csv) para ligar cada
concelho do INE à sua forma no mapa.

Corre localmente com: python app.py  (abre http://localhost:8050)
"""
import os

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")

# --- Dados (reais, lidos dos CSVs/GeoJSON gerados por scripts/atualizar_dados.py) ---
df_vendas = pd.read_csv(os.path.join(PASTA_DADOS, "precos_regionais.csv"))
df_arrendamento = pd.read_csv(os.path.join(PASTA_DADOS, "rendas_regionais.csv"))
df_indice = pd.read_csv(os.path.join(PASTA_DADOS, "indice_nacional.csv"))
df_crosswalk = pd.read_csv(os.path.join(PASTA_DADOS, "concelhos_geojson_crosswalk.csv"), dtype={"con_code": str})

with open(os.path.join(PASTA_DADOS, "concelhos.geojson"), encoding="utf-8") as f:
    import json

    GEOJSON_CONCELHOS = json.load(f)

# --- Configuração dos dois tipos de dado (venda / arrendamento) ---
TIPOS = {
    "Venda": {
        "df": df_vendas,
        "coluna": "preco_m2",
        "unidade": "€/m²",
        "unidade_eixo": "€ / m²",
        "formato_curto": "{:.0f}",
        "formato_hover": ".0f",
    },
    "Arrendamento": {
        "df": df_arrendamento,
        "coluna": "renda_m2",
        "unidade": "€/m²/mês",
        "unidade_eixo": "€ / m² / mês",
        "formato_curto": "{:.2f}",
        "formato_hover": ".2f",
    },
}
TIPOS_DISPONIVEIS = list(TIPOS.keys())

ANOS_DISPONIVEIS = sorted(df_vendas["ano"].unique().tolist())
ANO_MAIS_RECENTE = ANOS_DISPONIVEIS[-1]
NIVEIS_DISPONIVEIS = ["NUTS II", "NUTS III", "Concelho"]
QUARTIS_DISPONIVEIS = sorted(df_vendas["quartil"].dropna().unique().tolist())
QUARTIL_MEDIANA = "2.º quartil"

CORES = {
    "fundo": "#f7f7f5",
    "cartao": "#ffffff",
    "borda": "#e4e2dd",
    "texto": "#2b2b28",
    "texto_suave": "#6b6a65",
    "destaque": "#2f6f4f",
    "destaque_suave": "#e5f0ea",
}


def _kpis_para_ano(tipo: str, ano: int) -> dict:
    """Calcula os números-resumo (estatísticas nacionais) para um ano e tipo (venda/arrendamento)."""
    cfg = TIPOS[tipo]
    df, coluna = cfg["df"], cfg["coluna"]

    linhas_ano = df[
        (df["ano"] == ano) & (df["quartil"] == QUARTIL_MEDIANA) & (df["nivel"] == "Concelho")
    ].dropna(subset=[coluna])

    nacional = df[(df["ano"] == ano) & (df["quartil"] == QUARTIL_MEDIANA) & (df["nivel"] == "Nacional")]
    valor_nacional = nacional[coluna].iloc[0] if not nacional.empty else None

    valor_nacional_anterior = None
    if ano - 1 in ANOS_DISPONIVEIS:
        nacional_ant = df[(df["ano"] == ano - 1) & (df["quartil"] == QUARTIL_MEDIANA) & (df["nivel"] == "Nacional")]
        if not nacional_ant.empty:
            valor_nacional_anterior = nacional_ant[coluna].iloc[0]

    variacao = None
    if valor_nacional and valor_nacional_anterior:
        variacao = (valor_nacional / valor_nacional_anterior - 1) * 100

    mais_caro = linhas_ano.loc[linhas_ano[coluna].idxmax()] if not linhas_ano.empty else None
    mais_barato = linhas_ano.loc[linhas_ano[coluna].idxmin()] if not linhas_ano.empty else None

    return {
        "valor_nacional": valor_nacional,
        "variacao": variacao,
        "mais_caro": mais_caro,
        "mais_barato": mais_barato,
    }


def _cartao_kpi(titulo: str, valor: str, nota: str = "") -> html.Div:
    filhos = [html.Div(titulo, className="kpi-titulo"), html.Div(valor, className="kpi-valor")]
    if nota:
        filhos.append(html.Div(nota, className="kpi-nota"))
    return html.Div(filhos, className="kpi-cartao")


def _linha_evolucao_nacional() -> go.Figure:
    df = df_indice[df_indice["categoria"] == "Total"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["periodo"],
            y=df["indice"],
            mode="lines",
            line=dict(color=CORES["destaque"], width=2.5),
            fill="tozeroy",
            fillcolor=CORES["destaque_suave"],
            hovertemplate="%{x}<br>Índice: %{y:.1f}<extra></extra>",
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=340,
        plot_bgcolor=CORES["cartao"],
        paper_bgcolor=CORES["cartao"],
        font=dict(color=CORES["texto"], family="system-ui, sans-serif"),
        xaxis=dict(showgrid=False, tickangle=-45, nticks=16),
        yaxis=dict(showgrid=True, gridcolor=CORES["borda"], title="Índice (Base 2015 = 100)"),
    )
    return fig


def _dados_filtrados(tipo: str, nivel: str, ano: int, quartil: str) -> pd.DataFrame:
    cfg = TIPOS[tipo]
    df = cfg["df"]
    return df[(df["nivel"] == nivel) & (df["ano"] == ano) & (df["quartil"] == quartil)].dropna(
        subset=[cfg["coluna"]]
    )


def _barras_comparacao(tipo: str, nivel: str, ano: int, quartil: str) -> go.Figure:
    cfg = TIPOS[tipo]
    coluna = cfg["coluna"]
    df = _dados_filtrados(tipo, nivel, ano, quartil).sort_values(coluna, ascending=True)

    # Concelho tem 308 barras — mostra só as 25 mais caras para o gráfico ficar legível
    if nivel == "Concelho" and len(df) > 25:
        df = df.sort_values(coluna, ascending=False).head(25).sort_values(coluna, ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df[coluna],
            y=df["regiao"],
            orientation="h",
            marker_color=CORES["destaque"],
            hovertemplate="%{y}<br>%{x:" + cfg["formato_hover"] + "} " + cfg["unidade"] + "<extra></extra>",
        )
    )
    altura = max(340, 22 * len(df))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=altura,
        plot_bgcolor=CORES["cartao"],
        paper_bgcolor=CORES["cartao"],
        font=dict(color=CORES["texto"], family="system-ui, sans-serif"),
        xaxis=dict(showgrid=True, gridcolor=CORES["borda"], title=cfg["unidade_eixo"]),
        yaxis=dict(showgrid=False),
    )
    return fig


def _mapa_concelhos(tipo: str, ano: int, quartil: str) -> go.Figure:
    cfg = TIPOS[tipo]
    coluna = cfg["coluna"]
    df = _dados_filtrados(tipo, "Concelho", ano, quartil).merge(
        df_crosswalk[["geocod", "con_code"]], on="geocod", how="inner"
    )

    fig = go.Figure(
        go.Choroplethmap(
            geojson=GEOJSON_CONCELHOS,
            locations=df["con_code"],
            z=df[coluna],
            featureidkey="properties.con_code",
            colorscale=[[0, CORES["destaque_suave"]], [1, CORES["destaque"]]],
            marker_line_width=0.3,
            marker_line_color="#ffffff",
            colorbar=dict(title=cfg["unidade"], thickness=14, len=0.8),
            text=df["regiao"],
            hovertemplate="%{text}<br>%{z:" + cfg["formato_hover"] + "} " + cfg["unidade"] + "<extra></extra>",
        )
    )
    fig.update_layout(
        map_style="carto-positron",
        map_zoom=5.0,
        map_center={"lat": 39.6, "lon": -8.2},
        margin=dict(l=0, r=0, t=0, b=0),
        height=440,
        paper_bgcolor=CORES["cartao"],
    )
    return fig


app = dash.Dash(__name__, title="Análise de Preços de Habitação em Portugal")
server = app.server  # necessário para o Render (gunicorn aponta para "app:server")

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1("Análise de Preços de Habitação em Portugal"),
                html.P(
                    "Dados reais e oficiais do INE (Instituto Nacional de Estatística): "
                    "vendas e arrendamento de alojamentos familiares por concelho, e a "
                    "evolução do índice de preços de venda da habitação desde 2009.",
                    className="subtitulo",
                ),
            ],
            className="cabecalho",
        ),
        html.Div(id="kpis", className="kpis-linha"),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Tipo"),
                        dcc.Dropdown(
                            id="filtro-tipo",
                            options=[{"label": t, "value": t} for t in TIPOS_DISPONIVEIS],
                            value="Venda",
                            clearable=False,
                        ),
                    ],
                    className="filtro",
                ),
                html.Div(
                    [
                        html.Label("Nível geográfico"),
                        dcc.Dropdown(
                            id="filtro-nivel",
                            options=[{"label": n, "value": n} for n in NIVEIS_DISPONIVEIS],
                            value="NUTS II",
                            clearable=False,
                        ),
                    ],
                    className="filtro",
                ),
                html.Div(
                    [
                        html.Label("Ano"),
                        dcc.Dropdown(
                            id="filtro-ano",
                            options=[{"label": str(a), "value": a} for a in ANOS_DISPONIVEIS],
                            value=ANO_MAIS_RECENTE,
                            clearable=False,
                        ),
                    ],
                    className="filtro",
                ),
                html.Div(
                    [
                        html.Label("Quartil"),
                        dcc.Dropdown(
                            id="filtro-quartil",
                            options=[{"label": q, "value": q} for q in QUARTIS_DISPONIVEIS],
                            value=QUARTIL_MEDIANA,
                            clearable=False,
                        ),
                    ],
                    className="filtro",
                ),
                html.Div(
                    [
                        html.Label(" "),
                        html.Button("⬇ Descarregar CSV", id="botao-download", className="botao-download"),
                        dcc.Download(id="download-dados"),
                    ],
                    className="filtro",
                ),
            ],
            className="filtros-linha",
        ),
        html.Div(
            [
                html.H2("Mapa por concelho"),
                dcc.Graph(id="grafico-mapa", config={"displayModeBar": False}),
            ],
            className="cartao-grafico cartao-mapa",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H2("Comparação entre regiões"),
                        dcc.Graph(id="grafico-comparacao", config={"displayModeBar": False}),
                    ],
                    className="cartao-grafico",
                ),
                html.Div(
                    [
                        html.H2("Evolução do índice nacional de vendas (desde 2009)"),
                        dcc.Graph(figure=_linha_evolucao_nacional(), config={"displayModeBar": False}),
                    ],
                    className="cartao-grafico",
                ),
            ],
            className="graficos-grelha",
        ),
        html.Footer(
            [
                "Fonte: ",
                html.A("INE — Instituto Nacional de Estatística", href="https://www.ine.pt", target="_blank"),
                ". Projeto de portefólio de Elisama Manuel.",
            ],
            className="rodape",
        ),
    ],
    className="pagina",
)


@app.callback(Output("kpis", "children"), Input("filtro-tipo", "value"), Input("filtro-ano", "value"))
def _atualizar_kpis(tipo, ano):
    cfg = TIPOS[tipo]
    k = _kpis_para_ano(tipo, ano)
    cartoes = []

    valor_nacional = cfg["formato_curto"].format(k["valor_nacional"]) + f" {cfg['unidade']}" if k[
        "valor_nacional"
    ] else "—"
    titulo_nacional = "Renda mediana nacional" if tipo == "Arrendamento" else "Preço mediano nacional"
    nota_variacao = ""
    if k["variacao"] is not None:
        sinal = "+" if k["variacao"] >= 0 else ""
        nota_variacao = f"{sinal}{k['variacao']:.1f}% desde {ano - 1}"
    cartoes.append(_cartao_kpi(titulo_nacional, valor_nacional, nota_variacao))

    rotulo_caro = "Concelho mais caro" if tipo == "Venda" else "Concelho com renda mais alta"
    rotulo_barato = "Concelho mais acessível" if tipo == "Venda" else "Concelho com renda mais baixa"

    if k["mais_caro"] is not None:
        cartoes.append(
            _cartao_kpi(
                rotulo_caro,
                k["mais_caro"]["regiao"],
                cfg["formato_curto"].format(k["mais_caro"][cfg["coluna"]]) + f" {cfg['unidade']}",
            )
        )
    if k["mais_barato"] is not None:
        cartoes.append(
            _cartao_kpi(
                rotulo_barato,
                k["mais_barato"]["regiao"],
                cfg["formato_curto"].format(k["mais_barato"][cfg["coluna"]]) + f" {cfg['unidade']}",
            )
        )
    cartoes.append(_cartao_kpi("Concelhos analisados", "308", "todo o país"))
    return cartoes


@app.callback(
    Output("grafico-comparacao", "figure"),
    Input("filtro-tipo", "value"),
    Input("filtro-nivel", "value"),
    Input("filtro-ano", "value"),
    Input("filtro-quartil", "value"),
)
def _atualizar_grafico_comparacao(tipo, nivel, ano, quartil):
    return _barras_comparacao(tipo, nivel, ano, quartil)


@app.callback(
    Output("grafico-mapa", "figure"),
    Input("filtro-tipo", "value"),
    Input("filtro-ano", "value"),
    Input("filtro-quartil", "value"),
)
def _atualizar_mapa(tipo, ano, quartil):
    return _mapa_concelhos(tipo, ano, quartil)


@app.callback(
    Output("download-dados", "data"),
    Input("botao-download", "n_clicks"),
    State("filtro-tipo", "value"),
    State("filtro-nivel", "value"),
    State("filtro-ano", "value"),
    State("filtro-quartil", "value"),
    prevent_initial_call=True,
)
def _descarregar_csv(n_clicks, tipo, nivel, ano, quartil):
    df = _dados_filtrados(tipo, nivel, ano, quartil)
    nome_ficheiro = f"{tipo.lower()}_{nivel.lower().replace(' ', '-')}_{ano}.csv"
    return dcc.send_data_frame(df.to_csv, nome_ficheiro, index=False)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
