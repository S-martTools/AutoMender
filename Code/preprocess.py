"""Compatibility entry point for one-contract semantic extraction."""
import argparse
import json
from pathlib import Path

from automender.data.semantics import extract_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    path = Path(args.src)
    value = {"path": str(path), "text": path.read_text(encoding="utf-8", errors="replace"), "semantics": extract_file(path).to_dict()}
    Path(args.out).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
