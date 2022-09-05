"""Command-line interface."""
import click


@click.command()
@click.version_option()
def main() -> None:
    """Main DLsite Utilities."""


if __name__ == "__main__":
    main(prog_name="dlsite-utils")  # pragma: no cover
