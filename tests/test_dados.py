"""
Testes de qualidade dos dados: confirmam que os CSVs guardados no
repositório (dados reais, extraídos do INE) continuam com a forma esperada
pela app — úteis para apanhar problemas cedo, sem precisar de arrancar o
Dash. Não fazem pedidos à internet.
"""
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
