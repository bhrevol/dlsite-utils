"""DLST archive module."""
import io
import struct
import threading
from collections import defaultdict
from contextlib import AbstractContextManager
from dataclasses import dataclass
from functools import cached_property
from pathlib import PurePath
from typing import Any, BinaryIO, cast
from collections.abc import Iterator

from .crypto import CTCryptAES


def _u32(buf: bytes) -> int:
    return cast(int, struct.unpack("<I", buf[:4])[0])


def _u64(buf: bytes) -> int:
    return cast(int, struct.unpack("<Q", buf[:8])[0])


def _read_u32(fobj: BinaryIO) -> int:
    return _u32(fobj.read(4))


def _read_u64(fobj: BinaryIO) -> int:
    return _u64(fobj.read(8))


@dataclass(frozen=True)
class DlstInfo:
    """DLST archive member class."""

    name: str
    offset: int = 0
    data_size: int = 0
    chunk_size: int = 0


class DlstFile(AbstractContextManager["DlstFile"]):
    """DLST archive.

    Provides zipfile/tarfile-like interface to DLST files.

    Args:
        fobj: DLST file path or file object opened for binary reading.
        key: AES128 key used to encrypt the DLST file.
        iv: CBC IV used to encrypt the DLST file.
    """

    def __init__(
        self,
        fobj: BinaryIO | str | PurePath,
        key: bytes | None = None,
        iv: bytes | None = None,
    ):
        if isinstance(fobj, (str, PurePath)):
            fobj = open(fobj, "rb")
            self._should_close = True
        else:
            fobj.seek(0)
            self._should_close = False
        self.fobj: BinaryIO = fobj

        # ignore file config
        offset = _read_u64(fobj)
        fobj.seek(offset)
        magic = fobj.read(4)
        if magic != b"DNBE":
            raise ValueError(f"unsupported file section: {magic!r}")

        end_offset = _read_u64(fobj)
        fobj.seek(end_offset - 4)
        trailer_size = _read_u32(fobj)
        self._dir_offset = self._parse_trailer(fobj, end_offset - trailer_size)
        self._filelist = self._parse_directory()

        self._key = key
        self._iv: bytes = iv if iv else bytes([0] * 16)
        self._chunk_ivs: dict[DlstInfo, list[bytes]] = defaultdict(list)
        self._lock = threading.Lock()

    @staticmethod
    def _parse_trailer(fobj: BinaryIO, offset: int) -> int:
        fobj.seek(offset)
        magic = fobj.read(4)
        if magic != b"DNBF":
            raise ValueError(f"unsupported file trailer: {magic!r}")

        fobj.seek(12, 1)
        _read_u32(fobj)  # unused page count
        offset = _read_u32(fobj)
        return offset

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close this DLST file."""
        if self._should_close:
            with self._lock:
                self.fobj.close()

    @cached_property
    def _aes(self) -> CTCryptAES:
        if not self._key:
            raise ValueError("cannot decrypt encrypted files without AES key")
        return CTCryptAES(self._key)

    @cached_property
    def _name_info(self) -> dict[str, DlstInfo]:
        return {info.name: info for info in self._filelist}

    def _parse_directory(self) -> list[DlstInfo]:
        fobj = self.fobj
        fobj.seek(self._dir_offset)
        data = fobj.read(12)
        magic = data[:4]
        if magic != b"DNBS":
            raise ValueError(f"unsupported archive directory: {magic!r}")
        _u32(data[4:])  # unused flags
        page_count = _u32(data[8:])
        infos: list[DlstInfo] = []
        for _ in range(page_count):
            data = fobj.read(556)
            name = data[36:].decode("utf-16").rstrip("\x00")
            offset = _u64(data[20:])
            data_size = _u64(data[12:])
            file_offset, chunk_size = self._parse_entry_header(fobj, offset, data_size)
            infos.append(DlstInfo(name, file_offset, data_size, chunk_size))
        return infos

    @staticmethod
    def _parse_entry_header(
        fobj: BinaryIO, offset: int, expected_data_size: int
    ) -> tuple[int, int]:
        pos = fobj.tell()
        fobj.seek(offset)
        header = fobj.read(36)
        magic = header[:4]
        if magic != b"DNBA":
            raise ValueError(f"unsupported archive entry: {magic!r}")
        chunk_size = _u32(header[8:])
        data_size = _u32(header[24:])
        if data_size != expected_data_size:
            raise ValueError("expected data size mismatch")
        name_len = _u32(header[32:])
        data_offset = offset + 36 + name_len * 2
        fobj.seek(pos)
        return data_offset, chunk_size

    def infolist(self) -> list[DlstInfo]:
        """Return list of infos for files in this archive."""
        return self._filelist

    def namelist(self) -> list[str]:
        """Return list of string names for files in this archive."""
        return sorted(self._name_info.keys())

    def getinfo(self, name: str) -> DlstInfo:
        """Return info for the specified file name in this archive."""
        return self._name_info[name]

    def read(self, name: str | DlstInfo) -> bytes:
        """Read the bytes of the specfied file within this archive.

        Args:
            name: Name or info for the file to read.

        Returns:
            Decrypted file data.

        Raises:
            ValueError: AES key not set.
        """
        if not self._key:
            raise ValueError("cannot read encrypted files without AES key")

        if isinstance(name, DlstInfo):
            info = name
        else:
            info = self.getinfo(name)

        with self._lock:
            self.fobj.seek(info.offset)
            ciphertext = io.BytesIO(self.fobj.read(info.data_size))
        ciphertext.seek(0)
        plaintext = io.BytesIO()
        for chunk in self._decrypt_chunks(info, ciphertext):
            plaintext.write(chunk)
        return plaintext.getvalue()

    def _decrypt_chunks(
        self, info: DlstInfo, ciphertext: io.BytesIO
    ) -> Iterator[bytes]:
        chunk_size = info.chunk_size or info.data_size
        for offset in range(0, info.data_size, chunk_size):
            ciphertext.seek(offset)
            yield self._aes.decrypt(
                ciphertext.read(chunk_size),
                iv=self._chunk_iv(info, offset),
            )

    def _chunk_iv(self, info: DlstInfo, offset: int) -> bytes:
        # initial IV is re-encrypted once per chunk to allow random file access
        if offset < 0 or offset >= info.data_size:
            raise ValueError

        ivs = self._chunk_ivs[info]
        chunk_index = (offset // info.chunk_size) if info.chunk_size else 0

        last_iv = ivs[-1] if ivs else self._iv
        while len(ivs) <= chunk_index:
            last_iv = self._aes.encrypt(last_iv)
            last_iv = last_iv
            ivs.append(last_iv)

        return ivs[chunk_index]
