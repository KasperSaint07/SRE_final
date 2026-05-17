"""
Pytest test suite for the SRE Product Service.
Uses httpx.AsyncClient with ASGITransport — no real server needed.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app, _products


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def reset_products():
    """Snapshot + restore the in-memory store between tests."""
    snapshot = dict(_products)
    yield
    _products.clear()
    _products.update(snapshot)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_body(client):
    data = (await client.get("/health")).json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "timestamp" in data
    assert data["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# GET /products
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_products_returns_200(client):
    resp = await client.get("/products")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_products_returns_list(client):
    data = (await client.get("/products")).json()
    assert isinstance(data, list)
    assert len(data) >= 1  # seeded products exist


@pytest.mark.asyncio
async def test_list_products_filter_by_category(client):
    data = (await client.get("/products?category=Electronics")).json()
    assert all(p["category"] == "Electronics" for p in data)


@pytest.mark.asyncio
async def test_list_products_pagination(client):
    all_items = (await client.get("/products")).json()
    page = (await client.get("/products?limit=1&offset=0")).json()
    assert len(page) == 1
    assert page[0]["id"] == all_items[0]["id"]


# ---------------------------------------------------------------------------
# POST /products
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_product_returns_201(client):
    payload = {"name": "Test Widget", "price": 9.99, "category": "Test", "stock": 10}
    resp = await client.post("/products", json=payload)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_product_body(client):
    payload = {"name": "Test Widget", "price": 9.99, "category": "Test", "stock": 10}
    data = (await client.post("/products", json=payload)).json()
    assert data["name"] == "Test Widget"
    assert data["price"] == 9.99
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_product_invalid_price(client):
    payload = {"name": "Bad", "price": -1, "category": "X"}
    resp = await client.post("/products", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_product_missing_name(client):
    resp = await client.post("/products", json={"price": 10.0, "category": "X"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /products/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_product_exists(client):
    created = (
        await client.post(
            "/products",
            json={"name": "Findable", "price": 1.0, "category": "C"},
        )
    ).json()
    resp = await client.get(f"/products/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_product_not_found(client):
    resp = await client.get("/products/does-not-exist-00000")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_returns_200(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_metrics_prometheus_format(client):
    text = (await client.get("/metrics")).text
    assert "http_requests_total" in text
    assert "http_request_duration_seconds" in text
