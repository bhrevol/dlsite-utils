"""Test cases for rename."""
from pathlib import Path
from typing import Any, Dict

import pytest
from dlsite_async import AgeCategory, Work
from pytest_mock import MockerFixture

from dlsite_utils.rename import _make_name, rename

from .conftest import MockDlsiteAPI


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
    dlsite_api: MockDlsiteAPI,
    path: Path,
    work_kwargs: Dict[str, Any],
    expected: str,
    mocker: MockerFixture,
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
    dlsite_api.get_work = mocker.AsyncMock(  # type: ignore[assignment]
        return_value=work
    )
    assert expected == await _make_name(dlsite_api, path)


async def test_rename(tmp_path: Path, dlsite_api: MockDlsiteAPI) -> None:
    """Rename should succeed."""
    source = tmp_path / "RJ1234.zip"
    source.write_text("")
    await rename(dlsite_api, source)
    assert not source.exists()
    work = dlsite_api.work
    dest = tmp_path / f"{work.product_id} - {work.work_name}.zip"
    assert dest.exists()


async def test_rename_dry(tmp_path: Path, dlsite_api: MockDlsiteAPI) -> None:
    """Should not rename."""
    source = tmp_path / "RJ1234.zip"
    source.write_text("")
    await rename(dlsite_api, source, dry_run=True)
    assert source.exists()
    work = dlsite_api.work
    dest = tmp_path / f"{work.product_id} - {work.work_name}.zip"
    assert not dest.exists()


async def test_rename_force(tmp_path: Path, dlsite_api: MockDlsiteAPI) -> None:
    """Rename should succeed with force."""
    source = tmp_path / "RJ1234.zip"
    source.write_text("foo")
    work = dlsite_api.work
    dest = tmp_path / f"{work.product_id} - {work.work_name}.zip"
    dest.write_text("bar")

    await rename(dlsite_api, source)
    assert source.exists()
    assert dest.read_text() == "bar"

    await rename(dlsite_api, source, force=True)
    assert not source.exists()
    assert dest.read_text() == "foo"
