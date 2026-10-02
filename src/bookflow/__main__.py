from bookflow.cli.commands import extract_args
from bookflow.pipeline import run


def main() -> int:
    args = extract_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
