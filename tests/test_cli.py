"""Test cases for CLI."""
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from dlsite_utils.__main__ import cli


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for invoking command-line interfaces."""
    return CliRunner()


def test_rename_succeeds(runner: CliRunner, mocker: MockerFixture) -> None:
    """It exits with a status code of zero."""
    rename = mocker.patch(
        "dlsite_utils.__main__._rename",
        mocker.AsyncMock(),
    )
    with runner.isolated_filesystem():
        with open("RJ1234.zip", "w") as f:
            f.write("")
        result = runner.invoke(cli, ["rename", "RJ1234.zip"])
    assert result.exit_code == 0
    rename.assert_called_once_with(
        mocker.ANY,
        Path("RJ1234.zip"),
        force=False,
        dry_run=False,
    )


def test_dlst_extract_succeeds(runner: CliRunner, mocker: MockerFixture) -> None:
    """Should exit with zero."""
    m = mocker.patch("dlsite_utils.__main__.DlstFile", mocker.MagicMock())
    m.infolist = mocker.Mock(return_value=[mocker.Mock()])
    with runner.isolated_filesystem():
        with open("test.dlst", "w") as f:
            f.write("")
        result = runner.invoke(
            cli,
            ["dlst-extract", "--key=abc123", "--iv=abc123", "test.dlst"],
        )
    assert result.exit_code == 0
    m.assert_called_once_with(
        Path("test.dlst"),
        bytes.fromhex("abc123"),
        bytes.fromhex("abc123"),
    )
