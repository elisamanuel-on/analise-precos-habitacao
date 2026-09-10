"""
Testes das funções de exportação (CSV/Excel) da app: confirmam que os dados
ficam com colunas legíveis e que o .xlsx gerado tem a formatação esperada
(cabeçalho, larguras, formato de número). Usam os CSVs reais em dados/, não
fazem pedidos à internet.

Nota: estes testes importam "app", que precisa de dash/plotly instalados
(requirements.txt) — correm no CI e localmente com "pip install -r
requirements-dev.txt", tal como o resto da suite.
"""
import io

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from app import TIPOS, _dados_exportacao, _gerar_excel


def test_dados_exportacao_tem_colunas_legiveis():
    df = _dados_exportacao("Venda", "NUTS II", 2025, "2.º quartil")
    assert list(df.columns) == ["Região", "Nível geográfico", "Ano", "Quartil", "Preço (€/m²)"]
    assert not df.empty
    assert df["Região"].is_monotonic_increasing  # ordenado alfabeticamente


def test_dados_exportacao_nao_inclui_geocod():
    df = _dados_exportacao("Venda", "Concelho", 2025, "2.º quartil")
    assert "geocod" not in df.columns


def test_dados_exportacao_arrendamento_usa_rotulo_correto():
    df = _dados_exportacao("Arrendamento", "NUTS II", 2025, "2.º quartil")
    assert "Renda (€/m²/mês)" in df.columns
    assert not df.empty


def test_gerar_excel_tem_formatacao_profissional():
    cfg = TIPOS["Venda"]
    df = _dados_exportacao("Venda", "NUTS II", 2025, "2.º quartil")
    conteudo = _gerar_excel(df, cfg["rotulo_exportacao"], cfg["formato_excel"])

    wb = load_workbook(io.BytesIO(conteudo))
    ws = wb["Dados"]

    # Cabeçalho a negrito
    assert ws["A1"].value == "Região"
    assert ws["A1"].font.bold is True

    # 1ª linha fixa e filtros automáticos
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref is not None

    # Formato de número (separador de milhares) na coluna de valores
    indice_valor = df.columns.get_loc(cfg["rotulo_exportacao"]) + 1
    assert ws.cell(row=2, column=indice_valor).number_format == cfg["formato_excel"]

    # Largura das colunas ajustada ao conteúdo (nenhuma coluna com a largura por omissão)
    for indice in range(1, len(df.columns) + 1):
        letra = get_column_letter(indice)
        assert ws.column_dimensions[letra].width is not None
