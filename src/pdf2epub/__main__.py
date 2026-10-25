from pdf2epub.cli.commands import parse_args
from pdf2epub.pipeline import run


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
