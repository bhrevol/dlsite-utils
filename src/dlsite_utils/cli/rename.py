"""Rename DLsite work files and dirs."""
import asyncio
from pathlib import Path
from typing import Iterable

import click
from dlsite_async.exceptions import InvalidIDError
from dlsite_async.utils import find_product_id
from pathvalidate import sanitize_filename

from ..utils import get_work


@click.command()
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

    async def _gather(paths: Iterable[Path], **kwargs):
        await asyncio.gather(*(_rename(path, **kwargs) for path in paths))

    asyncio.run(_gather(path, force=force, dry_run=dry_run))


async def _rename(path: Path, force: bool = False, dry_run: bool = False) -> None:
    try:
        name = await _make_name(path)
    except InvalidIDError:
        return
    new_path = path.parent / name
    click.echo(f"Renaming {path} to {new_path}")
    if new_path.exists() and not force:
        click.secho("{new_path} already exists.", fg="red")
        return
    if not dry_run:
        path.rename(new_path)


async def _make_name(path: Path) -> str:
    try:
        product_id = find_product_id(str(path.name))
    except InvalidIDError:
        click.secho(f"{path} does not appear to be a DLsite work.", fg="red")
        raise
    work = await get_work(product_id)
    if work.circle:
        circle: str = f"[{work.circle}] "
    elif work.brand:
        circle = f"[{work.brand}] "
    elif work.author:
        # Prefer primary author over publisher/label for books
        circle = f"[{work.author[0]}] "
    else:
        circle = ""
    suffix = "".join(path.suffixes)
    return sanitize_filename(f"{work.product_id} - {circle}{work.work_name}{suffix}")
