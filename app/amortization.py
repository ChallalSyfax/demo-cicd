"""Cœur métier : échéancier d'amortissement à mensualités constantes.

Module volontairement PUR (aucune dépendance à FastAPI ni au stockage). C'est la
logique testable du dispositif : elle porte la couverture et sert de base à la
calibration déterministe de la charge (cf. ``tests/test_amortization.py``).

Tous les calculs sont menés en :class:`~decimal.Decimal` au centime, de sorte que
deux invariants sont garantis exactement :

* la somme des capitaux amortis vaut le montant emprunté ;
* le capital restant après la dernière échéance est nul.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class Echeance:
    """Une ligne d'échéancier."""

    numero: int
    mensualite: Decimal
    interet: Decimal
    capital: Decimal
    capital_restant: Decimal


def _round(value: Decimal) -> Decimal:
    """Arrondit une valeur monétaire au centime (arrondi commercial)."""
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def compute_schedule(
    montant: Decimal, taux_annuel: Decimal, duree_mois: int
) -> list[Echeance]:
    """Calcule l'échéancier d'un crédit à mensualités constantes.

    Args:
        montant: capital emprunté (strictement positif).
        taux_annuel: taux nominal annuel (>= 0), p. ex. ``Decimal("0.05")`` pour 5 %.
        duree_mois: nombre de mensualités (strictement positif).

    Returns:
        La liste des échéances, de la première à la dernière.

    Raises:
        ValueError: si l'un des paramètres est hors domaine.
    """
    if montant <= 0:
        raise ValueError("le montant doit être strictement positif")
    if taux_annuel < 0:
        raise ValueError("le taux annuel ne peut pas être négatif")
    if duree_mois <= 0:
        raise ValueError("la durée doit être strictement positive")

    montant = _round(Decimal(montant))
    taux_mensuel = Decimal(taux_annuel) / Decimal(12)

    if taux_mensuel == 0:
        mensualite = _round(montant / Decimal(duree_mois))
    else:
        # Mensualité constante : M·i·(1+i)^n / ((1+i)^n − 1).
        q = (Decimal(1) + taux_mensuel) ** duree_mois
        mensualite = _round(montant * taux_mensuel * q / (q - Decimal(1)))

    echeances: list[Echeance] = []
    restant = montant
    for numero in range(1, duree_mois + 1):
        interet = _round(restant * taux_mensuel)
        if numero == duree_mois:
            # Dernière échéance : on solde le capital restant (absorbe les arrondis).
            capital = restant
            mensualite_courante = _round(capital + interet)
        else:
            capital = mensualite - interet
            mensualite_courante = mensualite
        restant = restant - capital
        echeances.append(
            Echeance(
                numero=numero,
                mensualite=mensualite_courante,
                interet=interet,
                capital=capital,
                capital_restant=restant,
            )
        )
    return echeances
