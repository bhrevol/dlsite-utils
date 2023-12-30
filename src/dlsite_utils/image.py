"""Image utilities."""
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from PIL import Image


def _find_waifu2x() -> Path:
    waifu2x = shutil.which("waifu2x-ncnn-vulkan")
    if not waifu2x:
        raise FileNotFoundError
    return Path(waifu2x).resolve()


def upscale(im: Image, scale: int=2) -> Image:
    """Upscale an image using waifu2x.

    If waifu2x is not available in PATH the original image will be returned.
    """
    try:
        waifu2x = _find_waifu2x()
    except FileNotFoundError:
        return im
    with TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src.png")
        dst = os.path.join(tmpdir, "dst.png")
        im.save(src, format="PNG")
        try:
            subprocess.run(
                [
                    str(waifu2x),
                    "-i",
                    src,
                    "-o",
                    dst,
                    "-m",
                    str(waifu2x.parent / "models-cunet"),
                    "-n",
                    "1",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print("upscaling failed:", exc)
            return im
        upscaled = Image.open(dst)
        upscaled.load()
    return upscaled
