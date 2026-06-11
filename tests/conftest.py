import pytest
from unittest.mock import MagicMock
from src import models


@pytest.fixture
def mock_current_admin():
    """Returns a mock user with admin role."""
    user = MagicMock(spec=models.User)
    user.id = 1
    user.username = "test_admin"
    user.email = "admin@example.com"
    user.role = "admin"
    return user


@pytest.fixture
def mock_current_user():
    """Returns a mock user with standard user role."""
    user = MagicMock(spec=models.User)
    user.id = 2
    user.username = "test_user"
    user.email = "user@example.com"
    user.role = "user"
    return user


@pytest.fixture
def mock_current_chatter():
    """Returns a mock user with chatter role."""
    user = MagicMock(spec=models.User)
    user.id = 3
    user.username = "test_chatter"
    user.email = "chatter@example.com"
    user.role = "chatter"
    return user
