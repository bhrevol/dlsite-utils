"""Command-line interface."""
import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
from itertools import groupby
from pathlib import Path
from typing import Any, TextIO, cast
from collections.abc import Iterable

import click
import dlsite_async
from PIL import Image, ImageFile
from tqdm import tqdm

from .archive import zip_work
from .book import download as download_book
from .config import Config
from .dlst import DlstFile, DlstInfo
from .image import upscale as upscale_waifu2x
from .rename import rename as _rename
from .video import get_m3u8_urls


ImageFile.LOAD_TRUNCATED_IMAGES = True


_LOCALES = {
    "en": "en_US",
    "jp": "ja_JP",
}


pass_config = click.make_pass_decorator(Config)


@click.group()
@click.version_option()
@click.option(
    "-c",
    "--config",
    envvar="DLSITE_CONFIG",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Use the specified configuration file instead of the default config file.",
)
@click.pass_context
def cli(ctx: click.Context, config: Path | None) -> None:
    """DLsite utilities."""  # noqa: D403
    ctx.obj = Config.from_file(config)


@cli.command()
@click.option(
    "-l",
    "--list",
    "list_",
    is_flag=True,
    help="Print options set in the config in addition to the config path.",
)
@pass_config
def config(config: Config, list_: bool) -> None:
    """Print the config file location."""
    click.echo(config.path)
    if list_:
        for line in config.list():
            click.echo(line)


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
@pass_config
def rename(
    config: Config,
    path: Iterable[Path],
    language: str | None,
    force: bool,
    dry_run: bool,
) -> None:
    """Rename paths based on DLsite work information.

    Input paths should contain a DLsite work ID somewhere in the dir/file name.
    """
    locale = _LOCALES.get(language.lower()) if language else None

    async def _gather(paths: Iterable[Path], **kwargs: Any) -> None:
        async with dlsite_async.DlsiteAPI(locale=locale) as api:
            await asyncio.gather(*(_rename(api, path, **kwargs) for path in paths))

    asyncio.run(_gather(path, force=force, dry_run=dry_run, config=config))


@cli.command()
@click.option("-k", "--key", help="AES key")
@click.option("-i", "--iv", help="AES IV")
@click.option("--key-file", type=click.File(), help="YAML key file.")
@click.argument(
    "dlst_file",
    type=click.Path(exists=True, path_type=Path),
)
@pass_config
def dlst_extract(
    config: Config,
    dlst_file: Path,
    key: str | None,
    iv: str | None,
    key_file: click.File | None,
) -> None:
    """Extract images from DLST file.

    If --key or --key-file are not provided, will default to using 'keys.yml'.
    """
    biv: bytes | None = None
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


def _load_keys(fobj: TextIO) -> tuple[bytes, bytes | None]:  # pragma: no cover
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
@pass_config
def autotag(
    config: Config, file: Iterable[Path], force: bool, language: str, dry_run: bool
) -> None:
    """Tag audio files based on DLsite work."""
    from dlsite_async.work import Work
    from dlsite_utils.audio.tag import AudioTagger

    def _tag(tagger: AudioTagger, work: Work, f: Path, **kwargs) -> None:
        click.echo(f"Tagging {f} -> {work.product_id} - {work.work_name}")
        tags = tagger.tag(f, force=force, dry_run=dry_run, **kwargs)
        for k, v in tags.items():  # type: ignore[no-untyped-call]
            click.echo(f"  {k}: {v}")

    async def _run(product_id: str, files: Iterable[Path]) -> None:
        async with dlsite_async.DlsiteAPI(locale=locale) as api:
            work = await api.get_work(product_id)
            tagger = AudioTagger(work, config=config)
            sorted_, unsorted = tagger.sort_tracks(files)
            for i, f in enumerate(sorted_, 1):
                _tag(tagger, work, f, track_number=i)
            for f in unsorted:
                _tag(tagger, work, f)

    locale = _LOCALES.get(language.lower()) if language else None
    to_tag = sorted(
        ((AudioTagger.find_product_id(f), f) for f in file),
        key=lambda x: x[0],
    )
    for product_id, g in groupby(to_tag, lambda x: x[0]):
        asyncio.run(_run(product_id, (f for _, f in g)))


@cli.command()
@click.argument(
    "work_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    nargs=-1,
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Overwrite existing tar archives.",
)
@pass_config
def zip(config: Config, work_dir: Iterable[Path], force: bool) -> None:
    """Compress work directory into a zip archive.

    Archive will not be split (ZIP64 will be used if the resulting archive is >4GB in
    size). All filenames in the archive will be encoded as UTF-8.
    """
    for work_path in work_dir:
        with tqdm(unit="file") as pbar:
            try:
                zip_work(work_path, force=force, config=config, pbar=pbar)
            except FileExistsError:
                pass


@cli.command()
@click.argument(
    "product_id",
    nargs=-1,
)
@pass_config
def video_url(config: Config, product_id: Iterable[str]):
    """Output video m3u8 playlist URL(s) suitable for downloading or streaming."""
    for id_ in product_id:
        for filename, url in asyncio.run(get_m3u8_urls(id_)).items():
            click.echo(f"{filename}: {url}")


@cli.command()
@click.argument(
    "file",
    type=click.Path(exists=True, path_type=Path),
    nargs=-1,
)
def upscale(file: Iterable[Path]):
    file = list(file)
    with ProcessPoolExecutor(max_workers=2) as executor:
        for f in tqdm(
            executor.map(_upscale_one, file),
            unit="file",
            total=len(file),
            desc="Upscaling",
        ):
            pass


def _upscale_one(file: Path) -> Path:
    im = Image.open(file)
    if max(im.size) >= 2048:
        return file
    upscaled = upscale_waifu2x(im)
    upscaled.save(file)
    return file


@cli.command()
@click.argument(
    "product_id",
    nargs=-1,
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(dir_okay=True, path_type=Path),
)
@pass_config
def book(config: Config, product_id: Iterable[str], output_dir: Path | None):
    """Download book work(s) from DLsite Play."""
    for id_ in product_id:
        asyncio.run(_book_one(id_, output_dir))


async def _book_one(product_id: Iterable[str], output_dir: Path | None):
    with tqdm() as pbar:
        await download_book(product_id, output_dir=output_dir, pbar=pbar)


if __name__ == "__main__":
    cli(prog_name="dlsite")  # pragma: no cover
