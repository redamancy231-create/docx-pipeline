"""Tests for basic LaTeX-to-OMML support in PurePythonConverter."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from docx_pipeline.config.defaults import get_template
from docx_pipeline.config.schema import DocxPipelineConfig
from docx_pipeline.converters.pure_python import PurePythonConverter

OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"m": OMML_NS, "w": WORD_NS}


@pytest.fixture()
def pure_math_config(tmp_path: Path) -> DocxPipelineConfig:
    fixture_md = (
        Path(__file__).parent / "fixtures" / "pure_math_test.md"
    ).resolve()
    data = get_template("default")
    data["project"].update({"name": "Pure math test", "root": str(tmp_path)})
    data["paths"].update(
        {
            "md_source": str(fixture_md),
            "docx_output": str(tmp_path / "pure_math.docx"),
            "work_dir": str(tmp_path / "work"),
            "reference_docx": "",
        }
    )
    data["mermaid"]["enabled"] = False
    return DocxPipelineConfig.from_dict(data)


def _convert_xml(config: DocxPipelineConfig):
    document = PurePythonConverter(config).convert()
    return etree.fromstring(document._element.xml.encode("utf-8"))


def test_supported_math_structures_generate_omml(
    pure_math_config: DocxPipelineConfig,
) -> None:
    root = _convert_xml(pure_math_config)

    assert len(root.xpath("//m:oMath", namespaces=NS)) == 8
    assert len(root.xpath("//m:oMathPara", namespaces=NS)) == 1
    assert len(root.xpath("//m:f", namespaces=NS)) == 2
    assert len(root.xpath("//m:rad", namespaces=NS)) == 2
    assert len(root.xpath("//m:sSup", namespaces=NS)) == 2
    assert len(root.xpath("//m:sSub", namespaces=NS)) == 1
    assert len(root.xpath("//m:nary", namespaces=NS)) == 2

    math_text = "".join(root.xpath("//m:t/text()", namespaces=NS))
    assert "\u03b1" in math_text
    assert "\u03b2" in math_text
    assert "\u03b3" in math_text

    nary_characters = root.xpath("//m:naryPr/m:chr/@m:val", namespaces=NS)
    assert nary_characters == ["\u2211", "\u222b"]


def test_inline_and_display_math_are_inserted_at_the_right_level(
    pure_math_config: DocxPipelineConfig,
) -> None:
    root = _convert_xml(pure_math_config)

    fraction_paragraph = root.xpath(
        "//w:p[w:r/w:t[contains(., 'Inline fraction')]]", namespaces=NS
    )[0]
    child_names = [etree.QName(child).localname for child in fraction_paragraph]
    assert child_names.index("oMath") > child_names.index("r")
    assert child_names[-1] == "r"

    display_paragraphs = root.xpath("//w:p[m:oMathPara]", namespaces=NS)
    assert len(display_paragraphs) == 1
    assert display_paragraphs[0].xpath("./m:oMathPara/m:oMath", namespaces=NS)


def test_unsupported_and_code_math_remain_literal(
    pure_math_config: DocxPipelineConfig,
) -> None:
    root = _convert_xml(pure_math_config)
    word_text = "".join(root.xpath("//w:t/text()", namespaces=NS))

    assert r"$\notacommand{x}$" in word_text
    assert r"$x^{2}$" in word_text
    assert r"$\frac{code}{only}$" in word_text


def test_math_preprocessing_extracts_display_before_inline_and_skips_code(
    pure_math_config: DocxPipelineConfig,
) -> None:
    converter = PurePythonConverter(pure_math_config)
    source = (
        r"before $x^2$" + "\n\n" + r"$$\frac{a}{b}$$" + "\n"
        + r"`$inline_code$`" + "\n```text\n" + r"$fenced$" + "\n```\n"
    )

    processed, placeholders = converter._extract_math_placeholders(source)
    extracted = list(placeholders.values())

    assert extracted[0] == (r"\frac{a}{b}", True)
    assert extracted[1] == ("x^2", False)
    assert r"`$inline_code$`" in processed
    assert r"$fenced$" in processed
