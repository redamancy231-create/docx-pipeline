"""Programmatic API for DOCX Pipeline."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from docx_pipeline.config import DocxPipelineConfig, load_config, validate_config
from docx_pipeline.converters import PandocConverter, PurePythonConverter


class DocxPipelineError(RuntimeError):
    """Raised when configuration loading, validation, or conversion fails."""


class DocxPipeline:
    """Programmatic API for DOCX Pipeline."""

    def __init__(self, cfg: DocxPipelineConfig) -> None:
        self.cfg = cfg

    @classmethod
    def from_config(cls, config_path: str) -> "DocxPipeline":
        """Create from a project.yaml file."""
        try:
            cfg = load_config(config_path)
        except Exception as exc:
            raise DocxPipelineError(
                f"Failed to load configuration '{config_path}': {exc}"
            ) from exc

        try:
            issues = validate_config(cfg)
        except Exception as exc:
            raise DocxPipelineError(
                f"Failed to validate configuration '{config_path}': {exc}"
            ) from exc

        if issues:
            details = "\n".join(f"- {issue}" for issue in issues)
            raise DocxPipelineError(
                f"Configuration validation failed for '{config_path}':\n{details}"
            )

        return cls(cfg)

    def convert(self, method: str = "auto", output: str | None = None) -> str:
        """Execute conversion. Returns path to generated .docx."""
        if method not in ("pure", "pandoc", "auto"):
            raise DocxPipelineError(
                "Invalid conversion method "
                f"'{method}'. Expected one of: pure, pandoc, auto."
            )

        resolved_output = output if output is not None else self.cfg.paths.docx_output
        if not resolved_output:
            raise DocxPipelineError(
                "No output path was provided. Pass output=... or set "
                "paths.docx_output in the configuration."
            )

        pandoc_available = shutil.which("pandoc") is not None
        if method == "pandoc":
            if not pandoc_available:
                raise DocxPipelineError(
                    "The pandoc conversion method requires pandoc, but it was "
                    "not found on PATH. Install pandoc or use method='pure'."
                )
            effective_method = "pandoc"
        elif method == "auto":
            effective_method = (
                "pandoc"
                if self.cfg.pandoc.enabled and pandoc_available
                else "pure"
            )
        else:
            effective_method = "pure"

        try:
            if effective_method == "pandoc":
                converter = PandocConverter(self.cfg)
            else:
                converter = PurePythonConverter(self.cfg)
            saved_path = converter.save(str(resolved_output))
            return str(Path(saved_path).resolve())
        except Exception as exc:
            raise DocxPipelineError(
                f"Conversion failed using method '{effective_method}': {exc}"
            ) from exc

    def convert_to_bytes(self) -> bytes:
        """Execute conversion and return DOCX as bytes (for web services)."""
        try:
            with tempfile.TemporaryDirectory(prefix="docx_pipeline_") as temp_dir:
                temp_output = Path(temp_dir) / "output.docx"
                generated_path = Path(self.convert(output=str(temp_output)))
                return generated_path.read_bytes()
        except DocxPipelineError:
            raise
        except Exception as exc:
            raise DocxPipelineError(
                f"Failed to convert DOCX to bytes: {exc}"
            ) from exc


__all__ = ["DocxPipeline", "DocxPipelineError"]
