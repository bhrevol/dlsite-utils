"""Misc utilities."""
import re
from dataclasses import replace
from typing import TYPE_CHECKING, Optional

from dlsite_async import Work


if TYPE_CHECKING:
    from .config import Config


def configure_work(work: Work, config: Optional["Config"]) -> Work:
    """Return a new copy of `work` with `config` applied."""
    work_name = work.work_name
    if config:
        name_pattern: str = config.get(
            "work_name_pattern", maker_id=work.maker_id, default=""
        )
        if name_pattern:
            m = re.match(name_pattern, work_name)
            if m:
                work_name = m.group("work_name")
    return replace(work, work_name=work_name)
