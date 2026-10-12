"""Compatibility entry point. See ``python -m automender validate --help``."""
import sys
from automender.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["validate"] + sys.argv[1:]))
