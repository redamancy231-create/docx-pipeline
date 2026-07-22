"""Convert LaTeX formulas to Word OMML through an intermediate MathML tree."""

from __future__ import annotations

from collections.abc import Callable, Sequence
import math

import latex2mathml.converter
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml.xmlchemy import BaseOxmlElement
from lxml import etree

from docx_pipeline.data.math_symbols import MATH_SYMBOLS

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_MATHML = "http://www.w3.org/1998/Math/MathML"

_NARY_OPERATORS = set("∑∏∐∫∬∭∮⋂⋃⋀⋁")
_ACCENT_CHARACTERS = {
    "^",
    "¯",
    "~",
    "→",
    "←",
    "˙",
    "¨",
    "ˇ",
    "˘",
    "˚",
    "―",
    "↔",
}
_FENCE_PAIRS = {"(": ")", "[": "]", "{": "}", "|": "|", "‖": "‖"}
_TRANSPARENT_CONTAINERS = {
    "math",
    "mrow",
    "mstyle",
    "mpadded",
    "merror",
}


class MathConversionError(ValueError):
    """Raised when LaTeX or MathML cannot be converted safely to OMML."""


Handler = Callable[[etree._Element, BaseOxmlElement, float | None], None]


def _local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def _append_math_element(parent: BaseOxmlElement, tag: str) -> BaseOxmlElement:
    element = OxmlElement(f"m:{tag}")
    parent.append(element)
    return element


def _require_arity(element: etree._Element, expected: int) -> list[etree._Element]:
    children = list(element)
    if len(children) != expected:
        raise MathConversionError(
            f"MathML {_local_name(element)} expects {expected} children, "
            f"got {len(children)}"
        )
    return children


def _normal_math_variant(element: etree._Element) -> bool:
    current: etree._Element | None = element
    while current is not None:
        if current.get("mathvariant") == "normal":
            return True
        current = current.getparent()
    return False


def _append_run(
    parent: BaseOxmlElement,
    text: str,
    font_size: float | None,
    source: etree._Element | None = None,
) -> BaseOxmlElement:
    if not text:
        raise MathConversionError("MathML token is empty")

    run = _append_math_element(parent, "r")
    if source is not None and _normal_math_variant(source):
        math_properties = _append_math_element(run, "rPr")
        style = _append_math_element(math_properties, "sty")
        style.set(qn("m:val"), "p")

    if font_size is not None:
        word_properties = OxmlElement("w:rPr")
        half_points = str(round(font_size * 2))
        size = OxmlElement("w:sz")
        size.set(qn("w:val"), half_points)
        word_properties.append(size)
        complex_size = OxmlElement("w:szCs")
        complex_size.set(qn("w:val"), half_points)
        word_properties.append(complex_size)
        run.append(word_properties)

    text_element = _append_math_element(run, "t")
    if text[0].isspace() or text[-1].isspace():
        text_element.set(qn("xml:space"), "preserve")
    text_element.text = text
    return run


def _token_text(element: etree._Element) -> str:
    text = element.text or ""
    if not text:
        raise MathConversionError(f"MathML {_local_name(element)} token is empty")
    if _local_name(element) == "mi" and text.startswith("\\") and len(text) > 1:
        command = text[1:]
        symbol = MATH_SYMBOLS.get(command)
        if symbol is None:
            raise MathConversionError(f"Unsupported LaTeX command: {text}")
        return symbol
    return text


def _handle_token(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    _append_run(parent, _token_text(element), font_size, element)


def _space_character(element: etree._Element) -> str:
    width = element.get("width")
    if not width:
        return "\u2009"
    if not width.endswith("em"):
        return " "
    try:
        em_width = float(width[:-2])
    except ValueError as exc:
        raise MathConversionError(f"Invalid MathML space width: {width}") from exc
    if em_width <= 0:
        return ""
    if em_width <= 0.2:
        return "\u2009"
    if em_width <= 0.35:
        return "\u2005"
    if em_width <= 0.6:
        return "\u2002"
    return "\u2003"


def _handle_mspace(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    character = _space_character(element)
    if character:
        _append_run(parent, character, font_size, element)


def _convert_argument(
    parent: BaseOxmlElement,
    tag: str,
    source: etree._Element,
    font_size: float | None,
) -> BaseOxmlElement:
    argument = _append_math_element(parent, tag)
    _convert_element(source, argument, font_size)
    return argument


def _handle_container(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    children = list(element)
    if not children:
        raise MathConversionError(f"MathML {_local_name(element)} container is empty")
    _convert_sequence(children, parent, font_size)


def _handle_semantics(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    children = list(element)
    if not children:
        raise MathConversionError("MathML semantics container is empty")
    # semantics 的首个子元素是可视表达式，其余 annotation 不参与 OMML。
    _convert_element(children[0], parent, font_size)


def _handle_mfrac(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    numerator, denominator = _require_arity(element, 2)
    fraction = _append_math_element(parent, "f")
    _convert_argument(fraction, "num", numerator, font_size)
    _convert_argument(fraction, "den", denominator, font_size)


def _handle_msup(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    base, superscript = _require_arity(element, 2)
    script = _append_math_element(parent, "sSup")
    _convert_argument(script, "e", base, font_size)
    _convert_argument(script, "sup", superscript, font_size)


def _handle_msub(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    base, subscript = _require_arity(element, 2)
    script = _append_math_element(parent, "sSub")
    _convert_argument(script, "e", base, font_size)
    _convert_argument(script, "sub", subscript, font_size)


def _handle_msubsup(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    base, subscript, superscript = _require_arity(element, 3)
    script = _append_math_element(parent, "sSubSup")
    _convert_argument(script, "e", base, font_size)
    _convert_argument(script, "sub", subscript, font_size)
    _convert_argument(script, "sup", superscript, font_size)


def _accent_character(element: etree._Element) -> str | None:
    if _local_name(element) != "mover":
        return None
    base, over = _require_arity(element, 2)
    del base
    character = over.text or ""
    accented = (
        element.get("accent") == "true"
        or over.get("accent") == "true"
        or character in _ACCENT_CHARACTERS
    )
    if not accented:
        return None
    if not character:
        raise MathConversionError("MathML accent character is empty")
    return character


def _handle_munder(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    base, lower = _require_arity(element, 2)
    limit = _append_math_element(parent, "limLow")
    _convert_argument(limit, "e", base, font_size)
    _convert_argument(limit, "lim", lower, font_size)


def _handle_mover(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    base, upper = _require_arity(element, 2)
    accent_character = _accent_character(element)
    if accent_character is not None:
        accent = _append_math_element(parent, "acc")
        properties = _append_math_element(accent, "accPr")
        character = _append_math_element(properties, "chr")
        character.set(qn("m:val"), accent_character)
        _convert_argument(accent, "e", base, font_size)
        return

    limit = _append_math_element(parent, "limUpp")
    _convert_argument(limit, "e", base, font_size)
    _convert_argument(limit, "lim", upper, font_size)


def _handle_munderover(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    base, lower, upper = _require_arity(element, 3)
    upper_limit = _append_math_element(parent, "limUpp")
    upper_base = _append_math_element(upper_limit, "e")
    lower_limit = _append_math_element(upper_base, "limLow")
    _convert_argument(lower_limit, "e", base, font_size)
    _convert_argument(lower_limit, "lim", lower, font_size)
    _convert_argument(upper_limit, "lim", upper, font_size)


def _handle_msqrt(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    children = list(element)
    if not children:
        raise MathConversionError("MathML msqrt container is empty")
    radical = _append_math_element(parent, "rad")
    properties = _append_math_element(radical, "radPr")
    hidden_degree = _append_math_element(properties, "degHide")
    hidden_degree.set(qn("m:val"), "1")
    _append_math_element(radical, "deg")
    radicand = _append_math_element(radical, "e")
    _convert_sequence(children, radicand, font_size)


def _handle_mroot(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    radicand, degree = _require_arity(element, 2)
    radical = _append_math_element(parent, "rad")
    _convert_argument(radical, "deg", degree, font_size)
    _convert_argument(radical, "e", radicand, font_size)


def _append_delimiter(
    parent: BaseOxmlElement,
    opening: str,
    closing: str,
    children: Sequence[etree._Element],
    font_size: float | None,
) -> None:
    delimiter = _append_math_element(parent, "d")
    properties = _append_math_element(delimiter, "dPr")
    begin = _append_math_element(properties, "begChr")
    begin.set(qn("m:val"), opening)
    end = _append_math_element(properties, "endChr")
    end.set(qn("m:val"), closing)
    expression = _append_math_element(delimiter, "e")
    if children:
        _convert_sequence(children, expression, font_size)
    else:
        _append_run(expression, "\u200b", font_size)


def _handle_mfenced(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    children = list(element)
    delimiter = _append_math_element(parent, "d")
    properties = _append_math_element(delimiter, "dPr")
    begin = _append_math_element(properties, "begChr")
    begin.set(qn("m:val"), element.get("open", "("))
    end = _append_math_element(properties, "endChr")
    end.set(qn("m:val"), element.get("close", ")"))
    separators = element.get("separators", ",")
    if separators:
        separator = _append_math_element(properties, "sepChr")
        separator.set(qn("m:val"), separators[0])
    if children:
        for child in children:
            expression = _append_math_element(delimiter, "e")
            _convert_element(child, expression, font_size)
    else:
        expression = _append_math_element(delimiter, "e")
        _append_run(expression, "\u200b", font_size)


def _handle_mtd(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    cell = _append_math_element(parent, "e")
    children = list(element)
    if children:
        _convert_sequence(children, cell, font_size)
    else:
        _append_run(cell, "\u200b", font_size)


def _handle_mtr(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    row = _append_math_element(parent, "mr")
    children = list(element)
    if not children or any(_local_name(child) != "mtd" for child in children):
        raise MathConversionError("MathML mtr must contain one or more mtd cells")
    for child in children:
        _handle_mtd(child, row, font_size)


def _handle_mtable(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    matrix = _append_math_element(parent, "m")
    children = list(element)
    if not children or any(_local_name(child) != "mtr" for child in children):
        raise MathConversionError("MathML mtable must contain one or more mtr rows")
    for child in children:
        _handle_mtr(child, matrix, font_size)


def _nary_operator(element: etree._Element) -> str | None:
    name = _local_name(element)
    if name == "mo":
        text = element.text or ""
        return text if text in _NARY_OPERATORS else None
    if name in _TRANSPARENT_CONTAINERS and len(element) == 1:
        return _nary_operator(element[0])
    return None


def _nary_parts(
    element: etree._Element,
) -> tuple[str, etree._Element | None, etree._Element | None] | None:
    name = _local_name(element)
    if name == "mo":
        operator = _nary_operator(element)
        return (operator, None, None) if operator is not None else None

    expected = {
        "msub": 2,
        "msup": 2,
        "msubsup": 3,
        "munder": 2,
        "mover": 2,
        "munderover": 3,
    }.get(name)
    if expected is None:
        return None
    children = _require_arity(element, expected)
    operator = _nary_operator(children[0])
    if operator is None:
        return None
    if name in {"msub", "munder"}:
        return operator, children[1], None
    if name in {"msup", "mover"}:
        return operator, None, children[1]
    return operator, children[1], children[2]


def _append_nary_argument(
    nary: BaseOxmlElement,
    tag: str,
    source: etree._Element | None,
    font_size: float | None,
) -> None:
    argument = _append_math_element(nary, tag)
    if source is None:
        _append_run(argument, "\u200b", font_size)
    else:
        _convert_element(source, argument, font_size)


def _append_nary(
    parent: BaseOxmlElement,
    operator: str,
    lower: etree._Element | None,
    upper: etree._Element | None,
    body: Sequence[etree._Element],
    font_size: float | None,
) -> None:
    nary = _append_math_element(parent, "nary")
    properties = _append_math_element(nary, "naryPr")
    character = _append_math_element(properties, "chr")
    character.set(qn("m:val"), operator)
    location = _append_math_element(properties, "limLoc")
    location.set(qn("m:val"), "undOvr")
    sub_hidden = _append_math_element(properties, "subHide")
    sub_hidden.set(qn("m:val"), "1" if lower is None else "0")
    sup_hidden = _append_math_element(properties, "supHide")
    sup_hidden.set(qn("m:val"), "1" if upper is None else "0")
    _append_nary_argument(nary, "sub", lower, font_size)
    _append_nary_argument(nary, "sup", upper, font_size)
    expression = _append_math_element(nary, "e")
    if body:
        _convert_sequence(body, expression, font_size)
    else:
        _append_run(expression, "\u200b", font_size)


def _fence_text(element: etree._Element) -> str:
    return element.text or ""


def _is_prefix_fence(element: etree._Element) -> bool:
    return (
        _local_name(element) == "mo"
        and element.get("fence") == "true"
        and element.get("form") == "prefix"
    )


def _is_postfix_fence(element: etree._Element) -> bool:
    return (
        _local_name(element) == "mo"
        and element.get("fence") == "true"
        and element.get("form") == "postfix"
    )


def _matching_fence_index(elements: Sequence[etree._Element], start: int) -> int | None:
    opening = _fence_text(elements[start])
    expected_closing = _FENCE_PAIRS.get(opening)
    depth = 0
    for index in range(start + 1, len(elements)):
        candidate = elements[index]
        if _is_prefix_fence(candidate):
            depth += 1
            continue
        if not _is_postfix_fence(candidate):
            continue
        if depth:
            depth -= 1
            continue
        if expected_closing is None or _fence_text(candidate) == expected_closing:
            return index
    return None


def _convert_sequence(
    elements: Sequence[etree._Element],
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    index = 0
    while index < len(elements):
        element = elements[index]
        nary_parts = _nary_parts(element)
        if nary_parts is not None:
            operator, lower, upper = nary_parts
            # n-ary 运算符之后的同级表达式属于 m:e 主体。
            _append_nary(
                parent,
                operator,
                lower,
                upper,
                elements[index + 1 :],
                font_size,
            )
            return

        if _is_prefix_fence(element):
            closing_index = _matching_fence_index(elements, index)
            if closing_index is not None:
                _append_delimiter(
                    parent,
                    _fence_text(element),
                    _fence_text(elements[closing_index]),
                    elements[index + 1 : closing_index],
                    font_size,
                )
                index = closing_index + 1
                continue

        _convert_element(element, parent, font_size)
        index += 1


def _convert_element(
    element: etree._Element,
    parent: BaseOxmlElement,
    font_size: float | None,
) -> None:
    name = _local_name(element)
    handler = _HANDLERS.get(name)
    if handler is None:
        raise MathConversionError(f"Unsupported MathML element: {name}")
    handler(element, parent, font_size)


_HANDLERS: dict[str, Handler] = {
    "math": _handle_container,
    "mrow": _handle_container,
    "mstyle": _handle_container,
    "semantics": _handle_semantics,
    "mpadded": _handle_container,
    "merror": _handle_container,
    "mi": _handle_token,
    "mn": _handle_token,
    "mo": _handle_token,
    "mtext": _handle_token,
    "mspace": _handle_mspace,
    "mfrac": _handle_mfrac,
    "msup": _handle_msup,
    "msub": _handle_msub,
    "msubsup": _handle_msubsup,
    "munder": _handle_munder,
    "mover": _handle_mover,
    "munderover": _handle_munderover,
    "msqrt": _handle_msqrt,
    "mroot": _handle_mroot,
    "mfenced": _handle_mfenced,
    "mtable": _handle_mtable,
    "mtr": _handle_mtr,
    "mtd": _handle_mtd,
}


def latex_to_omml(latex: str, font_size: float | None = None) -> BaseOxmlElement:
    """Convert one LaTeX formula into an OMML m:oMath element.

    Args:
        latex: Formula contents without dollar delimiters.
        font_size: Optional Word font size in points for generated math runs.

    Returns:
        A python-docx XML element whose root is m:oMath.

    Raises:
        MathConversionError: If LaTeX conversion, MathML parsing, or an element
            mapping fails.
    """
    if not isinstance(latex, str) or not latex.strip():
        raise MathConversionError("LaTeX formula is empty")
    if font_size is not None:
        try:
            font_size = float(font_size)
        except (TypeError, ValueError) as exc:
            raise MathConversionError("Font size must be a positive number") from exc
        if not math.isfinite(font_size) or font_size <= 0:
            raise MathConversionError("Font size must be a positive number")

    try:
        mathml = latex2mathml.converter.convert(latex)
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        root = etree.fromstring(mathml.encode("utf-8"), parser=parser)
        root_name = etree.QName(root)
        if root_name.namespace != _MATHML or root_name.localname != "math":
            raise MathConversionError("latex2mathml returned an invalid MathML root")

        omath = OxmlElement("m:oMath")
        _convert_element(root, omath, font_size)
        if len(omath) == 0:
            raise MathConversionError("MathML formula produced no OMML content")
        return omath
    except MathConversionError:
        raise
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        raise MathConversionError(message) from exc


def wrap_omath_para(omath: BaseOxmlElement) -> BaseOxmlElement:
    """Wrap an m:oMath element in an m:oMathPara display container.

    Args:
        omath: OMML formula returned by latex_to_omml.

    Returns:
        An m:oMathPara element containing the supplied formula.

    Raises:
        MathConversionError: If omath is not an m:oMath element.
    """
    name = etree.QName(omath)
    if name.namespace != M or name.localname != "oMath":
        raise MathConversionError("Expected an m:oMath element")
    paragraph = OxmlElement("m:oMathPara")
    paragraph.append(omath)
    return paragraph


__all__ = ["M", "W", "MathConversionError", "latex_to_omml", "wrap_omath_para"]
