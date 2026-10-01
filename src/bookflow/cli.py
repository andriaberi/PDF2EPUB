import argparse
from collections.abc import Sequence

from bookflow import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bookflow",
        description="Convert PDF books into well-structured, reflowable EPUBs.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    print("Hello, world!")
    return 0
