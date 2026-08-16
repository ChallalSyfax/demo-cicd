"""Schémas de validation et de sérialisation (Pydantic v2).

La validation stricte des entrées fait partie du volet « conformité » du
dispositif : les contraintes de domaine (montant positif, taux borné, durée
plausible) sont déclarées ici et appliquées automatiquement par FastAPI.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class ContratCreate(BaseModel):
    """Données d'entrée pour la création d'un contrat de crédit-bail."""

    client: str = Field(min_length=1, max_length=120)
    montant: Decimal = Field(gt=0, description="Capital financé, en euros.")
    taux_annuel: Decimal = Field(ge=0, le=1, description="Taux nominal annuel (0..1).")
    duree_mois: int = Field(gt=0, le=600, description="Nombre de mensualités.")


class ContratOut(BaseModel):
    """Représentation d'un contrat renvoyée par l'API."""

    id: int
    client: str
    montant: Decimal
    taux_annuel: Decimal
    duree_mois: int


class EcheanceOut(BaseModel):
    """Une ligne d'échéancier renvoyée par l'API."""

    numero: int
    mensualite: Decimal
    interet: Decimal
    capital: Decimal
    capital_restant: Decimal
