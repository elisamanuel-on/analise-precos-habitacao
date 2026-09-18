"""
Testes das melhorias visuais: tema claro/escuro, variação homóloga (mapa
divergente) e o gráfico do índice nacional com as 3 séries (Total, Novos,
Existentes). Usam os CSVs reais em dados/, não fazem pedidos à internet nem
arrancam um browser (só validam a figura/dados que a app Dash geraria).
"""
import plotly.graph_objects as go

from app import (
    ANO_MAIS_ANTIGO,
    ANO_MAIS_RECENTE,
    CORES_CATEGORICAS,
    CORES_DIVERGENTE,
    _barras_comparacao,
    _cores,
    _linha_evolucao_nacional,
    _mapa_concelhos,
    _variacao_por_concelho,
)


def test_cores_devolve_tema_certo():
    assert _cores("claro")["fundo"] != _cores("escuro")["fundo"]
    assert _cores("qualquer-outra-coisa") == _cores("claro")  # tudo o que não é "escuro" cai no claro


def test_variacao_por_concelho_calcula_percentagem_correta():
    df = _variacao_por_concelho("Venda", ANO_MAIS_RECENTE, "2.º quartil")
    assert not df.empty
    assert set(df.columns) == {"geocod", "regiao", "variacao_pct"}
    # nenhuma variação absurda (>500%) — apanharia uma troca de unidades ou de anos
    assert df["variacao_pct"].abs().max() < 500


def test_variacao_por_concelho_vazia_sem_ano_anterior():
    # o primeiro ano da série não tem ano anterior para comparar
    df = _variacao_por_concelho("Venda", ANO_MAIS_ANTIGO, "2.º quartil")
    assert df.empty
    assert list(df.columns) == ["geocod", "regiao", "variacao_pct"]


def test_mapa_modo_variacao_devolve_figura_com_escala_divergente():
    fig = _mapa_concelhos("Venda", ANO_MAIS_RECENTE, "2.º quartil", tema="claro", modo="variacao")
    assert isinstance(fig, go.Figure)
    trace = fig.data[0]
    cores_esperadas = CORES_DIVERGENTE["claro"]
    escala = [ponto[1] for ponto in trace.colorscale]
    assert cores_esperadas["negativo"] in escala
    assert cores_esperadas["neutro"] in escala
    assert cores_esperadas["positivo"] in escala
    # escala simétrica à volta de zero (é isso que faz o cinzento cair no valor 0)
    assert trace.zmin == -trace.zmax


def test_mapa_modo_variacao_sem_ano_anterior_nao_rebenta():
    # não deve levantar exceção mesmo sem dados de comparação
    fig = _mapa_concelhos("Venda", ANO_MAIS_ANTIGO, "2.º quartil", tema="claro", modo="variacao")
    assert isinstance(fig, go.Figure)


def test_mapa_modo_nivel_ainda_funciona_como_antes():
    fig = _mapa_concelhos("Venda", ANO_MAIS_RECENTE, "2.º quartil", tema="claro", modo="nivel")
    assert isinstance(fig, go.Figure)
    assert len(fig.data[0].z) > 0


def test_grafico_indice_tem_as_3_series_com_cores_categoricas_fixas():
    fig = _linha_evolucao_nacional("claro")
    nomes = [trace.name for trace in fig.data]
    assert nomes == ["Total", "Novos", "Existentes"]
    cores_usadas = [trace.line.color for trace in fig.data]
    assert cores_usadas == CORES_CATEGORICAS["claro"]


def test_grafico_indice_tema_escuro_usa_paleta_escura():
    fig = _linha_evolucao_nacional("escuro")
    cores_usadas = [trace.line.color for trace in fig.data]
    assert cores_usadas == CORES_CATEGORICAS["escuro"]


def test_barras_comparacao_usa_cor_do_tema():
    fig_claro = _barras_comparacao("Venda", "NUTS II", ANO_MAIS_RECENTE, "2.º quartil", "claro")
    fig_escuro = _barras_comparacao("Venda", "NUTS II", ANO_MAIS_RECENTE, "2.º quartil", "escuro")
    assert fig_claro.data[0].marker.color == _cores("claro")["destaque"]
    assert fig_escuro.data[0].marker.color == _cores("escuro")["destaque"]
