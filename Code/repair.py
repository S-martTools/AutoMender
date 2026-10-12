"""Compatibility entry point. See ``python -m automender repair --help``."""
import sys
from automender.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["repair"] + sys.argv[1:]))
