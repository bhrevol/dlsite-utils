"""Command-line interface."""
import asyncio
from pathlib import Path
from typing import Iterable

import click
import dlsite_async

from .rename import rename as _rename


@click.group()
@click.version_option()
def cli() -> None:
    """DLsite utilities."""  # noqa: D403


@cli.command()
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force overwriting existing paths.",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show how files would be renamed, but do not actually rename anything.",
)
@click.argument(
    "path",
    type=click.Path(exists=True, path_type=Path),
    nargs=-1,
)
def rename(path: Iterable[Path], force: bool, dry_run: bool) -> None:
    """Rename paths based on DLsite work information.

    Input paths should contain a DLsite work ID somewhere in the dir/file name.
    """

    async def _gather(paths: Iterable[Path], **kwargs: bool) -> None:
        async with dlsite_async.DlsiteAPI() as api:
            await asyncio.gather(*(_rename(api, path, **kwargs) for path in paths))

    asyncio.run(_gather(path, force=force, dry_run=dry_run))


if __name__ == "__main__":
    cli(prog_name="dlsite")  # pragma: no cover
