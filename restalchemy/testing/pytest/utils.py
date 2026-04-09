import pytest

from restalchemy.testing import typing as ra_tp


@pytest.fixture(scope="session")
def xdist_worker_id(request: pytest.FixtureRequest) -> ra_tp.WorkerID:
    """
    Fixture required for handling installations
    with or without `pytest-xdist` package
    """
    try:
        return request.getfixturevalue("worker_id")
    except pytest.FixtureLookupError:
        return None
