"""Command-line interface."""

import asyncio
import os
import tempfile
import unicodedata
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor
from itertools import groupby
from pathlib import Path
from typing import Any, TextIO, cast

import aiohttp
import click
import dlsite_async
from bs4 import BeautifulSoup
from PIL import Image, ImageFile
from tqdm import tqdm

from .config import Config
from .play import download as download_play
from .rename import rename as _rename


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
@click.argument(
    "file",
    type=click.Path(path_type=Path),
    nargs=-1,
)
@click.option(
    "-c",
    "--cover-art",
    type=click.Path(path_type=Path),
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
    config: Config,
    file: Iterable[Path],
    cover_art: Path | None,
    force: bool,
    language: str,
    dry_run: bool,
) -> None:
    """Tag .mp3 and .m4a audio files based on DLsite work."""
    from dlsite_async.work import Work

    from dlsite_utils.audio.tag import AudioTagger

    def _tag(tagger: AudioTagger, work: Work, f: Path, **kwargs: Any) -> None:
        click.echo(f"Tagging {f} -> {work.product_id} - {work.work_name}")
        tags = tagger.tag(
            f, cover_art=cover_art, force=force, dry_run=dry_run, **kwargs
        )
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
    "product_id",
    nargs=-1,
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(dir_okay=True, path_type=Path),
)
@pass_config
def dl_play(config: Config, product_id: Iterable[str], output_dir: Path | None) -> None:
    """Download supported work(s) from DLsite Play.

    Currently supports downloading book (manga/CG) and voicecomic works, plus standalone
    (web optimized) image and audio files. If a work contains other file types they will
    not be downloaded.
    """
    for id_ in product_id:
        asyncio.run(_dl_play_one(id_, output_dir))


async def _dl_play_one(product_id: str, output_dir: Path | None) -> None:
    with tqdm() as pbar:
        await download_play(product_id, output_dir=output_dir, pbar=pbar)


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
def dl(config: Config, product_id: Iterable[str], output_dir: Path | None) -> None:
    """Download purchased work(s) from DLsite.

    Work must be downloadable as .zip (or legacy multipart .rar).
    For DLsite Play/browser only works, use dl-play instead.
    """
    asyncio.run(_dl(product_id, output_dir))


async def _dl(
    product_ids: Iterable[str], output_dir: Path | None, **kwargs: Any
) -> None:
    async with dlsite_async.PlayAPI() as play:
        await play.login()
        for id_ in product_ids:
            try:
                await _dl_one(play, id_, output_dir, **kwargs)
            except FileExistsError:
                click.echo("Skipped download for {product_id}: {e} already exists")


async def _dl_one(
    play: dlsite_async.PlayAPI,
    product_id: str,
    output_dir: Path | None,
    force: bool = False,
) -> None:
    url = "https://play.dlsite.com/api/v3/download"
    async with play.get(
        url, params={"workno": product_id}, timeout=play._DL_TIMEOUT
    ) as response:
        if response.content_disposition:
            # single zip download
            return await _dl_atomic(
                play, response, f"{product_id}.zip", output_dir, force=force
            )

        # legacy split rar download
        async def _dl_part(url: str, part: int) -> None:
            async with play.get(url, timeout=play._DL_TIMEOUT) as part_response:
                await _dl_atomic(
                    play,
                    part_response,
                    f"{product_id}.part{part}.rar",
                    output_dir,
                    force=force,
                )

        soup = BeautifulSoup(await response.text(), "lxml")
        parts = [a.get("href") for a in soup.find_all("a", class_="btn_dl split")]
        await asyncio.gather(
            *(_dl_part(str(url), i) for i, url in enumerate(parts, start=1) if url)
        )


async def _dl_atomic(
    play: dlsite_async.PlayAPI,
    response: aiohttp.ClientResponse,
    default_filename: str,
    output_dir: Path | None,
    force: bool = False,
) -> None:
    dest_dir = Path(output_dir) if output_dir else Path.cwd()
    if response.content_disposition:
        filename = response.content_disposition.filename or default_filename
    else:
        filename = default_filename
    dest = dest_dir / filename
    if not force and dest.exists():
        raise FileExistsError(str(dest))
    if not dest.parent.exists():
        dest.parent.mkdir(parents=True)
    with tempfile.NamedTemporaryFile(
        prefix=dest.name, dir=dest.parent, delete=False
    ) as temp:
        with tqdm(
            desc=f"Downloading {filename}",
            total=response.content_length,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            leave=True,
        ) as pbar:
            try:
                async for chunk in response.content.iter_chunked(play._DL_CHUNK_SIZE):
                    temp.write(chunk)
                    pbar.update(len(chunk))
            except Exception:
                temp.close()
                os.remove(temp.name)
                raise
    os.replace(temp.name, dest)


@cli.command()
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force overwriting existing paths.",
)
@click.argument(
    "voicecomic_dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path),
    nargs=-1,
)
def vc2mp4(voicecomic_dir: Iterable[Path], force: bool) -> None:
    """Convert DLsite Play voicecomic(s) to mp4 video.

    voicecomic_dir should be the path to a DLsite Play voicecomic directory downloaded
    with dl-play.

    Requires ffmpeg.
    """
    from .voicecomic import voicecomic_to_mp4

    for p in voicecomic_dir:
        try:
            dest = voicecomic_to_mp4(p, force=force)
            click.echo(f"Converted {p} -> {dest}")
        except FileExistsError as e:
            click.secho(f"Failed to convert {p}: {e}", fg="red")
