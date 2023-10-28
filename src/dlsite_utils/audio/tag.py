"""Audio tag module."""
import os
import re
import unicodedata
from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Iterable, NamedTuple, Optional, Tuple, Union


try:
    import mutagen
except ImportError as e:
    raise ImportError(
        "Missing dependency mutagen requires installation via dlsite-utils[mutagen]"
    ) from e

from dlsite_async import Work, WorkType
from dlsite_async.exceptions import InvalidIDError
from dlsite_async.utils import find_product_id as _find_product_id
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4, EasyMP4Tags
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3


EasyMP4Tags.RegisterTextKey("composer", "\xa9wrt")  # type: ignore[no-untyped-call]
EasyMP4Tags.RegisterFreeformKey(  # type: ignore[no-untyped-call]
    "catalognumber", "CATALOGNUMBER"
)
EasyMP4Tags.RegisterFreeformKey(  # type: ignore[no-untyped-call]
    "organization", "LABEL"
)


_TITLE_RE = re.compile(
    r"^((?P<disc_number>\d+)-|-)?([#])?(?P<track_number>\d+)([._])?(?P<title>.+)$"
)
_TITLE_PARENT_RE = re.compile(r"^(?P<disc_number>\d+).*$")


class TrackParts(NamedTuple):
    """Audio track name parts."""

    disc_number: Optional[int]
    track_number: Optional[int]
    title: str


class _EasyTag(str, Enum):
    """Mutagen Easy API tag names."""

    ALBUM = "album"
    ALBUM_ARTIST = "albumartist"
    ARTIST = "artist"
    CATALOG_NUMBER = "catalognumber"
    COMPOSER = "composer"
    DATE = "date"
    DISC_NUMBER = "discnumber"
    GENRE = "genre"
    LABEL = "organization"
    TITLE = "title"
    TRACK_NUMBER = "tracknumber"


class _VorbisTag(str, Enum):
    """Vorbis comment (FLAC) tag names."""

    ALBUM = "album"
    ALBUM_ARTIST = "albumartist"
    ARTIST = "artist"
    CATALOG_NUMBER = "catalognumber"
    COMPOSER = "composer"
    DATE = "date"
    DISC_NUMBER = "discnumber"
    GENRE = "genre"
    LABEL = "label"
    TITLE = "title"
    TRACK_NUMBER = "tracknumber"


_Tags = Union[EasyID3, EasyMP4Tags, mutagen._vorbis.VCommentDict]
_TagType = Union[type[_EasyTag], type[_VorbisTag]]


class AudioTagger:
    """Audio tagging class.

    Tags audio files based on a DLsite work. Tags are populated roughly
    according to MusicBrainz guidelines, with DLsite circle IDs stored in
    the label tag and DLsite work IDs stored in the catalog number.

    Once a file has been tagged, a reverse audio -> work lookup can be done
    using the catalog number or by label plus album title search.

    Args:
        work: DLsite work to use for tagging.
    """

    def __init__(self, work: Work):
        self.work = work

    @staticmethod
    def _tag_type(file: mutagen.FileType) -> _TagType:
        """Return tag type for the specified file."""
        if isinstance(file, FLAC):
            return _VorbisTag
        if isinstance(file, (EasyID3, EasyMP3, EasyMP4)):
            return _EasyTag
        raise ValueError("Unsupported file type.")

    @staticmethod
    def find_track_parts(file_path: Union[str, Path]) -> TrackParts:
        """Try to parse a filename into track information.

        Args:
            file_path: File to parse.

        Note:
            This method does not account for potential zero-indexed disc or
            track numbers.

        Returns:
            Tuple of (disc_number, track_number, title). Returned disc and track
            numbers may be None.
        """
        path = Path(file_path)
        filename = unicodedata.normalize("NFKC", path.stem)
        title = filename
        m = _TITLE_RE.match(filename)
        if m:
            disc = m.group("disc_number")
            track = m.group("track_number")
            disc_number: Optional[int] = int(disc, 10) if disc is not None else None
            track_number: Optional[int] = int(track, 10) if track is not None else None
        else:
            disc_number = None
            track_number = None
        if path.parent and disc_number is None:
            parent = unicodedata.normalize("NFKC", path.parent.name)
            m = _TITLE_PARENT_RE.match(parent)
            if m:
                disc = m.group("disc_number")
                disc_number = int(disc, 10) if disc is not None else None
        return TrackParts(disc_number, track_number, title)

    @staticmethod
    def find_product_id(file_path: Union[str, Path]) -> str:
        """Try to find a DLsite product ID for the specified path.

        Args:
            file_path: File path to use. If `file_path` is an audio file
                and it has a tagged DLsite catalog number, the tagged value
                will be returned. Otherwise, the full file path will be
                searched for a product ID.

        Returns:
            DLsite product ID.

        Raises:
            ValueError: No product ID was found.
        """
        try:
            f = mutagen.File(file_path, easy=True)
            if f.tags is not None:
                tag = f.tags.get(_EasyTag.CATALOG_NUMBER)
                if tag:
                    return _find_product_id(tag[0])
        except (mutagen.MutagenError, InvalidIDError):
            pass
        path = Path(os.path.abspath(file_path))
        for name in [path.name] + [parent.name for parent in reversed(path.parents)]:
            try:
                return _find_product_id(name)
            except InvalidIDError:
                pass
        raise ValueError(f"{file_path} does not appear to be a DLsite work.")

    def tag(
        self,
        file: Union[str, Path, BinaryIO],
        track_number: Optional[Union[int, Tuple[int, int]]] = None,
        disc_number: Optional[Union[int, Tuple[int, int]]] = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> _Tags:
        """Return tags for the specified audio file.

        Tags are set as follows:
            Title: Audio filename
            Album: Work name
            Album artist: Work circle/maker
            Artist: Work voice actor(s)
            Catalog number: DLsite product ID
            Composer: Work music composer(s)
            Date: Work release date
            Genre:
                If work type is Music: Soundtrack
                If work type is Voice/ASMR and ASMR in work genres: ASMR
                All other cases: Audio drama
            Record label: Work circle/maker (with appended DLsite maker ID)

        Note:
            Tags are not written back to the file.

        Args:
            file: Audio file to tag.
            track_number: Track number to use.
            disc_number: Disc number to use.
            force: Replace existing tags.
            dry_run: If True, tags will not be written back to the file.

        Returns:
            New tags.
        """
        audio_file = mutagen.File(file, easy=True)
        tag_type = self._tag_type(audio_file)
        path = Path(file if isinstance(file, (str, Path)) else file.name)
        if audio_file.tags is None and isinstance(audio_file, EasyMP3):
            tags: _Tags = EasyID3()  # type: ignore[no-untyped-call]
        else:
            tags = deepcopy(audio_file.tags)
        self._tag_album(tags, tag_type, force=force)
        self._tag_title(path, tags, tag_type, force=force)
        if track_number is not None:
            self._set_tag(tags, tag_type.TRACK_NUMBER, track_number, force=force)
        if disc_number is not None:
            self._set_tag(tags, tag_type.DISC_NUMBER, disc_number, force=force)
        if not dry_run:
            audio_file.tags = tags
            audio_file.save()
        return tags

    def _tag_album(
        self,
        tags: _Tags,
        tag_type: _TagType,
        **kwargs: Any,
    ) -> None:
        self._set_tag(tags, tag_type.ALBUM, self.work.work_name, **kwargs)
        self._set_tag(tags, tag_type.ALBUM_ARTIST, self._get_circle(), **kwargs)
        self._set_tag(
            tags,
            tag_type.ARTIST,
            (
                self._multistring(tags, self.work.voice_actor)
                if self.work.voice_actor
                else self._get_circle()
            ),
            **kwargs,
        )
        self._set_tag(tags, tag_type.CATALOG_NUMBER, self.work.product_id, **kwargs)
        if self.work.music:
            self._set_tag(
                tags,
                tag_type.COMPOSER,
                self.work.music,
                **kwargs,
            )
        if self.work.regist_date:
            self._set_tag(
                tags, tag_type.DATE, self.work.regist_date.date().isoformat(), **kwargs
            )
        self._set_tag(tags, tag_type.GENRE, self._get_genre(), **kwargs)
        self._set_tag(tags, tag_type.LABEL, self._get_label(), **kwargs)

    def _tag_title(
        self,
        path: Path,
        tags: _Tags,
        tag_type: _TagType,
        **kwargs: Any,
    ) -> None:
        _, _, title = self.find_track_parts(path)
        self._set_tag(tags, tag_type.TITLE, title, **kwargs)

    @staticmethod
    def _set_tag(tags: _Tags, key: str, value: Any, force: bool = False) -> None:
        if force or not tags.get(key):  # type: ignore[no-untyped-call]
            tags[key] = value

    def _get_circle(self) -> str:
        return (
            self.work.brand
            or self.work.publisher
            or self.work.circle
            or self.work.maker_id
        )

    @staticmethod
    def _multistring(tags: _Tags, strings: Iterable[str]) -> Union[str, list[str]]:
        if isinstance(tags, EasyMP4Tags):
            return "; ".join(strings)
        return list(strings)

    def _get_genre(self) -> str:
        if self.work.work_type == WorkType.MUSIC:
            return "Soundtrack"
        if self.work.genre and "ASMR" in self.work.genre:
            return "ASMR"
        return "Audio drama"

    def _get_label(self) -> str:
        def _make_label(s: str) -> str:
            return f"{s} [{self.work.maker_id}]"

        if self.work.label:
            return _make_label(self.work.label)
        return _make_label(self._get_circle())
