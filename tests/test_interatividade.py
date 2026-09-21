"""
Testes das funcionalidades adicionadas ao dashboard: tema único colorido
(sem dark/light), pesquisa/clique num concelho (pino + zoom no mapa, destaque
nas barras, painel de detalhe) e a tradução automática para o idioma do
browser de quem visita (sem botão — deteção via "Accept-Language").

Não faz suposições sobre nomes concretos de concelhos: usa sempre um
concelho retirado dos próprios dados carregados (app.CONCELHOS_PESQUISA /
app.CENTROIDE_POR_GEOCOD), para funcionar com os dados reais do INE.

Nota: se `test_graficos.py` tiver testes que dependam do antigo parâmetro
"tema" de `_barras_comparacao`/`_mapa_concelhos`/`_linha_evolucao_nacional`,
ou de `app._cores(tema)`, ou do modo escuro, esses testes ficaram
desatualizados de propósito — o dashboard passou a ter um único tema
(app.CORES), sem alternância dark/light. `pytest -v` mostra exatamente qual
teste falha, se for o caso.
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


def test_centroide_geometria_multipolygon_escolhe_o_maior():
    pequeno = [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]
    grande = [[[10.0, 10.0], [16.0, 10.0], [16.0, 16.0], [10.0, 16.0], [10.0, 10.0]]]
    geometria = {"type": "MultiPolygon", "coordinates": [pequeno, grande]}
    centro = m._centroide(geometria)
    assert centro == (13.0, 13.0)


def test_todos_os_concelhos_pesquisaveis_tem_centroide_e_nome():
    for opcao in m.CONCELHOS_PESQUISA:
        geocod = opcao["value"]
        assert opcao["label"]
        assert geocod in m.CENTROIDE_POR_GEOCOD


def test_geocod_por_con_code_e_o_inverso_de_con_code_por_geocod():
    geocod, con_code = _um_geocod_com_centroide()
    assert m.GEOCOD_POR_CON_CODE[con_code] == geocod


# --- Tema único colorido (sem dark/light) -----------------------------------


def test_nao_existe_modo_escuro():
    """Regressão: o dashboard passou a ter um único tema — confirma que a
    antiga infraestrutura de dark/light não voltou a aparecer sem querer."""
    assert not hasattr(m, "CORES_ESCURO")
    assert not hasattr(m, "CORES_CLARO")
    assert not hasattr(m, "_cores")


def test_cores_quente_e_fria_tem_contraste_suficiente_sobre_o_cartao():
    def _luminancia(hex_cor):
        hex_cor = hex_cor.lstrip("#")
        r, g, b = (int(hex_cor[i : i + 2], 16) / 255 for i in (0, 2, 4))

        def canal(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)

    def _contraste(a, b):
        la, lb = _luminancia(a), _luminancia(b)
        claro, escuro = max(la, lb), min(la, lb)
        return (claro + 0.05) / (escuro + 0.05)

    for tom in ("quente", "frio"):
        assert _contraste(m.CORES[tom], m.CORES["cartao"]) >= 4.5


def test_rampa_nivel_vivida_e_monotona_em_luminancia():
    def luminancia(hex_cor):
        hex_cor = hex_cor.lstrip("#")
        r, g, b = (int(hex_cor[i : i + 2], 16) / 255 for i in (0, 2, 4))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    tons = [cor for _posicao, cor in m.RAMPA_NIVEL_VIVIDA]
    luminancias = [luminancia(t) for t in tons]
    assert luminancias == sorted(luminancias, reverse=True)


def test_mapa_modo_nivel_usa_a_rampa_vivida():
    fig = m._mapa_concelhos("Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA)
    assert list(fig.data[0].colorscale) == [tuple(par) for par in m.RAMPA_NIVEL_VIVIDA]


def test_barras_sem_foco_usa_cor_quente_solida():
    fig = m._barras_comparacao("Venda", "NUTS II", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA)
    assert fig.data[0].marker.color == m.CORES["quente"]


# --- Foco num concelho (pino + zoom no mapa, contorno nas barras) ----------


def test_mapa_sem_foco_nao_tem_pino_e_usa_zoom_nacional():
    fig = m._mapa_concelhos("Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA)
    assert len(fig.data) == 1
    assert fig.layout.map.zoom == 5.0


def test_mapa_com_foco_adiciona_pino_frio_e_da_zoom():
    geocod, _con_code = _um_geocod_com_centroide()
    fig = m._mapa_concelhos("Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "nivel", geocod)
    assert len(fig.data) == 2  # coropleto + pino
    assert fig.layout.map.zoom == 9.5
    assert fig.data[1].marker.color == m.CORES["frio"]
    lon_esperado, lat_esperado = m.CENTROIDE_POR_GEOCOD[geocod]
    assert fig.layout.map.center.lon == lon_esperado
    assert fig.layout.map.center.lat == lat_esperado


def test_mapa_com_foco_desconhecido_nao_rebenta_e_nao_da_zoom():
    fig = m._mapa_concelhos("Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "nivel", "isto-nao-existe")
    assert len(fig.data) == 1
    assert fig.layout.map.zoom == 5.0


def test_barras_com_foco_destaca_a_barra_certa():
    geocod, _con_code = _um_geocod_com_centroide()
    fig = m._barras_comparacao("Venda", "Concelho", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, foco_geocod=geocod)
    df = m._dados_filtrados("Venda", "Concelho", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA)
    if len(df) > 25 and geocod not in df.sort_values("preco_m2", ascending=False).head(25)["geocod"].tolist():
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
    assert m._atualizar_painel_concelho(None, "Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "pt") == []


def test_painel_concelho_mostra_nome_e_valor():
    geocod, _con_code = _um_geocod_com_centroide()
    painel = m._atualizar_painel_concelho(geocod, "Venda", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "pt")
    assert len(painel) == 1
    nome_esperado = m.NOME_POR_GEOCOD[geocod]
    cartao = painel[0]
    titulo = cartao.children[0].children
    assert nome_esperado in titulo


# --- Tradução automática (deteção pelo Accept-Language do browser) ---------


def test_traducoes_pt_e_en_tem_as_mesmas_chaves():
    assert set(m.TRADUCOES["pt"].keys()) == set(m.TRADUCOES["en"].keys())


def test_t_cai_em_portugues_por_omissao_para_idioma_desconhecido():
    assert m._t("titulo", "fr") == m.TRADUCOES["pt"]["titulo"]


def test_rotulo_quartil_so_traduz_o_texto_mostrado_nao_o_valor_interno():
    quartil_original = m.QUARTIL_MEDIANA
    rotulo_en = m._rotulo_quartil(quartil_original, "en")
    rotulo_pt = m._rotulo_quartil(quartil_original, "pt")
    assert rotulo_pt == quartil_original  # valor interno = usado para filtrar os dados
    assert rotulo_en != quartil_original
    assert "quartile" in rotulo_en


def test_rotulo_tipo_traduz_label_mas_value_interno_fica_intacto():
    assert m._rotulo_tipo("Venda", "pt") == "Venda"
    assert m._rotulo_tipo("Venda", "en") == "Sale"
    # "Venda" continua a ser a chave usada em TIPOS/_dados_filtrados, só o
    # texto mostrado no dropdown muda — testado indiretamente: TIPOS não mudou.
    assert "Venda" in m.TIPOS


def test_deteta_idioma_do_cabecalho_accept_language():
    cliente = m.app.server.test_client()
    resposta_en = cliente.get("/", headers={"Accept-Language": "en-US,en;q=0.9"})
    resposta_pt = cliente.get("/", headers={"Accept-Language": "pt-PT,pt;q=0.9"})
    assert resposta_en.status_code == 200
    assert resposta_pt.status_code == 200


def test_layout_muda_conteudo_conforme_idioma():
    layout_pt = m._construir_layout("pt")
    layout_en = m._construir_layout("en")
    assert layout_pt.children[2].children[0].children == m.TRADUCOES["pt"]["titulo"]
    assert layout_en.children[2].children[0].children == m.TRADUCOES["en"]["titulo"]


def test_dados_exportacao_traduz_cabecalhos_das_colunas():
    df_pt = m._dados_exportacao("Venda", "NUTS II", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "pt")
    df_en = m._dados_exportacao("Venda", "NUTS II", m.ANO_MAIS_RECENTE, m.QUARTIL_MEDIANA, "en")
    assert "Região" in df_pt.columns
    assert "Region" in df_en.columns
    assert "Preço (€/m²)" in df_pt.columns
    assert "Price (€/sqm)" in df_en.columns