# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ |

## Reporting a Vulnerability

Please report security vulnerabilities by opening an issue on GitHub. Do NOT disclose the vulnerability publicly before it has been addressed.

## Known Considerations

- **Configuration trust boundary**: `pandoc.extra_args` and `--pandoc-args` are passed directly to pandoc. Pandoc's `--filter`/`--lua-filter` options can execute external programs. Only use `project.yaml` from trusted sources.
- **Mermaid rendering**: Mermaid diagrams are rendered via `mmdc` (mermaid-cli) subprocess with `shell=False`. Arguments containing batch metacharacters (`%`, `!`) are rejected on Windows when the resolved executable is a `.cmd`/`.bat` wrapper.
