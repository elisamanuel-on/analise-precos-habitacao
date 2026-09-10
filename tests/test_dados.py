"""
Testes de qualidade dos dados: confirmam que os CSVs guardados no
repositório (dados reais, extraídos do INE) continuam com a forma esperada
pela app — úteis para apanhar problemas cedo, sem precisar de arrancar o
Dash. Não fazem pedidos à internet.
"""
import json
import os

import pandas as pd

PASTA_DADOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados")


def test_precos_regionais_tem_as_colunas_esperadas():
    df = pd.read_csv(os.path.join(PASTA_DADOS, "precos_regionais.csv"))
    assert set(df.columns) == {"ano", "geocod", "regiao", "nivel", "quartil", "preco_m2"}
    assert not df.empty


def test_precos_regionais_tem_308_concelhos():
    df = pd.read_csv(os.path.join(PASTA_DADOS, "precos_regionais.csv"))
    assert df[df["nivel"] == "Concelho"]["geocod"].nunique() == 308


def test_precos_regionais_niveis_e_quartis_validos():
    df = pd.read_csv(os.path.join(PASTA_DADOS, "precos_regionais.csv"))
    assert set(df["nivel"].unique()) <= {"Nacional", "NUTS I", "NUTS II", "NUTS III", "Concelho"}
    assert set(df["quartil"].unique()) == {"1.º quartil", "2.º quartil", "3.º quartil"}


def test_indice_nacional_tem_as_colunas_esperadas():
    df = pd.read_csv(os.path.join(PASTA_DADOS, "indice_nacional.csv"))
    assert set(df.columns) == {"ano", "trimestre", "periodo", "categoria", "indice"}
    assert not df.empty


def test_indice_nacional_comeca_em_2009():
    df = pd.read_csv(os.path.join(PASTA_DADOS, "indice_nacional.csv"))
    assert df["ano"].min() == 2009


def test_mapa_geografico_tem_as_colunas_esperadas():
    df = pd.read_csv(os.path.join(PASTA_DADOS, "mapa_geografico.csv"))
    assert set(df.columns) == {"geocod", "regiao", "nivel"}
    assert not df.empty


def test_rendas_regionais_tem_as_colunas_esperadas():
    df = pd.read_csv(os.path.join(PASTA_DADOS, "rendas_regionais.csv"))
    assert set(df.columns) == {"ano", "geocod", "regiao", "nivel", "quartil", "renda_m2"}
    assert not df.empty


def test_rendas_regionais_tem_308_concelhos():
    df = pd.read_csv(os.path.join(PASTA_DADOS, "rendas_regionais.csv"))
    assert df[df["nivel"] == "Concelho"]["geocod"].nunique() == 308


def test_rendas_regionais_niveis_e_quartis_validos():
    df = pd.read_csv(os.path.join(PASTA_DADOS, "rendas_regionais.csv"))
    assert set(df["nivel"].unique()) <= {"Nacional", "NUTS I", "NUTS II", "NUTS III", "Concelho"}
    assert set(df["quartil"].unique()) == {"1.º quartil", "2.º quartil", "3.º quartil"}


def test_rendas_valores_plausiveis():
    # renda por m²/mês tem uma escala muito diferente do preço de venda por m²
    # (euros por mês, não milhares de euros) — confirma que não há troca de unidades
    df = pd.read_csv(os.path.join(PASTA_DADOS, "rendas_regionais.csv"))
    valores = df["renda_m2"].dropna()
    assert valores.min() > 0
    assert valores.max() < 100  # nenhum concelho real chega a 100€/m²/mês


def test_concelhos_geojson_tem_308_concelhos():
    with open(os.path.join(PASTA_DADOS, "concelhos.geojson"), encoding="utf-8") as f:
        geojson = json.load(f)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 308
    for feature in geojson["features"][:5]:
        assert "con_code" in feature["properties"]


def test_crosswalk_liga_todos_os_concelhos_ao_geojson():
    df_cross = pd.read_csv(os.path.join(PASTA_DADOS, "concelhos_geojson_crosswalk.csv"), dtype=str)
    assert len(df_cross) == 308
    assert df_cross["con_code"].nunique() == 308  # sem códigos repetidos

    with open(os.path.join(PASTA_DADOS, "concelhos.geojson"), encoding="utf-8") as f:
        geojson = json.load(f)
    codigos_geojson = {feature["properties"]["con_code"] for feature in geojson["features"]}

    codigos_em_falta = set(df_cross["con_code"]) - codigos_geojson
    assert codigos_em_falta == set(), f"códigos sem correspondência no geojson: {codigos_em_falta}"

    df_mapa = pd.read_csv(os.path.join(PASTA_DADOS, "mapa_geografico.csv"), dtype=str)
    geocods_concelho = set(df_mapa[df_mapa["nivel"] == "Concelho"]["geocod"])
    assert set(df_cross["geocod"]) == geocods_concelho
