"""
Core ingestion logic for converting various input types to Markdown
and saving them to vault/raw/.
"""

import hashlib
import logging
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Type mapping for input sources
TYPE_MAPPING = {
    "pdf": "paper",
    "docx": "paper",
    "doc": "paper",
    "pptx": "paper",
    "ppt": "paper",
    "url": "paper",
    "xlsx": "experiment",
    "xls": "experiment",
    "xlsm": "experiment",
    "csv": "experiment",
    "tsv": "experiment",
    "md": "paper",
    "txt": "paper",
    "idea": "idea",
    "experiment": "experiment",
    "discussion": "discussion",
}


def detect_type_from_input(input_type: str) -> str:
    """Detect the content type from input file extension or explicit type."""
    return TYPE_MAPPING.get(input_type, "paper")


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename/directory name."""
    name = re.sub(r'[ ()\[\]&#$`!#]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    name = re.sub(r'[^\w\-\.\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', '', name)
    return name or "untitled"


def generate_output_dir(source: str, base_dir: Optional[Path] = None) -> Path:
    """
    Generate a unique output directory for mineru output.
    Uses the pattern: ~/MinerU-Skill/<name>_<hash>/
    """
    if base_dir is None:
        base_dir = Path.home() / "MinerU-Skill"

    if source.startswith(("http://", "https://")):
        name = source.rstrip("/").split("/")[-1]
    else:
        name = Path(source).stem

    name = sanitize_filename(name)
    hash_short = hashlib.md5(source.encode("utf-8")).hexdigest()[:6]

    output_dir = base_dir / f"{name}_{hash_short}"
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


def run_mineru_flash_extract(file_path: str, output_dir: Path) -> Path:
    """Run mineru flash-extract on a file."""
    output_path = output_dir / "output.md"

    cmd = [
        "mineru-open-api",
        "flash-extract",
        file_path,
        "-o", str(output_path),
    ]

    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"mineru flash-extract failed: {result.stderr}")
        raise RuntimeError(f"mineru flash-extract failed: {result.stderr}")

    if output_path.is_dir():
        md_files = list(output_path.glob("*.md"))
        if not md_files:
            raise RuntimeError(f"No .md file found in {output_path}")
        return md_files[0]

    return output_path


def run_mineru_extract(file_path: str, output_dir: Path, model: Optional[str] = None) -> Path:
    """Run mineru extract on a file (requires token)."""
    cmd = [
        "mineru-open-api",
        "extract",
        file_path,
        "-o", str(output_dir),
    ]

    if model:
        cmd.extend(["--model", model])

    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"mineru extract failed: {result.stderr}")
        raise RuntimeError(f"mineru extract failed: {result.stderr}")

    md_files = list(output_dir.glob("*.md"))
    if not md_files:
        raise RuntimeError(f"No .md file found in {output_dir}")

    return md_files[0]


def run_mineru_crawl(url: str, output_dir: Path) -> Path:
    """Run mineru crawl on a URL (requires token)."""
    output_path = output_dir / "output.md"

    cmd = [
        "mineru-open-api",
        "crawl",
        url,
        "-o", str(output_path),
    ]

    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"mineru crawl failed: {result.stderr}")
        raise RuntimeError(f"mineru crawl failed: {result.stderr}")

    if output_path.is_dir():
        md_files = list(output_path.glob("*.md"))
        if not md_files:
            raise RuntimeError(f"No .md file found in {output_path}")
        return md_files[0]

    return output_path


def add_frontmatter(md_path: Path, doc_type: str, source: str, created_date: Optional[str] = None) -> None:
    """Add YAML frontmatter to a Markdown file if it doesn't already have it."""
    content = md_path.read_text(encoding="utf-8")

    if content.startswith("---"):
        return

    if created_date is None:
        created_date = date.today().isoformat()

    frontmatter = f"""---
type: {doc_type}
source: {source}
created: {created_date}
---

"""

    md_path.write_text(frontmatter + content, encoding="utf-8")


def copy_md_with_resources(
    src_md_path: Path,
    src_dir: Optional[Path],
    dest_dir: Path,
    dest_filename: str,
) -> Path:
    """
    Copy a Markdown file and its resources to the vault/raw/ directory.
    """
    dest_md_path = dest_dir / dest_filename
    shutil.copy2(src_md_path, dest_md_path)

    if src_dir is None:
        src_dir = src_md_path.parent

    for item in src_dir.iterdir():
        if item.is_dir() and item.name in ("images", "figures", "tables", "assets"):
            dest_resource_dir = dest_dir / item.name
            dest_resource_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(item, dest_resource_dir / item.name, dirs_exist_ok=True)
            logger.info(f"Copied resource directory: {item} -> {dest_resource_dir / item.name}")

    return dest_md_path


def check_file_references(md_path: Path, raw_dir: Path) -> list[str]:
    """
    Check if all file references in a Markdown file exist.
    Returns list of missing files.
    """
    content = md_path.read_text(encoding="utf-8")
    refs = re.findall(r'\[.*?\]\((.*?)\)', content)

    missing = []
    for ref in refs:
        if ref.startswith(("http://", "https://", "mailto:")):
            continue
        ref_path = (md_path.parent / ref).resolve()
        if not ref_path.exists():
            missing.append(ref)

    return missing


def get_next_number(type_prefix: str, raw_dir: Path) -> int:
    """Get the next available number for a type prefix."""
    existing = list(raw_dir.glob(f"{type_prefix}_*.md"))

    if not existing:
        return 1

    max_num = 0
    for f in existing:
        match = re.match(rf"{type_prefix}_(\d+)", f.stem)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    return max_num + 1


def generate_filename(
    doc_type: str,
    source_path: Optional[str],
    raw_dir: Path,
    is_url_or_text: bool = False,
) -> str:
    """Generate a filename for the raw file."""
    if source_path and not is_url_or_text:
        original_name = Path(source_path).name
        if not original_name.endswith(".md"):
            original_name = Path(original_name).stem + ".md"

        dest_path = raw_dir / original_name
        if dest_path.exists():
            stem = Path(original_name).stem
            ext = Path(original_name).suffix
            counter = 1
            while (raw_dir / f"{stem}_{counter}{ext}").exists():
                counter += 1
            return f"{stem}_{counter}{ext}"

        return original_name
    else:
        num = get_next_number(doc_type, raw_dir)
        return f"{doc_type}_{num:03d}.md"


def ingest_file(
    source: str,
    raw_dir: Path,
    doc_type: Optional[str] = None,
    mineru_model: Optional[str] = None,
) -> dict:
    """
    Ingest a single file into vault/raw/.

    Args:
        source: File path or URL
        raw_dir: vault/raw/ directory
        doc_type: Content type (auto-detect if None)
        mineru_model: Model to use for mineru extract

    Returns:
        Dictionary with ingestion results
    """
    source_path = Path(source)
    is_url = source.startswith(("http://", "https://"))

    if is_url:
        input_type = "url"
    elif source_path.exists():
        input_type = source_path.suffix.lstrip(".").lower()
    else:
        raise FileNotFoundError(f"Source file not found: {source}")

    if doc_type is None:
        doc_type = detect_type_from_input(input_type)

    output_dir = generate_output_dir(source)

    try:
        # Step 1: Convert to Markdown
        if input_type in ("pdf", "docx", "doc", "pptx", "ppt"):
            # Default to extract mode, fall back to flash-extract on failure
            try:
                md_path = run_mineru_extract(str(source_path), output_dir, model=mineru_model)
            except RuntimeError:
                logger.warning("mineru extract failed, falling back to flash-extract")
                md_path = run_mineru_flash_extract(str(source_path), output_dir)

        elif input_type == "url":
            md_path = run_mineru_crawl(source, output_dir)

        elif input_type in ("md", "txt"):
            md_path = source_path

        else:
            raise ValueError(f"Unsupported input type: {input_type}")

        # Step 2: Generate destination filename
        dest_filename = generate_filename(doc_type, source, raw_dir, is_url_or_text=is_url)

        # Step 3: Copy to vault/raw/
        src_dir = md_path.parent if md_path != source_path else None
        dest_md_path = copy_md_with_resources(md_path, src_dir, raw_dir, dest_filename)

        # Step 4: Add frontmatter for non-md files
        if input_type not in ("md",):
            add_frontmatter(dest_md_path, doc_type, source)

        # Step 5: Validate references
        missing_refs = check_file_references(dest_md_path, raw_dir)

        # Step 6: Post-ingestion validation
        file_size = dest_md_path.stat().st_size
        line_count = len(dest_md_path.read_text(encoding="utf-8").splitlines())

        return {
            "status": "success",
            "dest_path": str(dest_md_path),
            "type": doc_type,
            "file_size": file_size,
            "line_count": line_count,
            "missing_references": missing_refs,
            "warnings": [],
        }

    except Exception as e:
        return {
            "status": "error",
            "source": source,
            "error": str(e),
        }
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)


def ingest_multiple(
    sources: list[str],
    raw_dir: Path,
    doc_type: Optional[str] = None,
    mineru_model: Optional[str] = None,
) -> list[dict]:
    """Ingest multiple files into vault/raw/."""
    return [
        ingest_file(
            source=source,
            raw_dir=raw_dir,
            doc_type=doc_type,
            mineru_model=mineru_model,
        )
        for source in sources
    ]
