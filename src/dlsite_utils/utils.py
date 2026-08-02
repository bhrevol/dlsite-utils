"""Misc utilities."""

import re
from dataclasses import Field, fields, replace
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, get_args

from dlsite_async import DlsiteAPI, Work
from dlsite_async.utils import fromisoformat


if TYPE_CHECKING:
    from .config import Config


def configure_work(work: Work, config: Optional["Config"]) -> Work:
    """Return a new copy of `work` with `config` applied."""
    work_name = work.work_name
    circle = work.circle
    if config:
        name_pattern: str = config.get(
            "work_name_pattern", maker_id=work.maker_id, default=""
        )
        if name_pattern:
            m = re.match(name_pattern, work_name)
            if m:
                work_name = m.group("work_name")
        circle_name_override = config.get(
            "circle_name_override", maker_id=work.maker_id, default=work.circle
        )
        if circle_name_override:
            circle = circle_name_override
    return replace(work, work_name=work_name, circle=circle)
