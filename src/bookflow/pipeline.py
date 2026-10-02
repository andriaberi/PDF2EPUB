from dataclasses import asdict

from bookflow.cli.commands import Args


def run(args: Args) -> int:
    for name, value in asdict(args).items():
        print(f"{name}: {value}")

    # TODO: read PDF -> extract lines -> build paragraphs -> write EPUB

    return 0
