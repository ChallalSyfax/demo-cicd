"""Tests des endpoints de l'API Flask.

Chaque test part d'une application fraîche (store vide) grâce à la
*fixture* ``client``, ce qui garantit leur indépendance.
"""

import pytest

from app import create_app


@pytest.fixture
def client():
    """Fournit un client de test Flask basé sur une application neuve."""
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_list_items_empty(client):
    resp = client.get("/items")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_item(client):
    resp = client.post("/items", json={"name": "Premier", "description": "test"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["name"] == "Premier"
    assert body["description"] == "test"


def test_create_item_trims_name(client):
    resp = client.post("/items", json={"name": "  espace  "})
    assert resp.status_code == 201
    assert resp.get_json()["name"] == "espace"


def test_create_item_without_name_is_rejected(client):
    resp = client.post("/items", json={"description": "sans nom"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_item_with_empty_name_is_rejected(client):
    resp = client.post("/items", json={"name": "   "})
    assert resp.status_code == 400


def test_create_item_without_json_body_is_rejected(client):
    resp = client.post("/items", data="pas du json", content_type="text/plain")
    assert resp.status_code == 400


def test_get_item(client):
    created = client.post("/items", json={"name": "Cible"}).get_json()
    resp = client.get(f"/items/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Cible"


def test_get_item_not_found(client):
    resp = client.get("/items/999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_ids_are_incremented(client):
    first = client.post("/items", json={"name": "un"}).get_json()
    second = client.post("/items", json={"name": "deux"}).get_json()
    assert first["id"] == 1
    assert second["id"] == 2

    listing = client.get("/items").get_json()
    assert len(listing) == 2
