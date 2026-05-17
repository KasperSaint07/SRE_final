"""
E-Commerce Product Catalog Microservice
FastAPI + Prometheus metrics + in-memory storage
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
    REGISTRY,
)
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SRE Product Service",
    description="Production-ready e-commerce product microservice",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ERROR_COUNT = Counter(
    "http_requests_errors_total",
    "Total HTTP request errors (4xx/5xx)",
    ["method", "endpoint", "status_code"],
)

# ---------------------------------------------------------------------------
# Middleware — record every request
# ---------------------------------------------------------------------------


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start

    endpoint = request.url.path
    method = request.method
    status = str(response.status_code)

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    if response.status_code >= 400:
        ERROR_COUNT.labels(method=method, endpoint=endpoint, status_code=status).inc()

    return response


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, example="Laptop Pro X")
    description: Optional[str] = Field(None, max_length=1000, example="High-end laptop")
    price: float = Field(..., gt=0, example=999.99)
    category: str = Field(..., min_length=1, max_length=100, example="Electronics")
    stock: int = Field(default=0, ge=0, example=50)


class Product(ProductCreate):
    id: str
    created_at: str
    updated_at: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    uptime_seconds: float


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_products: Dict[str, Product] = {}
_start_time = time.time()

# Seed some demo products so GET /products is never empty
def _seed():
    demo = [
        ProductCreate(name="Laptop Pro X", description="High-performance laptop", price=1299.99, category="Electronics", stock=25),
        ProductCreate(name="Wireless Mouse", description="Ergonomic wireless mouse", price=49.99, category="Accessories", stock=100),
        ProductCreate(name="USB-C Hub", description="7-in-1 USB-C hub", price=39.99, category="Accessories", stock=75),
    ]
    for item in demo:
        pid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        _products[pid] = Product(id=pid, created_at=now, updated_at=now, **item.dict())


_seed()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["Operations"])
async def health():
    """Liveness + readiness probe endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        version="1.0.0",
        uptime_seconds=round(time.time() - _start_time, 2),
    )


@app.get("/products", response_model=List[Product], tags=["Products"])
async def list_products(
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Return paginated product list, optionally filtered by category."""
    items = list(_products.values())
    if category:
        items = [p for p in items if p.category.lower() == category.lower()]
    return items[offset : offset + limit]


@app.post("/products", response_model=Product, status_code=201, tags=["Products"])
async def create_product(payload: ProductCreate):
    """Create a new product and return it with generated ID."""
    pid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    product = Product(id=pid, created_at=now, updated_at=now, **payload.dict())
    _products[pid] = product
    return product


@app.get("/products/{product_id}", response_model=Product, tags=["Products"])
async def get_product(product_id: str):
    """Fetch a single product by ID."""
    product = _products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product


@app.get("/metrics", response_class=PlainTextResponse, tags=["Operations"])
async def metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
