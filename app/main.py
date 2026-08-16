"""API de crédit-bail (FastAPI) — support d'expérimentation CI/CD DevSecOps.

Endpoints :

* ``GET  /health``                       — sonde de disponibilité (conteneur).
* ``POST /contrats``                     — crée un contrat (validation stricte).
* ``GET  /contrats``                     — liste les contrats.
* ``GET  /contrats/{id}``                — renvoie un contrat, 404 sinon.
* ``DELETE /contrats/{id}``              — supprime un contrat, 404 sinon.
* ``GET  /contrats/{id}/echeancier``     — calcule l'échéancier d'amortissement.
* ``POST /contrats/import``              — import CSV (entrée utilisateur).

Le stockage est un dictionnaire en mémoire, propre à chaque instance renvoyée
par :func:`create_app` : chaque test repart d'un état vierge (isolation).
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import FastAPI, HTTPException, Response, UploadFile

from app.amortization import compute_schedule
from app.schemas import ContratCreate, ContratOut, EcheanceOut


def create_app() -> FastAPI:
    """Crée et configure une instance de l'application (application factory)."""
    app = FastAPI(title="API Crédit-bail (démo CI/CD DevSecOps)", version="0.2.0")

    contrats: dict[int, dict[str, Any]] = {}
    counter = {"next_id": 1}

    def _store(data: ContratCreate) -> dict[str, Any]:
        contrat = {"id": counter["next_id"], **data.model_dump()}
        contrats[contrat["id"]] = contrat
        counter["next_id"] += 1
        return contrat

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/contrats", response_model=ContratOut, status_code=201)
    def create_contrat(data: ContratCreate) -> dict[str, Any]:
        return _store(data)

    @app.get("/contrats", response_model=list[ContratOut])
    def list_contrats() -> list[dict[str, Any]]:
        return list(contrats.values())

    @app.get("/contrats/{contrat_id}", response_model=ContratOut)
    def get_contrat(contrat_id: int) -> dict[str, Any]:
        contrat = contrats.get(contrat_id)
        if contrat is None:
            raise HTTPException(status_code=404, detail="contrat introuvable")
        return contrat

    @app.delete("/contrats/{contrat_id}", status_code=204)
    def delete_contrat(contrat_id: int) -> Response:
        if contrats.pop(contrat_id, None) is None:
            raise HTTPException(status_code=404, detail="contrat introuvable")
        return Response(status_code=204)

    @app.get("/contrats/{contrat_id}/echeancier", response_model=list[EcheanceOut])
    def echeancier(contrat_id: int) -> list[dict[str, Any]]:
        contrat = contrats.get(contrat_id)
        if contrat is None:
            raise HTTPException(status_code=404, detail="contrat introuvable")
        echeances = compute_schedule(
            contrat["montant"], contrat["taux_annuel"], contrat["duree_mois"]
        )
        return [asdict(e) for e in echeances]

    @app.post("/contrats/import", response_model=list[ContratOut], status_code=201)
    def import_contrats(file: UploadFile) -> list[dict[str, Any]]:
        raw = file.file.read().decode("utf-8", errors="strict")
        reader = csv.DictReader(io.StringIO(raw))
        created: list[dict[str, Any]] = []
        for line_no, row in enumerate(reader, start=2):  # ligne 1 = en-tête
            try:
                data = ContratCreate(
                    client=row["client"],
                    montant=Decimal(row["montant"]),
                    taux_annuel=Decimal(row["taux_annuel"]),
                    duree_mois=int(row["duree_mois"]),
                )
            except (KeyError, InvalidOperation, ValueError) as exc:
                raise HTTPException(
                    status_code=400, detail=f"ligne CSV {line_no} invalide : {exc}"
                ) from exc
            created.append(_store(data))
        return created

    return app


# Lancement direct en développement : ``python -m app.main``.
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
