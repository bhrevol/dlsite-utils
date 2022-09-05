"""Test cases for rename."""
from pathlib import Path
from typing import Any, Dict

import pytest
from click.testing import CliRunner
from dlsite_async import AgeCategory, Work
from pytest_mock import MockerFixture

from dlsite_utils.cli.rename import _make_name, rename


def test_cli_succeeds(runner: CliRunner, mocker: MockerFixture) -> None:
    """It exits with a status code of zero."""
    mocker.patch("dlsite_utils.cli.rename._rename")
    result = runner.invoke(rename)
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "path, work_kwargs, expected",
    [
        (
            Path("foo - RJ1234 - bar"),
            {},
            "RJ1234 - Test Work",
        ),
        (
            Path("RJ1234.zip"),
            {"circle": "Test Circle"},
            "RJ1234 - [Test Circle] Test Work.zip",
        ),
        (
            Path("RJ1234.part2.rar"),
            {"brand": "Test Brand"},
            "RJ1234 - [Test Brand] Test Work.part2.rar",
        ),
        (
            Path("RJ1234"),
            {
                "publisher": "Test Publisher",
                "author": ["Author 1", "Author 2"],
            },
            "RJ1234 - [Author 1] Test Work",
        ),
    ],
)
async def test_make_name(
    path: Path, work_kwargs: Dict[str, Any], expected: str, mocker: MockerFixture
) -> None:
    """Name should be based on work."""
    work = Work(
        "RJ1234",
        "maniax",
        "RG1234",
        "Test Work",
        AgeCategory.R18,
        **work_kwargs,
    )
    mocker.patch("dlsite_utils.cli.rename.get_work", return_value=work)
    assert expected == await _make_name(path)
