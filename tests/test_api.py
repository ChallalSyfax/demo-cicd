"""Tests d'intégration de l'API (FastAPI TestClient).

Chaque test part d'une application fraîche (store vide) grâce à la fixture
``client``, ce qui garantit l'indépendance des tests.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app import create_app

_CONTRAT = {"client": "ACME", "montant": "10000.00", "taux_annuel": "0.05", "duree_mois": 24}


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_contrats_vide(client):
    resp = client.get("/contrats")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_contrat(client):
    resp = client.post("/contrats", json=_CONTRAT)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["client"] == "ACME"


@pytest.mark.parametrize(
    "patch",
    [
        {"montant": "0"},          # montant non positif
        {"montant": "-5"},         # montant négatif
        {"taux_annuel": "1.5"},    # taux hors bornes (> 1)
        {"taux_annuel": "-0.1"},   # taux négatif
        {"duree_mois": 0},         # durée non positive
        {"duree_mois": 900},       # durée hors bornes (> 600)
        {"client": ""},            # client vide
    ],
)
def test_create_contrat_invalide_renvoie_422(client, patch):
    payload = {**_CONTRAT, **patch}
    resp = client.post("/contrats", json=payload)
    assert resp.status_code == 422


def test_create_contrat_champ_manquant_renvoie_422(client):
    resp = client.post("/contrats", json={"client": "ACME", "montant": "1000"})
    assert resp.status_code == 422


def test_get_contrat(client):
    created = client.post("/contrats", json=_CONTRAT).json()
    resp = client.get(f"/contrats/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["client"] == "ACME"


def test_get_contrat_introuvable(client):
    resp = client.get("/contrats/999")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_delete_contrat(client):
    created = client.post("/contrats", json=_CONTRAT).json()
    assert client.delete(f"/contrats/{created['id']}").status_code == 204
    assert client.get(f"/contrats/{created['id']}").status_code == 404


def test_delete_contrat_introuvable(client):
    assert client.delete("/contrats/999").status_code == 404


def test_ids_incrementes_et_isolation(client):
    first = client.post("/contrats", json=_CONTRAT).json()
    second = client.post("/contrats", json=_CONTRAT).json()
    assert first["id"] == 1
    assert second["id"] == 2
    assert len(client.get("/contrats").json()) == 2


def test_echeancier(client):
    created = client.post("/contrats", json=_CONTRAT).json()
    resp = client.get(f"/contrats/{created['id']}/echeancier")
    assert resp.status_code == 200
    echeances = resp.json()
    assert len(echeances) == 24
    # Somme des capitaux ≈ montant (tolérance flottante côté JSON).
    total_capital = sum(float(e["capital"]) for e in echeances)
    assert total_capital == pytest.approx(10000.0, abs=0.01)
    assert float(echeances[-1]["capital_restant"]) == pytest.approx(0.0, abs=0.01)


def test_echeancier_introuvable(client):
    assert client.get("/contrats/999/echeancier").status_code == 404


def test_import_csv_valide(client):
    csv_content = (
        "client,montant,taux_annuel,duree_mois\n"
        "ACME,10000.00,0.05,24\n"
        "Globex,5000.00,0.00,12\n"
    )
    files = {"file": ("contrats.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/contrats/import", files=files)
    assert resp.status_code == 201
    assert len(resp.json()) == 2
    assert len(client.get("/contrats").json()) == 2


def test_import_csv_ligne_invalide_renvoie_400(client):
    csv_content = (
        "client,montant,taux_annuel,duree_mois\n"
        "ACME,pas_un_nombre,0.05,24\n"
    )
    files = {"file": ("contrats.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/contrats/import", files=files)
    assert resp.status_code == 400
