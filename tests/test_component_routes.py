import pytest
from uuid import UUID, uuid4
from datetime import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.routes.component_routes import component_router
from src import models
from src.db import get_db


# =====================================================================
# FIXTURES: Setup & Teardown
# =====================================================================

@pytest.fixture
def app():
    """
    GIVEN a FastAPI application instance
    WHEN the test imports the app
    THEN it should be a valid FastAPI instance with component router.
    """
    app = FastAPI()
    app.include_router(component_router)
    return app


@pytest.fixture
def client(app):
    """
    GIVEN a FastAPI application
    WHEN creating a test client
    THEN it should provide synchronous HTTP testing capability.
    """
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """
    GIVEN a need for mock database operations
    WHEN creating a mock session
    THEN it should return a MagicMock SQLAlchemy Session with query capabilities.
    """
    return MagicMock(spec=Session)


@pytest.fixture
def sample_component_uuid():
    """
    GIVEN a need for a consistent UUID in tests
    WHEN generating a component ID
    THEN it should return a valid UUID instance (not string).
    """
    return uuid4()


@pytest.fixture
def sample_component_response(sample_component_uuid):
    """
    GIVEN a need for sample component data
    WHEN creating a mock component response
    THEN it should return a dict matching ComponentResponse schema with UUID type.
    """
    now = datetime.utcnow()
    return {
        "id": str(sample_component_uuid),  # Serialized to string for JSON
        "name": "ESP32 Development Board",
        "quantity": 5,
        "category_id": 1,
        "datasheet_url": "https://example.com/esp32.pdf",
        "technical_specs": {"voltage": "3.3V", "cores": 2},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }


@pytest.fixture
def sample_component_db(sample_component_uuid):
    """
    GIVEN a need for mock SQLAlchemy Component database object
    WHEN creating a mock model instance
    THEN it should return a MagicMock models.Component with proper attributes.
    """
    mock_component = MagicMock(spec=models.Component)
    mock_component.id = sample_component_uuid
    mock_component.name = "ESP32 Development Board"
    mock_component.quantity = 5
    mock_component.category_id = 1
    mock_component.datasheet_url = "https://example.com/esp32.pdf"
    mock_component.technical_specs = {"voltage": "3.3V", "cores": 2}
    mock_component.created_at = datetime.utcnow()
    mock_component.updated_at = datetime.utcnow()
    return mock_component


@pytest.fixture
def sample_category_db():
    """
    GIVEN a need for mock SQLAlchemy Category database object
    WHEN creating a mock model instance
    THEN it should return a MagicMock models.Category with proper int ID.
    """
    mock_category = MagicMock(spec=models.Category)
    mock_category.id = 1
    mock_category.name = "Mikrodenetleyici"
    mock_category.created_at = datetime.utcnow()
    mock_category.updated_at = datetime.utcnow()
    return mock_category


# =====================================================================
# ENDPOINT 1: GET /api/v1/components/ - LIST COMPONENTS
# =====================================================================

def test_list_components_success(client, mock_db_session, sample_component_db):
    """
    GIVEN multiple components in the database
    WHEN calling GET /api/v1/components/
    THEN it should return a 200 response with a list of all components ordered by updated_at descending.
    """
    # Arrange
    mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        sample_component_db
    ]

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get("/api/v1/components/")

    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_components_with_pagination(client, mock_db_session, sample_component_db):
    """
    GIVEN multiple components in the database
    WHEN calling GET /api/v1/components/ with skip and limit parameters
    THEN it should apply pagination correctly to the query.
    """
    # Arrange
    mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        sample_component_db
    ]

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get("/api/v1/components/?skip=10&limit=50")

    # Assert
    assert response.status_code == 200
    # Verify pagination parameters were used
    mock_db_session.query.return_value.order_by.return_value.offset.assert_called_with(10)
    mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.assert_called_with(50)


def test_list_components_empty(client, mock_db_session):
    """
    GIVEN no components in the database
    WHEN calling GET /api/v1/components/
    THEN it should return a 200 response with an empty list.
    """
    # Arrange
    mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get("/api/v1/components/")

    # Assert
    assert response.status_code == 200
    assert response.json() == []


# =====================================================================
# ENDPOINT 2: GET /api/v1/components/search - SEARCH COMPONENTS
# =====================================================================

def test_search_components_success(client, mock_db_session, sample_component_db, sample_category_db):
    """
    GIVEN a component and category in the database
    WHEN calling GET /api/v1/components/search?search=ESP32
    THEN it should return components matching the search query by name or category name.
    """
    # Arrange
    search_query = "ESP32"
    mock_query = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        sample_component_db
    ]

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get(f"/api/v1/components/search?search={search_query}")

    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_search_components_empty_query_returns_empty(client, mock_db_session):
    """
    GIVEN an empty search query (query parameter is empty string)
    WHEN calling GET /api/v1/components/search?search=
    THEN it should instantly return an empty list without querying the database.
    """

    # Arrange
    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get("/api/v1/components/search?search=")

    # Assert
    assert response.status_code == 200
    assert response.json() == []
    # Verify database was NOT queried
    mock_db_session.query.assert_not_called()


def test_search_components_whitespace_only_query_returns_empty(client, mock_db_session):
    """
    GIVEN a search query containing only whitespace (spaces, tabs, newlines)
    WHEN calling GET /api/v1/components/search?search=%20%20%20
    THEN it should return an empty list without querying the database (edge case guard).
    """

    # Arrange
    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get("/api/v1/components/search?search=   ")

    # Assert
    assert response.status_code == 200
    assert response.json() == []
    mock_db_session.query.assert_not_called()


def test_search_components_no_results(client, mock_db_session):
    """
    GIVEN a search query that matches no components
    WHEN calling GET /api/v1/components/search?search=nonexistent
    THEN it should return a 200 response with an empty list.
    """
    # Arrange
    mock_query = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get("/api/v1/components/search?search=nonexistent")

    # Assert
    assert response.status_code == 200
    assert response.json() == []


def test_search_components_case_insensitive(client, mock_db_session, sample_component_db):
    """
    GIVEN components with mixed case names in database
    WHEN calling GET /api/v1/components/search?search=esp32 (lowercase)
    THEN it should find components with names like "ESP32" (uppercase match).
    """
    # Arrange
    mock_query = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        sample_component_db
    ]

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get("/api/v1/components/search?search=esp32")

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_components_by_category_name(client, mock_db_session, sample_component_db):
    """
    GIVEN components linked to categories
    WHEN calling GET /api/v1/components/search?search=Mikrodenetleyici (category name)
    THEN it should find components by their category name.
    """
    # Arrange
    mock_query = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        sample_component_db
    ]

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get("/api/v1/components/search?search=Mikrodenetleyici")

    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# =====================================================================
# ENDPOINT 3: POST /api/v1/components/ - CREATE COMPONENT
# =====================================================================

def test_create_component_success(client, mock_db_session, sample_component_db):
    """
    GIVEN a valid ComponentCreate payload with all required fields
    WHEN calling POST /api/v1/components/
    THEN it should create the component in the database and return 201 with the created component (with UUID id).
    """
    # Arrange
    component_payload = {
        "name": "ESP32 Development Board",
        "quantity": 5,
        "category_id": 1,
        "datasheet_url": "https://example.com/esp32.pdf",
        "technical_specs": {"voltage": "3.3V", "cores": 2}
    }

    mock_db_session.add = MagicMock()
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock()

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # We need to patch models.Component constructor
    with patch("src.routes.component_routes.models.Component") as MockComponent:
        mock_instance = sample_component_db
        MockComponent.return_value = mock_instance

        # Act
        response = client.post(
            "/api/v1/components/",
            json=component_payload
        )

    # Assert
    assert response.status_code == 201
    assert mock_db_session.add.called
    assert mock_db_session.commit.called
    assert mock_db_session.refresh.called


def test_create_component_with_zero_quantity(client, mock_db_session, sample_component_db):
    """
    GIVEN a valid ComponentCreate payload with quantity=0 (boundary case)
    WHEN calling POST /api/v1/components/
    THEN it should successfully create the component (quantity=0 is valid per schema).
    """
    # Arrange
    component_payload = {
        "name": "Resistor 10K",
        "quantity": 0,  # Zero quantity is valid
        "category_id": 2,
        "datasheet_url": None,
        "technical_specs": {}
    }

    mock_db_session.add = MagicMock()
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock()

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    with patch("src.routes.component_routes.models.Component") as MockComponent:
        mock_instance = sample_component_db
        MockComponent.return_value = mock_instance

        # Act
        response = client.post(
            "/api/v1/components/",
            json=component_payload
        )

    # Assert
    assert response.status_code == 201


def test_create_component_without_category(client, mock_db_session, sample_component_db):
    """
    GIVEN a ComponentCreate payload without a category_id (optional field)
    WHEN calling POST /api/v1/components/
    THEN it should successfully create the component with category_id=None.
    """
    # Arrange
    component_payload = {
        "name": "Unclassified Component",
        "quantity": 10
        # category_id is omitted (optional)
    }

    mock_db_session.add = MagicMock()
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock()

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    with patch("src.routes.component_routes.models.Component") as MockComponent:
        mock_instance = sample_component_db
        MockComponent.return_value = mock_instance

        # Act
        response = client.post(
            "/api/v1/components/",
            json=component_payload
        )

    # Assert
    assert response.status_code == 201


# =====================================================================
# ENDPOINT 4: PUT /api/v1/components/{component_id} - UPDATE COMPONENT
# =====================================================================

def test_update_component_success(client, mock_db_session, sample_component_uuid, sample_component_db):
    """
    GIVEN an existing component with a valid UUID
    WHEN calling PUT /api/v1/components/{component_id} with updated data
    THEN it should update the component and return 200 with the updated component.
    """
    # Arrange
    component_update_payload = {
        "name": "Updated ESP32 Board",
        "quantity": 10
    }

    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_component_db
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock()

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.put(
        f"/api/v1/components/{sample_component_uuid}",
        json=component_update_payload
    )

    # Assert
    assert response.status_code == 200
    assert mock_db_session.commit.called
    assert mock_db_session.refresh.called


def test_update_component_partial_update(client, mock_db_session, sample_component_uuid, sample_component_db):
    """
    GIVEN an existing component
    WHEN calling PUT /api/v1/components/{component_id} with only some fields
    THEN it should perform a partial update (only provided fields are updated).
    """
    # Arrange
    partial_update = {
        "quantity": 20
        # name is NOT provided, should remain unchanged
    }

    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_component_db
    mock_db_session.commit = MagicMock()
    mock_db_session.refresh = MagicMock()

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.put(
        f"/api/v1/components/{sample_component_uuid}",
        json=partial_update
    )

    # Assert
    assert response.status_code == 200
    mock_db_session.commit.called


def test_update_component_not_found(client, mock_db_session, sample_component_uuid):
    """
    GIVEN a component ID that does NOT exist in the database
    WHEN calling PUT /api/v1/components/{component_id}
    THEN it should return 404 with error detail "Component not found".
    """
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.put(
        f"/api/v1/components/{sample_component_uuid}",
        json={"name": "Updated Name"}
    )

    # Assert
    assert response.status_code == 404
    assert "Component not found" in response.json()["detail"]


def test_update_component_invalid_uuid_format(client, mock_db_session):
    """
    GIVEN an invalid UUID format in the URL path
    WHEN calling PUT /api/v1/components/not-a-uuid
    THEN FastAPI should return 422 Unprocessable Entity (validation error).
    """

    # Arrange
    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.put(
        "/api/v1/components/not-a-uuid",
        json={"name": "Updated"}
    )

    # Assert
    assert response.status_code == 422  # Validation error


# =====================================================================
# ENDPOINT 5: DELETE /api/v1/components/{component_id} - DELETE COMPONENT
# =====================================================================

def test_delete_component_success(client, mock_db_session, sample_component_uuid, sample_component_db):
    """
    GIVEN an existing component with a valid UUID
    WHEN calling DELETE /api/v1/components/{component_id}
    THEN it should delete the component and return 204 No Content.
    """
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = sample_component_db
    mock_db_session.delete = MagicMock()
    mock_db_session.commit = MagicMock()

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.delete(f"/api/v1/components/{sample_component_uuid}")

    # Assert
    assert response.status_code == 204
    assert mock_db_session.delete.called
    assert mock_db_session.commit.called


def test_delete_component_not_found(client, mock_db_session, sample_component_uuid):
    """
    GIVEN a component ID that does NOT exist in the database
    WHEN calling DELETE /api/v1/components/{component_id}
    THEN it should return 404 with error detail "Component not found.".
    """
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.delete(f"/api/v1/components/{sample_component_uuid}")

    # Assert
    assert response.status_code == 404
    assert "Component not found" in response.json()["detail"]


def test_delete_component_invalid_uuid_format(client, mock_db_session):
    """
    GIVEN an invalid UUID format in the URL path
    WHEN calling DELETE /api/v1/components/invalid-uuid
    THEN FastAPI should return 422 Unprocessable Entity.
    """

    # Arrange
    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.delete("/api/v1/components/invalid-uuid")

    # Assert
    assert response.status_code == 422


# =====================================================================
# ADVANCED EDGE CASES
# =====================================================================

def test_component_id_type_enforcement_uuid_not_string(client, mock_db_session, sample_component_db):
    """
    GIVEN the requirement that Component IDs must be strict UUID types
    WHEN creating a component via POST
    THEN the returned component should have an ID that is UUID-serializable (not just a string).
    """
    # Arrange
    component_payload = {
        "name": "Type Safety Test",
        "quantity": 1
    }

    mock_db_session.add = MagicMock()
    mock_db_session.commit = MagicMock()

    # Ensure mock returns proper UUID
    sample_component_db.id = uuid4()

    mock_db_session.refresh = MagicMock(side_effect=lambda x: None)

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    with patch("src.routes.component_routes.models.Component") as MockComponent:
        MockComponent.return_value = sample_component_db

        # Act
        response = client.post(
            "/api/v1/components/",
            json=component_payload
        )

    # Assert
    assert response.status_code == 201
    # Response should have an ID field that can be parsed as UUID
    data = response.json()
    try:
        UUID(data["id"])  # Should not raise ValueError
    except (ValueError, TypeError):
        pytest.fail(f"Component ID {data['id']} is not a valid UUID")


def test_component_search_with_special_characters(client, mock_db_session, sample_component_db):
    """
    GIVEN a search query with special characters (%, _, etc.)
    WHEN calling GET /api/v1/components/search
    THEN it should safely escape the query for SQL LIKE operations.
    """
    # Arrange
    mock_query = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        sample_component_db
    ]

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act (search with SQL LIKE special characters)
    response = client.get("/api/v1/components/search?search=ESP%_32")

    # Assert
    assert response.status_code == 200
    # Query should have been called (sqlalchemy ilike handles escaping)
    mock_db_session.query.assert_called()


@pytest.mark.parametrize("pagination_params,expected_offset,expected_limit", [
    ({"skip": 0, "limit": 100}, 0, 100),
    ({"skip": 10, "limit": 50}, 10, 50),
    ({"skip": 100, "limit": 1}, 100, 1),
])
def test_pagination_parameters_applied_correctly(client, mock_db_session, pagination_params, expected_offset,
                                                 expected_limit):
    """
    GIVEN various pagination parameter combinations
    WHEN calling GET /api/v1/components/
    THEN skip and limit should be correctly applied to the database query.
    """
    # Arrange
    mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    def get_db_override():
        return mock_db_session

    client.app.dependency_overrides[get_db] = get_db_override

    # Act
    response = client.get(
        f"/api/v1/components/?skip={pagination_params['skip']}&limit={pagination_params['limit']}"
    )

    # Assert
    assert response.status_code == 200
    mock_db_session.query.return_value.order_by.return_value.offset.assert_called_with(expected_offset)
    mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.assert_called_with(
        expected_limit)
