"""Test fixtures."""
import pytest
from dlsite_async import AgeCategory, DlsiteAPI, Work
from pytest_mock import MockerFixture


@pytest.fixture
async def dlsite_api(mocker: MockerFixture) -> DlsiteAPI:
    """Patch and return mocked DLsiteAPI instance."""
    test_work = Work("RJ1234", "maniax", "RG1234", "Test Work", AgeCategory.R18)
    mock = mocker.patch(
        "dlsite_async.DlsiteAPI",
        return_value=mocker.AsyncMock(DlsiteAPI),
    )
    mock.work = test_work
    mock.get_work = mocker.AsyncMock(return_value=test_work)
    return mock
