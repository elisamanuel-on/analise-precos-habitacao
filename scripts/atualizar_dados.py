"""
Atualiza os dados reais (não simulados) usados pela app, a partir da API
oficial do INE (Instituto Nacional de Estatística):

- Indicador 0013042: "Vendas de alojamentos familiares (Metodologia 2022 -
  €/m²)" por concelho/região e quartil, desde 2022 (anual). Fonte:
  https://www.ine.pt/xurl/indx/0013042/PT
- Indicador 0009201: "Índice de preços da habitação (Base - 2015)" nacional,
  trimestral, desde 2009. Fonte: https://www.ine.pt/xurl/indx/0009201/PT

O mapa geográfico (`dados/mapa_geografico.csv`, geocod -> região/nível) vem
do metainfo do indicador 0013042 e é estável (concelhos não mudam), por isso
fica gravado no repositório em vez de ser pedido todas as vezes.

Corre com: python -m scripts.atualizar_dados
"""
import logging
import os
import sys

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.ine.pt/ine/json_indicador/pindica.jsp"

# Alguns servidores (incluindo os runners do GitHub Actions) bloqueiam pedidos
# com o user-agent por omissão da biblioteca requests — identificamo-nos como
# um pedido normal de browser, tal como qualquer pessoa a consultar o site.
CABECALHOS_PEDIDO = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

ANOS_PRECOS_REGIONAIS = ["2022", "2023", "2024", "2025"]


def _pedir_indicador(varcd: str, dim1: str) -> dict:
    """Pede um indicador à API do INE. Real, não simulado."""
    parametros = {"op": "2", "varcd": varcd, "Dim1": dim1, "lang": "PT"}
    resposta = requests.get(
        BASE_URL, params=parametros, headers=CABECALHOS_PEDIDO, timeout=30
    )
    resposta.raise_for_status()
    dados = resposta.json()
    registo = dados[0]
    if "Sucesso" in registo and "Falso" in registo["Sucesso"]:
        msg = registo["Sucesso"]["Falso"][0].get("Msg", "erro desconhecido")
        raise RuntimeError(f"INE devolveu erro para o indicador {varcd}: {msg}")
    return registo


def atualizar_precos_regionais(pasta_dados: str) -> int:
    """
    Vendas de alojamentos por concelho/região e quartil (€/m²), últimos anos.
    Grava dados/precos_regionais.csv. Devolve o número de linhas gravadas.
    """
    mapa = pd.read_csv(os.path.join(pasta_dados, "mapa_geografico.csv"), dtype=str)
    mapa_geocod = mapa.set_index("geocod")[["regiao", "nivel"]].to_dict("index")

    dim1 = ",".join(f"S7A{ano}" for ano in ANOS_PRECOS_REGIONAIS)
    registo = _pedir_indicador("0013042", dim1)

    linhas = []
    for ano, entradas in registo["Dados"].items():
        for e in entradas:
            info = mapa_geocod.get(e["geocod"])
            if info is None:
                logger.warning("geocod desconhecido (fora do mapa): %s (%s)", e["geocod"], e.get("geodsg"))
                continue
            linhas.append(
                {
                    "ano": int(ano),
                    "geocod": e["geocod"],
                    "regiao": info["regiao"],
                    "nivel": info["nivel"],
                    "quartil": e["dim_3_t"],
                    "preco_m2": float(e["valor"]) if e.get("valor") not in (None, "") else None,
                }
            )

    df = pd.DataFrame(linhas)
    df.to_csv(os.path.join(pasta_dados, "precos_regionais.csv"), index=False)
    logger.info("precos_regionais.csv atualizado: %d linhas.", len(df))
    return len(df)


def atualizar_indice_nacional(pasta_dados: str) -> int:
    """
    Índice de preços da habitação nacional, trimestral, desde 2009.
    Grava dados/indice_nacional.csv. Devolve o número de linhas gravadas.
    """
    registo = _pedir_indicador("0009201", "T")

    linhas = []
    for periodo, entradas in registo["Dados"].items():
        # "1.º Trimestre de 2009" -> trimestre=1, ano=2009
        trimestre = int(periodo[0])
        ano = int(periodo.split(" de ")[1])
        for e in entradas:
            linhas.append(
                {
                    "ano": ano,
                    "trimestre": trimestre,
                    "periodo": f"{ano}-T{trimestre}",
                    "categoria": e["dim_3_t"],
                    "indice": float(e["valor"]),
                }
            )

    df = pd.DataFrame(linhas).sort_values(["ano", "trimestre"]).reset_index(drop=True)
    df.to_csv(os.path.join(pasta_dados, "indice_nacional.csv"), index=False)
    logger.info("indice_nacional.csv atualizado: %d linhas.", len(df))
    return len(df)


def main() -> int:
    pasta_dados = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados")
    erros = []

    for nome, funcao in [
        ("preços regionais", atualizar_precos_regionais),
        ("índice nacional", atualizar_indice_nacional),
    ]:
        try:
            funcao(pasta_dados)
        except Exception as exc:  # noqa: BLE001 - uma fonte falhar não deve travar a outra
            logger.exception("Falha ao atualizar '%s'", nome)
            erros.append((nome, exc))

    if erros:
        for nome, exc in erros:
            print(f"ERRO em '{nome}': {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
