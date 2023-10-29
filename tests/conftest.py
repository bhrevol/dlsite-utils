"""Test fixtures."""
from pathlib import Path

import pytest
from dlsite_async import AgeCategory, DlsiteAPI, Work
from pytest_mock import MockerFixture


class MockDlsiteAPI(DlsiteAPI):
    """Mocked DLsite API instance."""

    work: Work


@pytest.fixture
async def dlsite_api(mocker: MockerFixture) -> MockDlsiteAPI:
    """Patch and return mocked DLsiteAPI instance."""
    test_work = Work("RJ1234", "maniax", "RG1234", "Test Work", AgeCategory.R18)
    mock = mocker.patch(
        "dlsite_async.DlsiteAPI",
        return_value=mocker.AsyncMock(DlsiteAPI),
    )
    mock.work = test_work
    mock.get_work = mocker.AsyncMock(return_value=test_work)
    return mock


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, mocker: MockerFixture) -> Path:
    """Override the default config directory."""
    mocker.patch("platformdirs.user_config_dir", return_value=str(tmp_path))
    return tmp_path
