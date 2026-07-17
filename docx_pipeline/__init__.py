"""DOCX Pipeline — programmatic DOCX generation from Markdown + YAML config.

Dual backend (Pure Python + Pandoc), Mermaid diagram rendering, 4 preset
templates for Chinese document scenarios.
"""

__version__ = "1.0.0"
__author__ = "acerolaorion"

from .pipeline import DocxPipeline, DocxPipelineError

__all__ = [
    "DocxPipeline",
    "DocxPipelineError",
    "__version__",
    "__author__",
]
