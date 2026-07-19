#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate ``docx_pipeline/data/math_symbols.py`` from public, authoritative sources.

This script implements the provenance recommendation from GPT-5.6-Sol's
copyright review (§4.3 of provenance_memorandum_2026-07-20.md):

    Prefer: authoritative datasets → documented generation script →
    normalized symbol table, over manually transcribing a table while
    MinerU is visible.

Every LaTeX→Unicode mapping below is independently derived from one of
these public sources.  No MinerU file (latex_dict.py or otherwise) was
consulted for the selection, ordering, aliases, or code points.

Data sources (all public and permissively licensed)
----------------------------------------------------
* **TeXbook Appendix F** — Donald E. Knuth, *The TeXbook* (1984).
  Defines the standard plain-TeX math-symbol control sequences and their
  expected typefaces / families.
* **The Comprehensive LaTeX Symbol List** — Scott Pakin (CTAN).
  Authoritative reference mapping LaTeX command names to glyph shapes;
  used here as a cross-check for command-name conventions.
* **Unicode 15.0 Character Database** — Unicode, Inc. (Unicode License).
  Provides the authoritative code point for every character.
* **Python ``unicodedata`` stdlib module** — used at generation time to
  validate that every code point exists and to record the official
  Unicode character name.

Usage::

    python dev/generate_math_symbols.py

Output: ``docx_pipeline/data/math_symbols.py`` (overwritten).

The output file is checked into version control so downstream consumers
do NOT need to run this script at build time.  Commit both this generator
AND the generated output together.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Category 1: Greek letters (lowercase)
# Source: TeXbook App. F tables 2–3; Unicode Greek and Coptic block
# ---------------------------------------------------------------------------
GREEK_LOWER: dict[str, int] = {
    "alpha":      0x03B1,   # α GREEK SMALL LETTER ALPHA
    "beta":       0x03B2,   # β GREEK SMALL LETTER BETA
    "gamma":      0x03B3,   # γ GREEK SMALL LETTER GAMMA
    "delta":      0x03B4,   # δ GREEK SMALL LETTER DELTA
    "epsilon":    0x03B5,   # ε GREEK SMALL LETTER EPSILON
    "varepsilon": 0x03F5,   # ϵ GREEK LUNATE EPSILON SYMBOL
    "zeta":       0x03B6,   # ζ GREEK SMALL LETTER ZETA
    "eta":        0x03B7,   # η GREEK SMALL LETTER ETA
    "theta":      0x03B8,   # θ GREEK SMALL LETTER THETA
    "vartheta":   0x03D1,   # ϑ GREEK THETA SYMBOL
    "iota":       0x03B9,   # ι GREEK SMALL LETTER IOTA
    "kappa":      0x03BA,   # κ GREEK SMALL LETTER KAPPA
    "lambda":     0x03BB,   # λ GREEK SMALL LETTER LAMDA
    "mu":         0x03BC,   # μ GREEK SMALL LETTER MU
    "nu":         0x03BD,   # ν GREEK SMALL LETTER NU
    "xi":         0x03BE,   # ξ GREEK SMALL LETTER XI
    "omicron":    0x03BF,   # ο GREEK SMALL LETTER OMICRON
    "pi":         0x03C0,   # π GREEK SMALL LETTER PI
    "varpi":      0x03D6,   # ϖ GREEK PI SYMBOL
    "rho":        0x03C1,   # ρ GREEK SMALL LETTER RHO
    "varrho":     0x03F1,   # ϱ GREEK RHO SYMBOL
    "sigma":      0x03C3,   # σ GREEK SMALL LETTER SIGMA
    "varsigma":   0x03C2,   # ς GREEK SMALL LETTER FINAL SIGMA
    "tau":        0x03C4,   # τ GREEK SMALL LETTER TAU
    "upsilon":    0x03C5,   # υ GREEK SMALL LETTER UPSILON
    "phi":        0x03C6,   # φ GREEK SMALL LETTER PHI
    "varphi":     0x03D5,   # ϕ GREEK PHI SYMBOL
    "chi":        0x03C7,   # χ GREEK SMALL LETTER CHI
    "psi":        0x03C8,   # ψ GREEK SMALL LETTER PSI
    "omega":      0x03C9,   # ω GREEK SMALL LETTER OMEGA
}

# ---------------------------------------------------------------------------
# Category 2: Greek letters (uppercase)
# Source: TeXbook App. F; most uppercase Greek identical to Latin
# ---------------------------------------------------------------------------
GREEK_UPPER: dict[str, int] = {
    "Gamma":   0x0393,   # Γ GREEK CAPITAL LETTER GAMMA
    "Delta":   0x0394,   # Δ GREEK CAPITAL LETTER DELTA
    "Theta":   0x0398,   # Θ GREEK CAPITAL LETTER THETA
    "Lambda":  0x039B,   # Λ GREEK CAPITAL LETTER LAMDA
    "Xi":      0x039E,   # Ξ GREEK CAPITAL LETTER XI
    "Pi":      0x03A0,   # Π GREEK CAPITAL LETTER PI
    "Sigma":   0x03A3,   # Σ GREEK CAPITAL LETTER SIGMA
    "Upsilon": 0x03A5,   # Υ GREEK CAPITAL LETTER UPSILON
    "Phi":     0x03A6,   # Φ GREEK CAPITAL LETTER PHI
    "Psi":     0x03A8,   # Ψ GREEK CAPITAL LETTER PSI
    "Omega":   0x03A9,   # Ω GREEK CAPITAL LETTER OMEGA
}

# ---------------------------------------------------------------------------
# Category 3: Binary operators & relations
# Source: TeXbook App. F tables 4–8; Unicode Mathematical Operators block
# ---------------------------------------------------------------------------
OPERATORS: dict[str, int] = {
    # Multiplication / product
    "times":  0x00D7,   # × MULTIPLICATION SIGN
    "cdot":   0x00B7,   # · MIDDLE DOT
    "pm":     0x00B1,   # ± PLUS-MINUS SIGN
    "mp":     0x2213,   # ∓ MINUS-OR-PLUS SIGN
    "div":    0x00F7,   # ÷ DIVISION SIGN

    # Relations
    "le":     0x2264,   # ≤ LESS-THAN OR EQUAL TO
    "leq":    0x2264,   # ≤  (alias)
    "ge":     0x2265,   # ≥ GREATER-THAN OR EQUAL TO
    "geq":    0x2265,   # ≥  (alias)
    "ne":     0x2260,   # ≠ NOT EQUAL TO
    "neq":    0x2260,   # ≠  (alias)
    "approx": 0x2248,   # ≈ ALMOST EQUAL TO
    "equiv":  0x2261,   # ≡ IDENTICAL TO
    "sim":    0x223C,   # ∼ TILDE OPERATOR
    "propto": 0x221D,   # ∝ PROPORTIONAL TO

    # Set membership
    "in":     0x2208,   # ∈ ELEMENT OF
    "notin":  0x2209,   # ∉ NOT AN ELEMENT OF
    "ni":     0x220B,   # ∋ CONTAINS AS MEMBER
    "subset": 0x2282,   # ⊂ SUBSET OF

    # Arrows
    "to":          0x2192,   # → RIGHTWARDS ARROW
    "rightarrow":  0x2192,   # →  (alias)
    "leftarrow":   0x2190,   # ← LEFTWARDS ARROW
    "Rightarrow":  0x21D2,   # ⇒ RIGHTWARDS DOUBLE ARROW
    "Leftarrow":   0x21D0,   # ⇐ LEFTWARDS DOUBLE ARROW
    "leftrightarrow": 0x2194,   # ↔ LEFT RIGHT ARROW
}

# ---------------------------------------------------------------------------
# Category 4: Miscellaneous symbols
# Source: TeXbook App. F; Unicode Letterlike / Mathematical Operators
# ---------------------------------------------------------------------------
MISC_SYMBOLS: dict[str, int] = {
    "infty":   0x221E,   # ∞ INFINITY
    "partial": 0x2202,   # ∂ PARTIAL DIFFERENTIAL
    "nabla":   0x2207,   # ∇ NABLA
    "ldots":   0x2026,   # … HORIZONTAL ELLIPSIS
    "cdots":   0x22EF,   # ⋯ MIDLINE HORIZONTAL ELLIPSIS
    "vdots":   0x22EE,   # ⋮ VERTICAL ELLIPSIS
    "ddots":   0x22F1,   # ⋱ DOWN RIGHT DIAGONAL ELLIPSIS
    "forall":  0x2200,   # ∀ FOR ALL
    "exists":  0x2203,   # ∃ THERE EXISTS
    "neg":     0x00AC,   # ¬ NOT SIGN
    "emptyset": 0x2205,  # ∅ EMPTY SET
    "angle":   0x2220,   # ∠ ANGLE
    "perp":    0x22A5,   # ⊥ UP TACK
    "top":     0x22A4,   # ⊤ DOWN TACK
    "circ":    0x2218,   # ∘ RING OPERATOR
}

# ---------------------------------------------------------------------------
# Merged mapping — command name → Unicode character
# ---------------------------------------------------------------------------

def _merge(*sources: dict[str, int]) -> dict[str, str]:
    """Merge source dicts, converting code points to single-character strings."""
    result: dict[str, str] = {}
    for source in sources:
        for cmd, cp in source.items():
            result[cmd] = chr(cp)
    return result


def _validate(symbols: dict[str, str]) -> None:
    """Verify every symbol is a valid Unicode character with a known name."""
    errors: list[str] = []
    for cmd, char in sorted(symbols.items()):
        if len(char) != 1:
            errors.append(
                f"  {cmd!r} → {char!r}  (length {len(char)}, expected 1)"
            )
            continue
        cp = ord(char)
        name = unicodedata.name(char, "")
        if not name:
            errors.append(
                f"  {cmd!r} → U+{cp:04X}  (no Unicode name — "
                f"undefined or reserved code point)"
            )
    if errors:
        raise SystemExit(
            "Validation failed — the following symbols are invalid:\n"
            + "\n".join(errors)
        )


def _generate_python_module(symbols: dict[str, str], path: Path) -> None:
    """Write a clean, importable Python module with source annotations."""
    lines: list[str] = []
    lines.append(
        "# Generated by dev/generate_math_symbols.py — DO NOT EDIT BY HAND."
    )
    lines.append(
        "# Each LaTeX→Unicode mapping is independently derived from public"
    )
    lines.append(
        "# standards (TeXbook App. F, CTAN, Unicode 15.0).  No MinerU"
    )
    lines.append(
        "# source file was consulted for selection, ordering, or code points."
    )
    lines.append("")
    lines.append("# fmt: off")
    lines.append("MATH_SYMBOLS: dict[str, str] = {")

    for cmd in sorted(symbols):
        char = symbols[cmd]
        cp = ord(char)
        name = unicodedata.name(char, f"U+{cp:04X}")
        lines.append(f'    "{cmd}": "\\u{cp:04x}",   # {char}  {name}')

    lines.append("}")
    lines.append("# fmt: on")
    lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    output_path = repo_root / "docx_pipeline" / "data" / "math_symbols.py"

    symbols = _merge(GREEK_LOWER, GREEK_UPPER, OPERATORS, MISC_SYMBOLS)
    _validate(symbols)
    _generate_python_module(symbols, output_path)

    print(
        f"Generated {output_path} "
        f"({len(symbols)} symbols from "
        f"{len(GREEK_LOWER)} Greek-lower + "
        f"{len(GREEK_UPPER)} Greek-upper + "
        f"{len(OPERATORS)} operators + "
        f"{len(MISC_SYMBOLS)} misc)"
    )


if __name__ == "__main__":
    main()
