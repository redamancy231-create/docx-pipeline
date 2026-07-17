"""Maintainer benchmark for the Pure Python and Pandoc converters.

Provenance: GPT-5.6-Sol (via Codex CLI), 2026-07-17.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docx_pipeline import (  # noqa: E402
    __version__ as DOCX_PIPELINE_VERSION,
)
from docx_pipeline.config import (  # noqa: E402
    DocxPipelineConfig,
    get_template,
)
from docx_pipeline.converters import (  # noqa: E402
    AbstractConverter,
    PandocConverter,
    PurePythonConverter,
)

RESULTS_PATH = Path(__file__).with_name("bench_results.json")
PANDOC_UNAVAILABLE_NOTE = "Pandoc not available"
WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
FENCE = chr(96) * 3


@dataclass(frozen=True)
class DocumentSpec:
    """Description of one generated Markdown benchmark document."""

    key: str
    display: str
    target_words: int


@dataclass(frozen=True)
class BackendSpec:
    """Description of one converter backend under test."""

    key: str
    display: str
    converter_class: type[AbstractConverter]


DOCUMENT_SPECS = (
    DocumentSpec("small", "500w", 500),
    DocumentSpec("medium", "2000w", 2000),
    DocumentSpec("large", "5000w", 5000),
)

PURE_BACKEND = BackendSpec("pure", "Pure", PurePythonConverter)
PANDOC_BACKEND = BackendSpec("pandoc", "Pandoc", PandocConverter)

_FILLER_WORDS = tuple(
    (
        "reliable document conversion depends on deterministic input stable "
        "configuration careful parsing consistent styling measurable output "
        "repeatable execution practical validation and clear reporting each "
        "benchmark paragraph exercises headings sentences punctuation layout "
        "generation backend processing memory allocation file writing archive "
        "creation metadata handling and final serialization "
        "maintainers compare "
        "results across machines versions operating systems and dependency "
        "updates while representative content keeps the workload "
        "understandable "
        "portable focused neutral realistic and suitable for routine "
        "engineering "
        "checks performance changes should be investigated with profiles "
        "before "
        "optimization decisions alter production behavior or compatibility"
    ).split()
)


def count_words(markdown: str) -> int:
    """Count benchmark words consistently across generated documents."""
    return len(WORD_PATTERN.findall(markdown))


def _make_filler(word_count: int, paragraph_size: int = 80) -> str:
    """Create deterministic prose containing exactly word_count words."""
    words = [
        _FILLER_WORDS[index % len(_FILLER_WORDS)]
        for index in range(word_count)
    ]
    paragraphs = []
    for start in range(0, len(words), paragraph_size):
        paragraph = " ".join(words[start : start + paragraph_size])
        paragraphs.append(f"{paragraph}.")
    return "\n\n".join(paragraphs)


def _complete_document(prefix: str, target_words: int) -> str:
    """Extend a Markdown prefix to the requested benchmark word count."""
    remaining = target_words - count_words(prefix)
    if remaining <= 0:
        raise ValueError("Benchmark prefix already exceeds its word target")

    markdown = f"{prefix.rstrip()}\n\n{_make_filler(remaining)}\n"
    actual_words = count_words(markdown)
    if actual_words != target_words:
        raise AssertionError(
            f"Generated {actual_words} words instead of {target_words}"
        )
    return markdown


def _small_markdown() -> str:
    prefix = """# Small Benchmark Document

## Purpose

This compact document measures conversion of ordinary prose with a predictable
heading hierarchy. It intentionally avoids tables, code, lists, images, and
other specialized structures so the workload emphasizes plain paragraphs.

## Narrative

The text below provides a stable body for timing parser and document creation
work. Every run receives identical UTF-8 input and the same default styling.
"""
    return _complete_document(prefix, 500)


def _medium_markdown() -> str:
    prefix = f"""# Medium Benchmark Document

## Overview

This document adds structured Markdown to a larger prose workload. The table
and code block remain constant so measurements can be compared across runs.

## Processing Table

| Stage | Responsibility | Expected result |
| --- | --- | --- |
| Parse | Read Markdown blocks | Structured content |
| Style | Apply document settings | Consistent layout |
| Save | Serialize the package | Valid DOCX output |

## Code Sample

{FENCE}python
def median_duration(samples: list[float]) -> float:
    ordered = sorted(samples)
    midpoint = len(ordered) // 2
    return ordered[midpoint]
{FENCE}

## Benchmark Narrative

The remaining paragraphs increase the document to the medium benchmark size
while preserving deterministic content and straightforward formatting.
"""
    return _complete_document(prefix, 2000)


def _large_markdown() -> str:
    prefix = f"""# Large Benchmark Document

## Scope

This workload combines long-form prose with representative Markdown blocks.
It exercises **emphasis**, _alternate emphasis_, headings, lists, quotations,
tables, code, and a horizontal rule without relying on external resources.

> Stable benchmarks favor repeatable local inputs over network content and
> should record enough environment data to explain meaningful differences.

## Checklist

- Generate deterministic Markdown source files.
- Use isolated output and work directories.
- Warm each converter before collecting samples.
- Report the median together with minimum and maximum durations.

1. Prepare the converter configuration.
2. Convert and save the document.
3. Capture elapsed time with a monotonic high-resolution timer.
4. Summarize and persist the measurements.

## Workload Matrix

| Content type | Small | Medium | Large |
| --- | ---: | ---: | ---: |
| Plain prose | Yes | Yes | Yes |
| Headings | Yes | Yes | Yes |
| Tables and code | No | Yes | Yes |
| Mixed structures | No | Limited | Yes |

## Implementation Example

{FENCE}python
def summarize(samples: list[float]) -> dict[str, float]:
    return {{
        "minimum": min(samples),
        "maximum": max(samples),
        "median": statistics.median(samples),
    }}
{FENCE}

---

## Extended Narrative

The following deterministic paragraphs provide most of the large workload.
Their repeated vocabulary keeps document complexity stable while the mixed
blocks above exercise multiple converter paths.
"""
    return _complete_document(prefix, 5000)


def generate_markdown_files(directory: Path) -> dict[str, Path]:
    """Generate all benchmark Markdown inputs under directory."""
    directory.mkdir(parents=True, exist_ok=True)
    builders = {
        "small": _small_markdown,
        "medium": _medium_markdown,
        "large": _large_markdown,
    }
    paths: dict[str, Path] = {}

    for spec in DOCUMENT_SPECS:
        path = directory / f"{spec.key}.md"
        path.write_text(
            builders[spec.key](),
            encoding="utf-8",
            newline="\n",
        )
        paths[spec.key] = path

    return paths


def _build_config(
    source_path: Path,
    output_path: Path,
    work_dir: Path,
    pandoc_enabled: bool,
) -> DocxPipelineConfig:
    """Create an isolated default config for one conversion run."""
    data = get_template("default")
    data["project"].update(
        {
            "name": "docx-pipeline benchmark",
            "root": str(source_path.parent),
        }
    )
    data["paths"].update(
        {
            "md_source": str(source_path),
            "docx_output": str(output_path),
            "work_dir": str(work_dir),
            "reference_docx": "",
        }
    )
    data["pandoc"].update(
        {
            "enabled": pandoc_enabled,
            "extra_args": [],
            "reference_docx": "",
        }
    )
    data["mermaid"]["enabled"] = False
    data["backup"]["enabled"] = False
    return DocxPipelineConfig.from_dict(data)


def _prepare_run(
    backend: BackendSpec,
    source_path: Path,
    run_dir: Path,
) -> tuple[AbstractConverter, Path]:
    """Prepare a converter and isolated paths outside the timed section."""
    run_dir.mkdir(parents=True, exist_ok=True)
    work_dir = run_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "output.docx"
    config = _build_config(
        source_path=source_path,
        output_path=output_path,
        work_dir=work_dir,
        pandoc_enabled=backend.key == "pandoc",
    )
    return backend.converter_class(config), output_path


def _timing_summary(durations: Sequence[float]) -> dict[str, Any]:
    """Return JSON-ready timing statistics for measured runs."""
    if not durations:
        raise ValueError("At least one measured duration is required")

    return {
        "runs_seconds": [round(value, 9) for value in durations],
        "median_seconds": round(statistics.median(durations), 9),
        "min_seconds": round(min(durations), 9),
        "max_seconds": round(max(durations), 9),
    }


def benchmark_backend(
    backend: BackendSpec,
    documents: Mapping[str, Path],
    output_root: Path,
    repeat: int,
) -> dict[str, Any]:
    """Warm and measure one backend for every document size."""
    size_results: dict[str, Any] = {}

    for spec in DOCUMENT_SPECS:
        source_path = documents[spec.key]
        case_root = output_root / backend.key / spec.key

        warmup_converter, warmup_output = _prepare_run(
            backend,
            source_path,
            case_root / "warmup",
        )
        warmup_converter.save(str(warmup_output))

        durations = []
        for run_number in range(1, repeat + 1):
            converter, output_path = _prepare_run(
                backend,
                source_path,
                case_root / f"run_{run_number}",
            )
            started = time.perf_counter()
            converter.save(str(output_path))
            durations.append(time.perf_counter() - started)

        size_results[spec.display] = {
            "name": spec.key,
            "target_words": spec.target_words,
            "actual_words": count_words(
                source_path.read_text(encoding="utf-8")
            ),
            **_timing_summary(durations),
        }

    return {
        "backend": backend.display,
        "status": "completed",
        "sizes": size_results,
    }


def _selected_backends(method: str) -> tuple[BackendSpec, ...]:
    """Resolve the requested backend selection in display order."""
    if method == "pure":
        return (PURE_BACKEND,)
    if method == "pandoc":
        return (PANDOC_BACKEND,)
    return (PURE_BACKEND, PANDOC_BACKEND)


def _skipped_pandoc_result() -> dict[str, Any]:
    """Build the standard JSON entry for an unavailable Pandoc backend."""
    return {
        "backend": PANDOC_BACKEND.display,
        "status": "skipped",
        "note": PANDOC_UNAVAILABLE_NOTE,
        "sizes": {},
    }


def _format_seconds(stats: Mapping[str, Any]) -> str:
    """Format median and range for a single table cell."""
    median_value = float(stats["median_seconds"])
    minimum = float(stats["min_seconds"])
    maximum = float(stats["max_seconds"])
    return (
        f"{median_value:.3f}s "
        f"({minimum:.3f}-{maximum:.3f}s)"
    )


def format_results_table(
    backends: Sequence[BackendSpec],
    results: Mapping[str, Mapping[str, Any]],
) -> str:
    """Render benchmark results as an aligned plain-text table."""
    headers = ["Backend", *(spec.display for spec in DOCUMENT_SPECS)]
    rows = []

    for backend in backends:
        backend_result = results[backend.key]
        if backend_result["status"] == "skipped":
            cells = ["N/A" for _ in DOCUMENT_SPECS]
        else:
            sizes = backend_result["sizes"]
            cells = [
                _format_seconds(sizes[spec.display])
                for spec in DOCUMENT_SPECS
            ]
        rows.append([backend.display, *cells])

    table_rows = [headers, *rows]
    widths = [
        max(len(str(row[column])) for row in table_rows)
        for column in range(len(headers))
    ]

    def render(row: Sequence[str]) -> str:
        return " | ".join(
            str(cell).ljust(widths[index])
            for index, cell in enumerate(row)
        )

    separator = "-+-".join("-" * width for width in widths)
    return "\n".join(
        [render(headers), separator, *(render(row) for row in rows)]
    )


def _environment_info() -> dict[str, str]:
    """Collect environment metadata for the persisted result file."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "os": platform.platform(),
        "docx_pipeline_version": DOCX_PIPELINE_VERSION,
        "timestamp": timestamp.replace("+00:00", "Z"),
    }


def _positive_integer(value: str) -> int:
    """Parse a strictly positive argparse integer."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse benchmark command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark the docx-pipeline Pure Python and Pandoc backends."
        )
    )
    parser.add_argument(
        "--method",
        choices=("pure", "pandoc", "both"),
        default="both",
        help="backend to benchmark (default: both)",
    )
    parser.add_argument(
        "--repeat",
        type=_positive_integer,
        default=3,
        metavar="N",
        help="measurement runs per backend and size (default: 3)",
    )
    return parser.parse_args(argv)


def _write_results(payload: Mapping[str, Any], path: Path) -> None:
    """Write benchmark results as UTF-8 JSON without a byte-order mark."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as result_file:
        json.dump(payload, result_file, ensure_ascii=False, indent=2)
        result_file.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected benchmarks, print the table, and save JSON results."""
    args = parse_args(argv)
    backends = _selected_backends(args.method)
    notes: list[str] = []

    with tempfile.TemporaryDirectory(
        prefix="docx_pipeline_bench_"
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        documents = generate_markdown_files(temporary_root / "inputs")
        document_info = {
            spec.key: {
                "display": spec.display,
                "target_words": spec.target_words,
                "actual_words": count_words(
                    documents[spec.key].read_text(encoding="utf-8")
                ),
            }
            for spec in DOCUMENT_SPECS
        }
        results: dict[str, Any] = {}

        for backend in backends:
            if (
                backend.key == "pandoc"
                and shutil.which("pandoc") is None
            ):
                results[backend.key] = _skipped_pandoc_result()
                notes.append(PANDOC_UNAVAILABLE_NOTE)
                continue

            try:
                results[backend.key] = benchmark_backend(
                    backend=backend,
                    documents=documents,
                    output_root=temporary_root / "outputs",
                    repeat=args.repeat,
                )
            except FileNotFoundError:
                if backend.key != "pandoc":
                    raise
                results[backend.key] = _skipped_pandoc_result()
                notes.append(PANDOC_UNAVAILABLE_NOTE)

    payload = {
        "environment": _environment_info(),
        "settings": {
            "method": args.method,
            "repeat": args.repeat,
            "warmup_runs": 1,
            "timer": "time.perf_counter",
        },
        "documents": document_info,
        "results": results,
    }
    _write_results(payload, RESULTS_PATH)

    print(format_results_table(backends, results))
    for note in dict.fromkeys(notes):
        print(note)
    print(f"Results saved to {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())