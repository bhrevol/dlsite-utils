"""Rename DLsite work files and dirs."""
from aiohttp import ClientResponseError
from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

import click
import re
from dlsite_async import DlsiteAPI
from dlsite_async.exceptions import InvalidIDError
from dlsite_async.utils import find_product_id
from pathvalidate import sanitize_filename

from .utils import configure_work


if TYPE_CHECKING:
    from .config import Config


async def rename(
    api: DlsiteAPI,
    path: Path,
    force: bool = False,
    dry_run: bool = False,
    config: Optional["Config"] = None,
) -> None:
    """Rename path according to DLsite work info."""
    try:
        name = await _make_name(api, path, config)
    except InvalidIDError:  # pragma: no cover
        click.secho(f"{path} does not appear to be a DLsite work.", fg="red")
        return
    new_path = path.parent / name
    if new_path == path:
        click.echo(f"Skipping {path}")
        return
    click.echo(f"Renaming {path} to {new_path}")
    if new_path.exists() and not force:
        click.secho(f"{new_path} already exists.", fg="red")
        return
    if not dry_run:
        path.replace(new_path)


async def _make_name(
    api: DlsiteAPI, path: Path, config: Optional["Config"] = None
) -> str:
    try:
        product_id = find_product_id(str(path.name))
    except InvalidIDError:  # pragma: no cover
        raise
    try:
        work = configure_work(await api.get_work(product_id), config)
    except ClientResponseError as e:
        if e.status == 404:
            click.secho(
                f"Could not find work {product_id}, it may have been deleted", fg="red"
            )
            raise InvalidIDError from e
        raise InvalidIDError from e
    if work.circle:
        circle: str = f"[{work.circle}] "
    elif work.brand:
        circle = f"[{work.brand}] "
    elif work.author:
        # Prefer primary author over publisher/label for books
        circle = f"[{work.author[0]}] "
    else:
        circle = ""
    suffix = "".join(
        suffix for suffix in path.suffixes if re.match(r"^[.A-Za-z0-9]+$", suffix)
    )
    return cast(
        str, sanitize_filename(f"{work.product_id} - {circle}{work.work_name}{suffix}")
    )
