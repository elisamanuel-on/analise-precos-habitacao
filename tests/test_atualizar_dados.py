"""
Testes com respostas simuladas (mocks) da API do INE — não fazem pedidos
reais à internet, por isso correm em qualquer máquina/CI. As respostas de
exemplo usadas aqui refletem a estrutura real confirmada manualmente na API
do INE (https://www.ine.pt/ine/json_indicador/pindica.jsp).

Corre com: pytest -v
"""
import csv
import os
from unittest.mock import patch

import pandas as pd
import pytest

from scripts import atualizar_dados

RESPOSTA_PRECOS_EXEMPLO = {
    "IndicadorCod": "0013042",
    "UltimoPref": "2025",
    "Dados": {
        "2024": [
            {"geocod": "PT", "geodsg": "Portugal", "dim_3_t": "2.º quartil", "valor": "1777"},
            {"geocod": "1950502", "geodsg": "Castelo Branco", "dim_3_t": "2.º quartil", "valor": "800"},
        ],
        "2025": [
            {"geocod": "PT", "geodsg": "Portugal", "dim_3_t": "2.º quartil", "valor": "2076"},
            {"geocod": "1950502", "geodsg": "Castelo Branco", "dim_3_t": "2.º quartil", "valor": "966"},
        ],
    },
}

RESPOSTA_INDICE_EXEMPLO = {
    "IndicadorCod": "0009201",
    "Dados": {
        "1.º Trimestre de 2009": [
            {"geocod": "PT", "geodsg": "Portugal", "dim_3_t": "Total", "valor": "105.67"},
        ],
        "4.º Trimestre de 2025": [
            {"geocod": "PT", "geodsg": "Portugal", "dim_3_t": "Total", "valor": "280.21"},
        ],
    },
}


@pytest.fixture
def pasta_dados_temp(tmp_path):
    # o mapa geográfico é estático e vem sempre do repositório
    mapa = pd.DataFrame(
        [
            {"geocod": "PT", "regiao": "Portugal", "nivel": "Nacional"},
            {"geocod": "1950502", "regiao": "Castelo Branco", "nivel": "Concelho"},
        ]
    )
    mapa.to_csv(tmp_path / "mapa_geografico.csv", index=False)
    return str(tmp_path)


def test_atualizar_precos_regionais_grava_csv_correto(pasta_dados_temp):
    with patch.object(atualizar_dados, "_pedir_indicador", return_value=RESPOSTA_PRECOS_EXEMPLO):
        total = atualizar_dados.atualizar_precos_regionais(pasta_dados_temp)

    assert total == 4  # 2 anos x 2 linhas
    df = pd.read_csv(os.path.join(pasta_dados_temp, "precos_regionais.csv"))
    assert set(df.columns) == {"ano", "geocod", "regiao", "nivel", "quartil", "preco_m2"}

    linha = df[(df["ano"] == 2025) & (df["geocod"] == "1950502")].iloc[0]
    assert linha["regiao"] == "Castelo Branco"
    assert linha["nivel"] == "Concelho"
    assert linha["preco_m2"] == 966.0


def test_atualizar_precos_regionais_ignora_geocod_fora_do_mapa(pasta_dados_temp):
    resposta = {
        "Dados": {
            "2025": [
                {"geocod": "PT", "geodsg": "Portugal", "dim_3_t": "2.º quartil", "valor": "2076"},
                {"geocod": "9999999", "geodsg": "Desconhecido", "dim_3_t": "2.º quartil", "valor": "100"},
            ]
        }
    }
    with patch.object(atualizar_dados, "_pedir_indicador", return_value=resposta):
        total = atualizar_dados.atualizar_precos_regionais(pasta_dados_temp)

    assert total == 1  # só a linha "PT" está no mapa de teste


def test_atualizar_indice_nacional_grava_csv_correto(pasta_dados_temp):
    with patch.object(atualizar_dados, "_pedir_indicador", return_value=RESPOSTA_INDICE_EXEMPLO):
        total = atualizar_dados.atualizar_indice_nacional(pasta_dados_temp)

    assert total == 2
    df = pd.read_csv(os.path.join(pasta_dados_temp, "indice_nacional.csv"))
    primeira = df.iloc[0]
    assert primeira["ano"] == 2009
    assert primeira["trimestre"] == 1
    assert primeira["periodo"] == "2009-T1"
    ultima = df.iloc[-1]
    assert ultima["ano"] == 2025
    assert ultima["indice"] == 280.21


def test_pedir_indicador_levanta_erro_claro_quando_ine_devolve_falha():
    resposta_falsa_ine = {
        "Sucesso": {"Falso": [{"Msg": "Código(s) em Dim2 não válido(s) para o indicador."}]}
    }
    with patch("scripts.atualizar_dados.requests.get") as pedido_falso:
        pedido_falso.return_value.raise_for_status.return_value = None
        pedido_falso.return_value.json.return_value = [resposta_falsa_ine]

        with pytest.raises(RuntimeError, match="INE devolveu erro"):
            atualizar_dados._pedir_indicador("0013042", "T")
