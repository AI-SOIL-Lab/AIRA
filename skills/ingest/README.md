# AIRA Ingest Skill

Unified knowledge base ingestion skill + CLI tool.

## Overview

Handles file conversion, raw file ingestion, digest generation, and index updates in one unified workflow.

## Quick Start

```bash
# Install
cd skills/ingest
uv pip install -e .

# Ingest a file
aira-ingest ingest paper.pdf

# Batch ingest
aira-ingest batch file1.pdf file2.pdf file3.pdf
```

## Documentation

See [SKILL.md](SKILL.md) for detailed usage instructions.

## License

MIT
