"""Utilities to repack works into zip archives."""
import os
import unicodedata
import zipfile
from fnmatch import fnmatch
from pathlib import Path
from tempfile import NamedTemporaryFile
from collections.abc import Iterable, Iterator

from tqdm import tqdm

from .config import Config


DEFAULT_EXCLUDES = [
    "*.DS_Store",
    "*.bak",
    "Thumbs.db",
]

STORE_FORMATS = {
    ".flac",
    ".jpeg",
    ".jpg",
    ".mkv",
    ".mp3",
    ".mp4",
    ".m4a",
    ".ogg",
    ".png",
    ".rar",
    ".wmv",
    ".zip",
    ".exe",
    ".dll",
}


def zip_work(
    work_path: str | Path,
    archive_path: str | Path | None = None,
    force: bool = False,
    config: Config | None = None,
    pbar: tqdm | None = None,
) -> Path:
    """Archive and compress the specified work directory.

    Arguments:
        work_path: DLsite work directory.
        archive_path: Path to new zip archive. Defaults to ``<work_path>.zip``.
        force: Overwrite `archive_path` if it already exists.
        config: Optional configuration.

    Returns:
        Path to new zip archive.
    """
    work_path = Path(work_path) if isinstance(work_path, str) else work_path
    work_path = work_path.resolve()
    if archive_path:
        archive_path = (
            Path(archive_path) if isinstance(archive_path, str) else archive_path
        )
    else:
        archive_path = work_path.parent / f"{work_path.name}.zip"

    if archive_path.exists() and not force:
        raise FileExistsError
    excludes = (
        DEFAULT_EXCLUDES
        if config is None
        else config.get("archive_excludes", default=DEFAULT_EXCLUDES)
    )
    tempfile = NamedTemporaryFile(dir=archive_path.parent, delete=False)
    try:
        with zipfile.ZipFile(
            tempfile,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zf:
            files = list(_find_files(work_path, excludes=excludes))
            if pbar is not None:
                pbar.total = len(files)
                pbar.set_description(f"Archiving {work_path.name}")
            for path, arcname, compress_type in files:
                zf.write(path, arcname=arcname, compress_type=compress_type)
                if pbar is not None:
                    pbar.update()
    except BaseException:
        tempfile.close()
        os.unlink(tempfile.name)
        raise
    tempfile.close()
    os.replace(tempfile.name, archive_path)
    try:
        os.chmod(archive_path, 0o644)
    except BaseException:
        pass
    return archive_path


def _find_files(
    work_path: Path, excludes=Iterable[str]
) -> Iterator[tuple[Path, str, int | None]]:
    for root, dirs, files in work_path.walk():
        for file in files:
            arcname = (root / file).relative_to(work_path.parent)
            if not any(fnmatch(file, pattern) for pattern in excludes):
                compress_type = (
                    zipfile.ZIP_STORED
                    if arcname.suffix.lower() in STORE_FORMATS
                    else None
                )
                yield (
                    root / file,
                    unicodedata.normalize("NFC", arcname.as_posix()),
                    compress_type,
                )
