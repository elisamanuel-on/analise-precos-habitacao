"""
Análise de Preços de Habitação em Portugal — dashboard interativo com dados
reais e oficiais do INE (Instituto Nacional de Estatística).

Fontes (ver scripts/atualizar_dados.py):
- Vendas de alojamentos por concelho/região (€/m²), 2022-2025.
- Índice de preços da habitação, nacional, trimestral, desde 2009.

Corre localmente com: python app.py  (abre http://localhost:8050)
"""
import os

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

PASTA_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")

# --- Dados (reais, lidos dos CSVs gerados por scripts/atualizar_dados.py) ---
df_regioes = pd.read_csv(os.path.join(PASTA_DADOS, "precos_regionais.csv"))
df_indice = pd.read_csv(os.path.join(PASTA_DADOS, "indice_nacional.csv"))

ANOS_DISPONIVEIS = sorted(df_regioes["ano"].unique().tolist())
ANO_MAIS_RECENTE = ANOS_DISPONIVEIS[-1]
NIVEIS_DISPONIVEIS = ["NUTS II", "NUTS III", "Concelho"]
QUARTIS_DISPONIVEIS = sorted(df_regioes["quartil"].dropna().unique().tolist())
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


def _kpis_para_ano(ano: int) -> dict:
    """Calcula os números-resumo (estatísticas nacionais) para um ano."""
    linhas_ano = df_regioes[
        (df_regioes["ano"] == ano)
        & (df_regioes["quartil"] == QUARTIL_MEDIANA)
        & (df_regioes["nivel"] == "Concelho")
    ].dropna(subset=["preco_m2"])

    nacional = df_regioes[
        (df_regioes["ano"] == ano)
        & (df_regioes["quartil"] == QUARTIL_MEDIANA)
        & (df_regioes["nivel"] == "Nacional")
    ]
    preco_nacional = nacional["preco_m2"].iloc[0] if not nacional.empty else None

    preco_nacional_anterior = None
    if ano - 1 in ANOS_DISPONIVEIS:
        nacional_ant = df_regioes[
            (df_regioes["ano"] == ano - 1)
            & (df_regioes["quartil"] == QUARTIL_MEDIANA)
            & (df_regioes["nivel"] == "Nacional")
        ]
        if not nacional_ant.empty:
            preco_nacional_anterior = nacional_ant["preco_m2"].iloc[0]

    variacao = None
    if preco_nacional and preco_nacional_anterior:
        variacao = (preco_nacional / preco_nacional_anterior - 1) * 100

    mais_cara = linhas_ano.loc[linhas_ano["preco_m2"].idxmax()] if not linhas_ano.empty else None
    mais_barata = linhas_ano.loc[linhas_ano["preco_m2"].idxmin()] if not linhas_ano.empty else None

    return {
        "preco_nacional": preco_nacional,
        "variacao": variacao,
        "mais_cara": mais_cara,
        "mais_barata": mais_barata,
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


def _barras_comparacao(nivel: str, ano: int, quartil: str) -> go.Figure:
    df = df_regioes[
        (df_regioes["nivel"] == nivel) & (df_regioes["ano"] == ano) & (df_regioes["quartil"] == quartil)
    ].dropna(subset=["preco_m2"])
    df = df.sort_values("preco_m2", ascending=True)

    # Concelho tem 308 barras — mostra só as 25 mais caras para o gráfico ficar legível
    if nivel == "Concelho" and len(df) > 25:
        df = df.sort_values("preco_m2", ascending=False).head(25).sort_values("preco_m2", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["preco_m2"],
            y=df["regiao"],
            orientation="h",
            marker_color=CORES["destaque"],
            hovertemplate="%{y}<br>%{x:.0f} €/m²<extra></extra>",
        )
    )
    altura = max(340, 22 * len(df))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=altura,
        plot_bgcolor=CORES["cartao"],
        paper_bgcolor=CORES["cartao"],
        font=dict(color=CORES["texto"], family="system-ui, sans-serif"),
        xaxis=dict(showgrid=True, gridcolor=CORES["borda"], title="€ / m²"),
        yaxis=dict(showgrid=False),
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
                    "vendas de alojamentos familiares por concelho e índice de preços da "
                    "habitação desde 2009.",
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
            ],
            className="filtros-linha",
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
                        html.H2("Evolução do índice nacional (desde 2009)"),
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


@app.callback(Output("kpis", "children"), Input("filtro-ano", "value"))
def _atualizar_kpis(ano):
    k = _kpis_para_ano(ano)
    cartoes = []

    valor_nacional = f"{k['preco_nacional']:.0f} €/m²" if k["preco_nacional"] else "—"
    nota_variacao = ""
    if k["variacao"] is not None:
        sinal = "+" if k["variacao"] >= 0 else ""
        nota_variacao = f"{sinal}{k['variacao']:.1f}% desde {ano - 1}"
    cartoes.append(_cartao_kpi("Preço mediano nacional", valor_nacional, nota_variacao))

    if k["mais_cara"] is not None:
        cartoes.append(
            _cartao_kpi(
                "Concelho mais caro",
                k["mais_cara"]["regiao"],
                f"{k['mais_cara']['preco_m2']:.0f} €/m²",
            )
        )
    if k["mais_barata"] is not None:
        cartoes.append(
            _cartao_kpi(
                "Concelho mais acessível",
                k["mais_barata"]["regiao"],
                f"{k['mais_barata']['preco_m2']:.0f} €/m²",
            )
        )
    cartoes.append(_cartao_kpi("Concelhos analisados", "308", "todo o país"))
    return cartoes


@app.callback(
    Output("grafico-comparacao", "figure"),
    Input("filtro-nivel", "value"),
    Input("filtro-ano", "value"),
    Input("filtro-quartil", "value"),
)
def _atualizar_grafico_comparacao(nivel, ano, quartil):
    return _barras_comparacao(nivel, ano, quartil)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
