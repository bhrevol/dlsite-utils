"""CLI config utilities."""
from pathlib import Path
from typing import Any, Iterator, Optional, Union, cast

import platformdirs


try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from .audio.tag import DEFAULT_FILENAME_PATTERN, DEFAULT_PARENT_PATTERN


_APP_NAME = "dlsite-utils"

_DEFAULT_CONFIG = f"""\
# dlsite-utils TOML configuration file

#autotag_filename_pattern = {DEFAULT_FILENAME_PATTERN!r}
#autotag_parent_pattern = {DEFAULT_PARENT_PATTERN!r}
#autotag_zero_indexed_track = false

#[maker.RG1234]
#autotag_filename_pattern = {DEFAULT_FILENAME_PATTERN!r}
#autotag_parent_pattern = {DEFAULT_PARENT_PATTERN!r}
#autotag_zero_indexed_track = false
"""


class Config:
    """DLsite utils configuration."""

    def __init__(self, data: dict[str, Any], path: Optional[Union[str, Path]] = None):
        """Construct a new config.

        Args:
            data: Config dictionary.
            path: Config path.
        """
        self._data = data
        self._path = path

    @property
    def path(self) -> Optional[str]:
        """Return config file path."""
        if self._path is not None:
            return str(self._path)
        return None

    def get(
        self,
        option: str,
        maker_id: Optional[str] = None,
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
    def from_file(cls, file_path: Optional[Union[str, Path]] = None) -> "Config":
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
    def _load(cls, file_path: Optional[Union[str, Path]] = None) -> dict[str, Any]:
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
        file_path: Union[str, Path],
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
