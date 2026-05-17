"""
Locust load test for the SRE Product Service.

Scenarios:
  - GET /health       weight 1  (liveness probes)
  - GET /products     weight 5  (browse catalog)
  - POST /products    weight 2  (create product)
  - GET /products/:id weight 3  (product detail)

Run:
  locust -f locustfile.py --host http://<EC2_IP>:8000

Headless ramp-up (10 → 200 users, spawn rate 10/sec, 5 min run):
  locust -f locustfile.py --host http://<EC2_IP>:8000 \
         --headless -u 200 -r 10 --run-time 5m \
         --html report.html --csv results
"""
from __future__ import annotations

import random
import string

from locust import HttpUser, between, task


def _random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


class ProductServiceUser(HttpUser):
    """Simulates a realistic mix of catalog API traffic."""

    # Wait 0.5–2 seconds between tasks (simulates human think-time)
    wait_time = between(0.5, 2.0)

    # Shared pool of product IDs discovered during the test
    _known_ids: list[str] = []

    def on_start(self) -> None:
        """Called once per virtual user at startup — warm up known IDs."""
        resp = self.client.get("/products", name="/products [warm-up]")
        if resp.ok:
            data = resp.json()
            for product in data:
                if product.get("id") not in self.__class__._known_ids:
                    self.__class__._known_ids.append(product["id"])

    # ── Tasks ─────────────────────────────────────────────────────────────

    @task(1)
    def health_check(self) -> None:
        """GET /health — liveness probe (low weight, always present)."""
        self.client.get("/health", name="/health")

    @task(5)
    def list_products(self) -> None:
        """GET /products — browse catalog (highest weight, most common)."""
        params = {}
        # Randomly add filters to exercise different code paths
        if random.random() < 0.3:
            params["category"] = random.choice(
                ["Electronics", "Accessories", "Clothing", "Books"]
            )
        if random.random() < 0.2:
            params["limit"] = random.randint(5, 20)
            params["offset"] = random.randint(0, 5)

        self.client.get("/products", params=params, name="/products")

    @task(2)
    def create_product(self) -> None:
        """POST /products — create a new product."""
        payload = {
            "name": f"Load Test Product {_random_string()}",
            "description": "Automatically generated during load test",
            "price": round(random.uniform(1.0, 999.99), 2),
            "category": random.choice(
                ["Electronics", "Accessories", "Clothing", "Books", "Sports"]
            ),
            "stock": random.randint(0, 500),
        }
        resp = self.client.post("/products", json=payload, name="/products [POST]")
        if resp.ok:
            product_id = resp.json().get("id")
            if product_id:
                self.__class__._known_ids.append(product_id)
                # Keep pool bounded to avoid unbounded memory growth
                if len(self.__class__._known_ids) > 500:
                    self.__class__._known_ids = self.__class__._known_ids[-500:]

    @task(3)
    def get_product(self) -> None:
        """GET /products/:id — product detail page."""
        if not self.__class__._known_ids:
            # Fall back to listing if no IDs are known yet
            self.list_products()
            return

        product_id = random.choice(self.__class__._known_ids)
        self.client.get(
            f"/products/{product_id}",
            name="/products/:id",
        )

    @task(1)
    def get_product_not_found(self) -> None:
        """GET /products/:id with an invalid ID — exercises 404 path."""
        self.client.get(
            "/products/nonexistent-id-00000",
            name="/products/:id [404]",
        )


class SpikeUser(HttpUser):
    """
    Secondary user class for spike testing.
    Hammers /products with no wait time to simulate traffic bursts.
    Activate with: --class-picker or by commenting out ProductServiceUser.
    """

    wait_time = between(0.1, 0.5)
    weight = 0  # Set to >0 to include in mixed load

    @task
    def spike_list(self) -> None:
        self.client.get("/products", name="/products [spike]")
