"""Test cases for rename."""

from pathlib import Path
from typing import Any

import pytest
from dlsite_async import AgeCategory, Work
from dlsite_utils.rename import _make_name, rename
from pytest_mock import MockerFixture

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
            {"maker_name": "Test Circle"},
            "RJ1234 - [Test Circle] Test Work.zip",
        ),
        (
            Path("VJ1234.part2.rar"),
            {
                "product_id": "VJ1234",
                "maker_id": "VG1234",
                "maker_name": "Test Brand",
            },
            "VJ1234 - [Test Brand] Test Work.part2.rar",
        ),
        (
            Path("BJ1234"),
            {
                "product_id": "BJ1234",
                "maker_id": "BG1234",
                "maker_name": "Test Publisher",
                "author": ["Author 1", "Author 2"],
            },
            "BJ1234 - [Author 1] Test Work",
        ),
    ],
)
async def test_make_name(
    dlsite_api: MockDlsiteAPI,
    path: Path,
    work_kwargs: dict[str, Any],
    expected: str,
    mocker: MockerFixture,
) -> None:
    """Name should be based on work."""
    kwargs: dict[str, Any] = {
        "product_id": "RJ1234",
        "site_id": "maniax",
        "maker_id": "RG1234",
        "work_name": "Test Work",
        "age_category": AgeCategory.R18,
    }
    kwargs.update(work_kwargs)
    work = Work(**kwargs)
    dlsite_api.get_work = mocker.AsyncMock(  # type: ignore[method-assign]
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
