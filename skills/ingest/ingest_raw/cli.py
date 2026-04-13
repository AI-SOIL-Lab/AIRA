"""
CLI interface for ingest skill.

Provides a command-line interface for ingesting files into vault/raw/.
"""

import argparse
import logging
import sys
from pathlib import Path

from .core import ingest_file, ingest_multiple

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def cmd_ingest(args):
    """Handle the ingest command."""
    setup_logging(args.verbose)

    raw_dir = Path(args.vault_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    result = ingest_file(
        source=args.source,
        raw_dir=raw_dir,
        doc_type=args.type,
        mineru_model=args.mineru_model,
    )

    if result["status"] == "success":
        print(f"✅ Successfully ingested: {result['dest_path']}")
        print(f"   Type: {result['type']}")
        print(f"   Size: {result['file_size']} bytes, {result['line_count']} lines")

        if result["missing_references"]:
            print(f"   ⚠️  Missing references: {', '.join(result['missing_references'])}")
    else:
        print(f"❌ Failed to ingest: {result.get('source', args.source)}")
        print(f"   Error: {result['error']}")
        sys.exit(1)

    return result


def cmd_batch(args):
    """Handle the batch command."""
    setup_logging(args.verbose)

    raw_dir = Path(args.vault_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results = ingest_multiple(
        sources=args.sources,
        raw_dir=raw_dir,
        doc_type=args.type,
        mineru_model=args.mineru_model,
    )

    success_count = sum(1 for r in results if r["status"] == "success")
    total = len(results)
    print(f"\n{'='*60}")
    print(f"Batch ingestion complete: {success_count}/{total} succeeded")
    print(f"{'='*60}\n")

    for result in results:
        if result["status"] == "success":
            print(f"✅ {result['dest_path']}")
            print(f"   Type: {result['type']}, Size: {result['file_size']} bytes")

            if result["missing_references"]:
                print(f"   ⚠️  Missing: {', '.join(result['missing_references'])}")
        else:
            print(f"❌ {result.get('source', 'unknown')}")
            print(f"   Error: {result['error']}")
        print()

    if success_count < total:
        sys.exit(1)

    return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="aira-ingest",
        description="Ingest files into AIRA vault/raw/ directory",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a single file")
    ingest_parser.add_argument("source", help="File path or URL to ingest")
    ingest_parser.add_argument(
        "-v", "--vault-dir",
        default="./vault",
        help="Path to vault directory (default: ./vault)",
    )
    ingest_parser.add_argument(
        "-t", "--type",
        choices=["paper", "idea", "experiment", "discussion"],
        help="Content type (auto-detect if omitted)",
    )
    ingest_parser.add_argument(
        "--mineru-model",
        choices=["vlm", "pipeline", "html"],
        help="Model to use for MinerU extract",
    )
    ingest_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    ingest_parser.set_defaults(func=cmd_ingest)

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Ingest multiple files")
    batch_parser.add_argument("sources", nargs="+", help="File paths or URLs to ingest")
    batch_parser.add_argument(
        "-v", "--vault-dir",
        default="./vault",
        help="Path to vault directory (default: ./vault)",
    )
    batch_parser.add_argument(
        "-t", "--type",
        choices=["paper", "idea", "experiment", "discussion"],
        help="Content type for all files (auto-detect if omitted)",
    )
    batch_parser.add_argument(
        "--mineru-model",
        choices=["vlm", "pipeline", "html"],
        help="Model to use for MinerU extract",
    )
    batch_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    batch_parser.set_defaults(func=cmd_batch)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
