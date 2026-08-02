import os
from pathlib import Path
from typing import Literal

import click
from dlsite_async import EbookSession, EpubFixedSession, EpubReflowableSession, PlayAPI
from dlsite_async.play.models import DownloadToken, PlayFile, ZipTree
from tqdm import tqdm


async def download(
    product_id: str,
    output_dir: str | Path | None = None,
    login_id: str | None = None,
    password: str | None = None,
    pbar: tqdm | None = None,
    **kwargs,
) -> None:
    """Download the specified work from DLsite Play."""
    output_dir = Path(output_dir) if output_dir else Path.cwd()
    output_dir /= product_id.upper()
    async with PlayAPI(**kwargs) as play:
        await play.login(login_id=login_id, password=password)
        token = await play.download_token(product_id)
        tree = await play.ziptree(token)
        if pbar is not None:
            pbar.set_description(f"Downloading {product_id}")
            pbar.unit = "playfile"
            pbar.total = len(tree)
        for filename, playfile in tree.items():
            if playfile.is_ebook:
                await _download_ebook(
                    play, output_dir, token, tree, filename, playfile, pbar=pbar
                )
            elif playfile.is_epub_fixed:
                await _download_epub_fixed(
                    play, output_dir, token, tree, filename, playfile, pbar=pbar
                )
            elif playfile.is_epub_reflowable:
                await _download_epub_reflowable(
                    play, output_dir, token, tree, filename, playfile, pbar=pbar
                )
            elif playfile.type == "pdf":
                await _download_pdf(
                    play, output_dir, token, tree, filename, playfile, pbar=pbar
                )
            elif playfile.type in {"image", "audio"}:
                await _download_playfile(
                    play, output_dir, token, tree, filename, playfile, pbar=pbar
                )
            else:
                msg = f"Unsupported playfile type {playfile.type}: {filename}"
                if pbar is None:
                    click.secho(msg, color="red")
                else:
                    pbar.write(msg)
            if pbar is not None:
                pbar.update()


async def _download_ebook(
    play: PlayAPI,
    output_dir: Path,
    token: DownloadToken,
    tree: ZipTree,
    filename: str,
    playfile: PlayFile,
    pbar: tqdm | None = None,
) -> None:
    ebook_dir, name = os.path.splitext(filename)
    async with EbookSession(play, tree, playfile) as ebook:
        if pbar is None:
            it = range(ebook.page_count)
        else:
            it = tqdm(range(ebook.page_count), f"Downloading {filename}", unit="page")
        for i in it:
            paths = await ebook.download_page(
                i,
                output_dir / ebook_dir,
                mkdir=True,
                force=True,
            )
            if paths:
                for path in paths:
                    # multiple paths are image + audio
                    path.rename(path.parent / f"{i:03}{path.suffix}")


async def _download_epub_fixed(
    play: PlayAPI,
    output_dir: Path,
    token: DownloadToken,
    tree: ZipTree,
    filename: str,
    playfile: PlayFile,
    convert: Literal["jpg", "png"] | None = None,
    pbar: tqdm | None = None,
) -> None:
    epub_dir, _ = os.path.splitext(filename)
    async with EpubFixedSession(play, tree, playfile) as epub:
        if pbar is None:
            it = range(epub.page_count)
        else:
            it = tqdm(range(epub.page_count), f"Downloading {filename}", unit="page")
        for i in it:
            paths = await epub.download_page(
                i,
                output_dir / epub_dir,
                mkdir=True,
                force=True,
                descramble=True,
            )
            if paths:
                for j, path in enumerate(paths):
                    # multiple paths are multipart page
                    prefix = f"{i:03}" if len(paths) == 1 else f"{i:03}-{j}"
                    path.rename(path.parent / f"{prefix}{path.suffix}")


async def _download_epub_reflowable(
    play: PlayAPI,
    output_dir: Path,
    token: DownloadToken,
    tree: ZipTree,
    filename: str,
    playfile: PlayFile,
    pbar: tqdm | None = None,
) -> None:
    dest = output_dir / filename
    async with EpubReflowableSession(play, tree, playfile) as epub:
        dl_path = await epub.download_epub(dest.parent, mkdir=True, force=True)
        if dl_path != dest:
            dl_path.replace(dest)


async def _download_playfile(
    play: PlayAPI,
    output_dir: Path,
    token: DownloadToken,
    tree: ZipTree,
    filename: str,
    playfile: PlayFile,
    pbar: tqdm | None = None,
) -> None:
    orig_path, _ = os.path.splitext(filename)
    _, ext = os.path.splitext(playfile.optimized_name)
    await play.download_playfile(
        token,
        playfile,
        output_dir / f"{orig_path}{ext}",
        mkdir=True,
        descramble=True,
    )


async def _download_pdf(
    play: PlayAPI,
    output_dir: Path,
    token: DownloadToken,
    tree: ZipTree,
    filename: str,
    playfile: PlayFile,
    pbar: tqdm | None = None,
) -> None:
    pages = playfile.files.get("page", [])
    if pbar is None:
        it = enumerate(pages)
    else:
        it = tqdm(enumerate(pages), desc=f"Downloading {filename}", unit="page")
    for i, page in it:
        page_playfile = PlayFile(playfile.length, "image", page, "")
        orig_path, _ = os.path.splitext(filename)
        _, ext = os.path.splitext(page_playfile.optimized_name)
        await play.download_playfile(
            token,
            page_playfile,
            output_dir / orig_path / f"{i:03}{ext}",
            mkdir=True,
            descramble=True,
        )
