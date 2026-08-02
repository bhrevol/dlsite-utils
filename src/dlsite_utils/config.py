"""CLI config utilities."""

import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import platformdirs

from .audio.tag import DEFAULT_FILENAME_PATTERN, DEFAULT_PARENT_PATTERN


_APP_NAME = "dlsite-utils"

_EXAMPLE_WORK_NAME_PATTERN = r"^(【[^】]*】)*(?P<work_name>[^【]*)(【.*】)?$"
_DEFAULT_CONFIG = f"""\
# dlsite-utils TOML configuration file

#######################
# Default configuration
#######################

# Default regex pattern to use when converting audio file name to audio track tags.
# Any matching regex groups will be used as the specified audio file tag.
#
# Supported regex groups:
# - title (any string)
# - track_number (integer track number)
# - track_sort (any string, see note below)
# - disc_number (integer disc number)
# - disc_subtitle (any string)
#
# When using track_sort, all matching audio files in a directory will be lexically sorted
# (in ascending order) and then assigned track numbers in that order.
# This may be useful when tagging audio works by circles which use filenames like 1-a...,
# 1-b..., 2-a..., etc.
#autotag_filename_pattern = {DEFAULT_FILENAME_PATTERN!r}

# Default regex pattern to use when converting parent directory name to audio track tags.
# Supported regex groups are the same as autotag_filename_pattern (filename level matches
# take precedence over parent directory matches).
#autotag_parent_pattern = {DEFAULT_PARENT_PATTERN!r}

# When autotag_zero_indexed_track is set to true, tag numbers converted from file names
# will be incremented by 1. This may be useful if your audio player assumes audio track
# numbers always start at 1 (and does not sort a 0 (zero) track number correctly).
#autotag_zero_indexed_track = false

######################################
# Circle/Maker specific configurations
######################################

# Circle/Maker configurations can be set by adding additional [maker.RGxxxx]
# sections to this file (where RGxxxx is the circle/maker ID.

#[maker.RG1234]

# Regex pattern to use when converting DLsite work name to album title
# (in `dlsite autotag`) and when renaming a file or directory (in `dlsite rename`).
# Pattern must contain the group `work_name` which will be used intead of the full DLsite
# work name. This may be useful if you wish to remove extraneous portions of a work title
# (such as tags or sale ads placed within  【】 braces ).
#work_name_pattern = {_EXAMPLE_WORK_NAME_PATTERN!r}

# Circle/Maker name to use for this maker (overrides current DLsite circle/maker name for
# works by this maker). This may be useful for consistency when tagging or renaming works
# by circles which have changed their name.
#circle_name_override = ''

# autotag_... settings behave the same as in the default configuration, but are only
# applied to works by this maker (and take precedence over any defaults).
#autotag_filename_pattern = {DEFAULT_FILENAME_PATTERN!r}
#autotag_parent_pattern = {DEFAULT_PARENT_PATTERN!r}
#autotag_zero_indexed_track = false
"""


class Config:
    """DLsite utils configuration."""

    def __init__(self, data: dict[str, Any], path: str | Path | None = None):
        """Construct a new config.

        Args:
            data: Config dictionary.
            path: Config path.
        """
        self._data = data
        self._path = path

    @property
    def path(self) -> str | None:
        """Return config file path."""
        if self._path is not None:
            return str(self._path)
        return None

    def get(
        self,
        option: str,
        maker_id: str | None = None,
        default: Any = None,
    ) -> Any:
        """Return the value of a configuration option.

        Args:
            option: Configuration option.
            maker_id: Maker (circle) to prefer over default config.
            default: Default value to use when option is not set.

        Returns:
            Option value.
        """
        value = self._data.get(option, default)
        if maker_id:
            maker = self._makers.get(maker_id, {})
            value = maker.get(option, value)
        return value

    def list(self) -> Iterator[str]:
        """Iterate over values in this config."""
        for k, v in self._data.items():
            if k != "maker":
                yield f"{k}: {v}"
        for maker_id, maker in self._makers.items():
            for k, v in maker.items():
                yield f"maker.{maker_id}.{k}: {v}"

    @property
    def _makers(self) -> dict[str, Any]:
        return cast(dict[str, Any], self._data.get("maker", {}))

    @classmethod
    def from_file(cls, file_path: str | Path | None = None) -> "Config":
        """Load a config from the specified file.

        Args:
            file_path: Configuration file to load.

        Returns:
            Loaded configuration.
        """
        return cls(cls._load(file_path), file_path or cls.default_config_path())

    @classmethod
    def default_config_path(cls) -> Path:
        """Return the default configuration file path."""
        return Path(platformdirs.user_config_dir(_APP_NAME)) / "config.toml"

    @classmethod
    def _load(cls, file_path: str | Path | None = None) -> dict[str, Any]:
        """Load configuration file.

        Args:
            file_path: Configuration file to load. Defaults to platform specific user
                config location. If `file_path` is specified and the file does not exist
                an exception will be raised.

        Returns:
            Config dictionary.
        """
        if file_path:
            with open(file_path, "rb") as f:
                return tomllib.load(f)
        path = cls.default_config_path()
        try:
            cls.init_default(path)
        except FileExistsError:
            pass
        with open(path, "rb") as f:
            return tomllib.load(f)

    @staticmethod
    def init_default(
        file_path: str | Path,
        make_parents: bool = True,
        force: bool = False,
    ) -> None:
        """Init the specified configuration file.

        Args:
            file_path: Configuration file to init.
            make_parents: Create parent directories if they do not already exist.
            force: Overwrite `file_path` if it already exists. If `force` is False and
                `file_path` already exists an exception will be raised.
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        if make_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if force else "x"
        with open(file_path, mode=mode, encoding="utf-8") as f:
            f.write(_DEFAULT_CONFIG)
