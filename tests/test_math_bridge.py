"""Tests for the latex2mathml to OMML bridge."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from docx_pipeline.config.defaults import get_template
from docx_pipeline.config.schema import DocxPipelineConfig
from docx_pipeline.converters.mathml2omml import (
    MathConversionError,
    latex_to_omml,
    wrap_omath_para,
)
from docx_pipeline.converters.pure_python import PurePythonConverter

OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"m": OMML_NS, "w": WORD_NS}


def _xml(element):
    return etree.fromstring(etree.tostring(element, encoding="utf-8"))


def _config(tmp_path: Path, source: Path) -> DocxPipelineConfig:
    data = get_template("default")
    data["project"].update({"name": "Math bridge test", "root": str(tmp_path)})
    data["paths"].update(
        {
            "md_source": str(source),
            "docx_output": str(tmp_path / "math_bridge.docx"),
            "work_dir": str(tmp_path / "work"),
            "reference_docx": "",
        }
    )
    data["mermaid"]["enabled"] = False
    return DocxPipelineConfig.from_dict(data)


@pytest.fixture()
def pure_converter(tmp_path: Path) -> PurePythonConverter:
    source = tmp_path / "source.md"
    source.write_text("placeholder", encoding="utf-8")
    return PurePythonConverter(_config(tmp_path, source))


def test_fraction_mapping() -> None:
    root = _xml(latex_to_omml(r"\frac{a}{b}"))

    assert root.xpath("./m:f/m:num", namespaces=NS)
    assert root.xpath("./m:f/m:den", namespaces=NS)


@pytest.mark.parametrize(
    ("latex", "xpath"),
    [
        ("x^2", "./m:sSup"),
        ("x_i", "./m:sSub"),
        (r"\sum_{i=0}^n", "./m:nary[m:sub and m:sup]"),
        (r"\int_0^\infty", "./m:nary"),
        (r"\hat{x}", "./m:acc"),
    ],
)
def test_script_nary_and_accent_mappings(latex: str, xpath: str) -> None:
    root = _xml(latex_to_omml(latex))

    assert root.xpath(xpath, namespaces=NS)


def test_square_root_mapping() -> None:
    root = _xml(latex_to_omml(r"\sqrt{x}"))

    assert root.xpath("./m:rad/m:radPr/m:degHide[@m:val='1']", namespaces=NS)
    assert root.xpath("./m:rad/m:e", namespaces=NS)


def test_indexed_root_mapping() -> None:
    root = _xml(latex_to_omml(r"\sqrt[n]{x}"))

    assert root.xpath("./m:rad/m:deg", namespaces=NS)
    assert root.xpath("./m:rad/m:e", namespaces=NS)


def test_display_wrapper() -> None:
    root = _xml(wrap_omath_para(latex_to_omml(r"\frac{a}{b}")))

    assert etree.QName(root).localname == "oMathPara"
    assert root.xpath("./m:oMath/m:f", namespaces=NS)


@pytest.mark.parametrize("latex", [r"\notacommand{x}", r"\frac{a}", "x^^2"])
def test_pure_converter_falls_back_for_unsupported_math(
    pure_converter: PurePythonConverter, latex: str
) -> None:
    assert pure_converter._latex_to_omml(latex) is None


def test_public_bridge_raises_for_unsupported_math() -> None:
    with pytest.raises(MathConversionError):
        latex_to_omml(r"\notacommand{x}")


def test_empty_formula_is_rejected() -> None:
    with pytest.raises(MathConversionError, match="empty"):
        latex_to_omml("   ")


def test_nested_fraction_mapping() -> None:
    root = _xml(latex_to_omml(r"\frac{1}{\frac{a}{b}}"))

    assert len(root.xpath(".//m:f", namespaces=NS)) == 2


def test_unicode_formula_is_preserved() -> None:
    root = _xml(latex_to_omml("α + β"))
    text = "".join(root.xpath(".//m:t/text()", namespaces=NS))

    assert "α" in text
    assert "β" in text


def test_matrix_and_paired_fence_mappings() -> None:
    matrix = _xml(latex_to_omml(r"\begin{matrix}a&b\\c&d\end{matrix}"))
    fenced = _xml(latex_to_omml(r"\left( x \right)"))

    assert len(matrix.xpath("./m:m/m:mr", namespaces=NS)) == 2
    assert len(matrix.xpath("./m:m/m:mr/m:e", namespaces=NS)) == 4
    assert fenced.xpath("./m:d/m:dPr/m:begChr[@m:val='(']", namespaces=NS)
    assert fenced.xpath("./m:d/m:dPr/m:endChr[@m:val=')']", namespaces=NS)


def test_font_size_is_written_in_half_points() -> None:
    root = _xml(latex_to_omml("x", font_size=10.5))

    assert root.xpath(".//w:sz/@w:val", namespaces=NS) == ["21"]
    assert root.xpath(".//w:szCs/@w:val", namespaces=NS) == ["21"]


def test_normal_variant_and_preserved_space(monkeypatch: pytest.MonkeyPatch) -> None:
    mathml = (
        '<math xmlns="http://www.w3.org/1998/Math/MathML">'
        '<mstyle mathvariant="normal"><mtext> x </mtext></mstyle>'
        "</math>"
    )
    monkeypatch.setattr(
        "docx_pipeline.converters.mathml2omml.latex2mathml.converter.convert",
        lambda latex: mathml,
    )

    root = _xml(latex_to_omml("ignored"))

    assert root.xpath(".//m:rPr/m:sty[@m:val='p']", namespaces=NS)
    assert root.xpath(".//m:t[@xml:space='preserve']", namespaces=NS)


def test_unknown_mathml_element_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mathml = (
        '<math xmlns="http://www.w3.org/1998/Math/MathML">'
        "<menclose><mi>x</mi></menclose>"
        "</math>"
    )
    monkeypatch.setattr(
        "docx_pipeline.converters.mathml2omml.latex2mathml.converter.convert",
        lambda latex: mathml,
    )

    with pytest.raises(MathConversionError, match="menclose"):
        latex_to_omml("ignored")


def test_full_pure_python_pipeline_inserts_omml(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "Inline equation: $\\frac{a}{b}$ and $x^2$.",
        encoding="utf-8",
    )
    document = PurePythonConverter(_config(tmp_path, source)).convert()
    root = etree.fromstring(document._element.xml.encode("utf-8"))

    assert root.xpath("//m:oMath/m:f", namespaces=NS)
    assert root.xpath("//m:oMath/m:sSup", namespaces=NS)
