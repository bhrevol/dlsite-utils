"""Command-line interface."""
import asyncio
import os
from pathlib import Path
from typing import Iterable, Optional, TextIO, Tuple, cast

import click
import dlsite_async
from tqdm import tqdm

from .dlst import DlstFile, DlstInfo
from .rename import rename as _rename


_LOCALES = {
    "en": "en_US",
    "jp": "ja_JP",
}


@click.group()
@click.version_option()
def cli() -> None:
    """DLsite utilities."""  # noqa: D403


@cli.command()
@click.option(
    "-l",
    "--language",
    type=click.Choice(["en", "jp"], case_sensitive=False),
    default=None,
    help="Preferred metadata language.",
)
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
def rename(
    path: Iterable[Path], language: Optional[str], force: bool, dry_run: bool
) -> None:
    """Rename paths based on DLsite work information.

    Input paths should contain a DLsite work ID somewhere in the dir/file name.
    """
    locale = _LOCALES.get(language.lower()) if language else None

    async def _gather(paths: Iterable[Path], **kwargs: bool) -> None:
        async with dlsite_async.DlsiteAPI(locale=locale) as api:
            await asyncio.gather(*(_rename(api, path, **kwargs) for path in paths))

    asyncio.run(_gather(path, force=force, dry_run=dry_run))


@cli.command()
@click.option("-k", "--key", help="AES key")
@click.option("-i", "--iv", help="AES IV")
@click.option("--key-file", type=click.File(), help="YAML key file.")
@click.argument(
    "dlst_file",
    type=click.Path(exists=True, path_type=Path),
)
def dlst_extract(
    dlst_file: Path,
    key: Optional[str],
    iv: Optional[str],
    key_file: Optional[click.File],
) -> None:
    """Extract images from DLST file.

    If --key or --key-file are not provided, will default to using 'keys.yml'.
    """
    biv: Optional[bytes] = None
    if key:
        bkey = bytes.fromhex(key)
    else:  # pragma: no cover
        try:
            if key_file:
                bkey, biv = _load_keys(cast(TextIO, key_file))
            else:
                with open("keys.yml") as fobj:
                    bkey, biv = _load_keys(fobj)
        except (KeyError, FileNotFoundError):
            click.secho("No valid key file found")
            return
    if iv:  # pragma: no cover
        biv = bytes.fromhex(iv)

    with DlstFile(dlst_file, bkey, biv) as dlst:
        pbar = tqdm([info for info in dlst.infolist() if info.name != "index.bin"])
        for info in pbar:  # pragma: no cover
            _dlst_extract_one(dlst, info, dlst_file.parent / dlst_file.stem, pbar)


def _dlst_extract_one(
    dlst: DlstFile, info: DlstInfo, output_dir: Path, pbar: tqdm
) -> None:  # pragma: no cover
    if not output_dir.exists():
        os.makedirs(output_dir)
    pbar.set_description(f"Extracting {info.name}")
    data = dlst.read(info)
    with open(output_dir / info.name, "wb") as fobj:
        fobj.write(data)


def _load_keys(fobj: TextIO) -> Tuple[bytes, Optional[bytes]]:  # pragma: no cover
    from ruamel.yaml import YAML

    data = YAML().load(fobj)
    iv = data.get("iv")
    return bytes.fromhex(data["key"]), bytes.fromhex(iv) if iv else None


@cli.command()
@click.argument(
    "file",
    type=click.Path(exists=True, path_type=Path),
    nargs=-1,
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force overwriting existing tags.",
)
@click.option(
    "-l",
    "--language",
    type=click.Choice(["en", "jp"], case_sensitive=False),
    default=None,
    help="Preferred metadata language.",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show how files would be tagged, but do not actually do anything.",
)
def autotag(file: Path, force: bool, language: str, dry_run: bool) -> None:
    """Tag audio files based on DLsite work."""
    from dlsite_utils.audio.tag import AudioTagger

    async def _run(file: Path):
        file = Path(os.path.abspath(file))
        product_id = AudioTagger.find_product_id(file)
        async with dlsite_async.DlsiteAPI(locale=locale) as api:
            work = await api.get_work(product_id)
            click.echo(f"Tagging {file} -> {work.product_id} - {work.work_name}")
            tagger = AudioTagger(work)
            tags = tagger.tag(file, force=force, dry_run=dry_run)
            for k, v in tags.items():
                click.echo(f"  {k}: {v}")

    locale = _LOCALES.get(language.lower()) if language else None
    for f in file:
        asyncio.run(_run(f))


if __name__ == "__main__":
    cli(prog_name="dlsite")  # pragma: no cover
