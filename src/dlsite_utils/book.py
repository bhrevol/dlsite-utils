import os
from pathlib import Path
from typing import Literal

from dlsite_async import EbookSession, EpubSession, PlayAPI
from tqdm import tqdm


async def download(
    product_id: str,
    output_dir: str | Path | None = None,
    convert: Literal["jpg", "png"] | None = "jpg",
    login_id: str | None = None,
    password: str | None = None,
    pbar: tqdm | None = None,
    **kwargs,
) -> None:
    """Download the specified book work."""
    output_dir = Path(output_dir) if output_dir else Path.cwd()
    output_dir /= product_id.upper()
    async with PlayAPI(**kwargs) as play:
        await play.login(login_id=login_id, password=password)
        token = await play.download_token(product_id)
        tree = await play.ziptree(token)
        if pbar is not None:
            pbar.set_description(f"Downloading {product_id}")
            pbar.unit = "page"
            image_count = sum(playfile.type == "image" for playfile in tree.values())
            if image_count:
                pbar.total = image_count
        for filename, playfile in tree.items():
            if playfile.is_ebook:
                ebook_dir, _ = os.path.splitext(filename)
                async with EbookSession(play, tree, playfile) as ebook:
                    if pbar is not None:
                        pbar.total = ebook.page_count
                    for i in range(ebook.page_count):
                        await ebook.download_page(
                            i,
                            output_dir / ebook_dir,
                            mkdir=True,
                            force=True,
                            convert=convert,
                        )
                        pbar.update()
            elif playfile.is_epub:
                epub_dir, _ = os.path.splitext(filename)
                async with EpubSession(play, tree, playfile) as epub:
                    if pbar is not None:
                        pbar.total = epub.page_count
                    for i in range(epub.page_count):
                        await epub.download_page(
                            i,
                            output_dir / ebook_dir,
                            mkdir=True,
                            force=True,
                            descramble=True,
                        )
                        pbar.update()
            elif playfile.type == "image":
                orig_path, _ = os.path.splitext(filename)
                _, ext = os.path.splitext(playfile.optimized_name)
                await play.download_playfile(
                    token,
                    playfile,
                    output_dir / f"{orig_path}{ext}",
                    mkdir=True,
                    descramble=True,
                )
                if pbar is not None:
                    pbar.update()
