"""
Testes das funcionalidades de interatividade adicionadas ao mapa e às barras:
gradiente sequencial mais vivo (RAMPA_NIVEL_VIVIDA), cálculo de centroides
dos concelhos (pesquisa + pino no mapa), e o fluxo de seleção de concelho
(pesquisa, clique no mapa, botão "Limpar seleção").

Não faz suposições sobre nomes concretos de concelhos: usa sempre um
concelho retirado dos próprios dados carregados (app.CONCELHOS_PESQUISA /
app.CENTROIDE_POR_GEOCOD), para funcionar com os dados reais do INE.

Nota: se `test_graficos.py` tiver um teste que compare a cor exata do modo
"nível" do mapa com a rampa antiga (um único tom, claro->escuro), esse teste
precisa de ser atualizado para usar `app.RAMPA_NIVEL_VIVIDA` — foi uma
mudança pedida (gradiente mais vivo, visível em claro e escuro), não uma
regressão.
"""
import app as m


def _um_geocod_com_centroide():
    """Devolve (geocod, con_code) de um concelho qualquer com centroide calculado."""
    assert m.CONCELHOS_PESQUISA, "esperava pelo menos um concelho pesquisável"
    geocod = m.CONCELHOS_PESQUISA[0]["value"]
    con_code = m.CON_CODE_POR_GEOCOD[geocod]
    return geocod, con_code


class FalsoCtx:
    """Substitui dash.ctx nos testes sem depender de APIs internas do Dash
    (mais robusto entre versões do que simular dash.callback_context)."""

    def __init__(self, triggered_id):
        self.triggered_id = triggered_id


# --- Centroides e lookups ---------------------------------------------------


def test_centroide_de_um_quadrado_fica_no_centro():
    anel = [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]
    lon, lat = m._centroide_de_anel(anel)
    assert lon == 1.0
    assert lat == 1.0


def test_centroide_geometria_polygon():
    geometria = {"type": "Polygon", "coordinates": [[[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0], [0.0, 0.0]]]}
    centro = m._centroide(geometria)
    assert centro == (2.0, 2.0)


def test_centroide_geometria_multipolygon_escolhe_o_maior():
    pequeno = [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]
    grande = [[[10.0, 10.0], [16.0, 10.0], [16.0, 16.0], [10.0, 16.0], [10.0, 10.0]]]
    geometria = {"type": "MultiPolygon", "coordinates": [pequeno, grande]}
    centro = m._centroide(geometria)
    # o centroide devolvido deve ser o do maior polígono (grande), não do pequeno
    assert centro == (13.0, 13.0)


def test_todos_os_concelhos_pesquisaveis_tem_centroide_e_nome():
    for opcao in m.CONCELHOS_PESQUISA:
        geocod = opcao["value"]
        assert opcao["label"]
        assert geocod in m.CENTROIDE_POR_GEOCOD


def test_geocod_por_con_code_e_o_inverso_de_con_code_por_geocod():
    geocod, con_code = _um_geocod_com_centroide()
    assert m.GEOCOD_POR_CON_CODE[con_code] == geocod


# --- Rampa vívida sequencial -------------------------------------------------


def test_rampa_nivel_vivida_e_monotona_em_luminancia():
    """A rampa deve ficar sempre mais escura (não é uma 'rainbow' arbitrária)."""

    def luminancia(hex_cor):
        hex_cor = hex_cor.lstrip("#")
        r, g, b = (int(hex_cor[i : i + 2], 16) / 255 for i in (0, 2, 4))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    tons = [cor for _posicao, cor in m.RAMPA_NIVEL_VIVIDA]
    luminancias = [luminancia(t) for t in tons]
    assert luminancias == sorted(luminancias, reverse=True)


def test_mapa_modo_nivel_usa_a_rampa_vivida():
    fig = m._mapa_concelhos("Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "claro", "nivel")
    assert list(fig.data[0].colorscale) == [tuple(par) for par in m.RAMPA_NIVEL_VIVIDA]


# --- Foco num concelho (pino + zoom no mapa, contorno nas barras) ----------


def test_mapa_sem_foco_nao_tem_pino_e_usa_zoom_nacional():
    fig = m._mapa_concelhos("Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "claro", "nivel")
    assert len(fig.data) == 1
    assert fig.layout.map.zoom == 5.0


def test_mapa_com_foco_adiciona_pino_e_da_zoom():
    geocod, _con_code = _um_geocod_com_centroide()
    fig = m._mapa_concelhos("Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "claro", "nivel", foco_geocod=geocod)
    assert len(fig.data) == 2  # coropleto + pino
    assert fig.layout.map.zoom == 9.5
    lon_esperado, lat_esperado = m.CENTROIDE_POR_GEOCOD[geocod]
    assert fig.layout.map.center.lon == lon_esperado
    assert fig.layout.map.center.lat == lat_esperado


def test_mapa_com_foco_desconhecido_nao_rebenta_e_nao_da_zoom():
    fig = m._mapa_concelhos("Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "claro", "nivel", foco_geocod="isto-nao-existe")
    assert len(fig.data) == 1
    assert fig.layout.map.zoom == 5.0


def test_barras_sem_foco_mantem_cor_solida_da_marca():
    cores = m._cores("claro")
    fig = m._barras_comparacao("Venda", "NUTS II", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "claro")
    assert fig.data[0].marker.color == cores["destaque"]


def test_barras_com_foco_destaca_a_barra_certa():
    geocod, _con_code = _um_geocod_com_centroide()
    fig = m._barras_comparacao("Venda", "Concelho", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "claro", foco_geocod=geocod)
    df = m._dados_filtrados("Venda", "Concelho", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA).sort_values("preco_m2")
    if len(df) > 25:
        # a função só mostra as 25 mais caras — se o concelho escolhido ficou
        # de fora, não há barra nenhuma para destacar (comportamento correto)
        if geocod not in df.sort_values("preco_m2", ascending=False).head(25)["geocod"].tolist():
            assert not hasattr(fig.data[0].marker, "line") or fig.data[0].marker.line.width is None
            return
    larguras = fig.data[0].marker.line.width
    assert 2.5 in larguras
    assert larguras.count(2.5) == 1


# --- Fluxo de seleção (pesquisa / clique no mapa / limpar) ------------------


def test_selecao_via_pesquisa(monkeypatch):
    monkeypatch.setattr(m, "ctx", FalsoCtx("pesquisa-concelho"))
    geocod, _con_code = _um_geocod_com_centroide()
    resultado = m._atualizar_concelho_selecionado(geocod, None, None)
    assert resultado == (geocod, geocod)


def test_selecao_via_clique_no_mapa(monkeypatch):
    monkeypatch.setattr(m, "ctx", FalsoCtx("grafico-mapa"))
    geocod, con_code = _um_geocod_com_centroide()
    click_data = {"points": [{"location": con_code}]}
    resultado = m._atualizar_concelho_selecionado(None, click_data, None)
    assert resultado == (geocod, geocod)


def test_selecao_via_clique_no_mapa_sem_correspondencia(monkeypatch):
    monkeypatch.setattr(m, "ctx", FalsoCtx("grafico-mapa"))
    click_data = {"points": [{"location": "codigo-que-nao-existe"}]}
    resultado = m._atualizar_concelho_selecionado(None, click_data, None)
    assert resultado == (m.dash.no_update, m.dash.no_update)


def test_selecao_via_limpar(monkeypatch):
    monkeypatch.setattr(m, "ctx", FalsoCtx("botao-limpar-selecao"))
    resultado = m._atualizar_concelho_selecionado(None, None, 1)
    assert resultado == (None, None)


def test_estado_botao_limpar_segue_a_selecao():
    assert m._atualizar_estado_botao_limpar(None) is True
    geocod, _con_code = _um_geocod_com_centroide()
    assert m._atualizar_estado_botao_limpar(geocod) is False


# --- Painel de detalhe do concelho ------------------------------------------


def test_painel_concelho_vazio_sem_selecao():
    assert m._atualizar_painel_concelho(None, "Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA) == []


def test_painel_concelho_mostra_nome_e_valor():
    geocod, _con_code = _um_geocod_com_centroide()
    painel = m._atualizar_painel_concelho(geocod, "Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA)
    assert len(painel) == 1
    nome_esperado = m.NOME_POR_GEOCOD[geocod]
    cartao = painel[0]
    titulo = cartao.children[0].children
    assert nome_esperado in titulo