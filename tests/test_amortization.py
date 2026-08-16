"""Tests du cœur métier (échéancier) et CALIBRATION déterministe de la charge.

La classe ``TestCalibration`` vérifie les invariants de l'échéancier sur un grand
nombre de contrats générés avec une graine fixe. Elle a un double rôle :

1. renforcer la preuve de correction (invariants sur ~un millier de cas) ;
2. **calibrer de façon déterministe la durée du job de test** — sans I/O, sans
   réseau, sans aléa non maîtrisé — afin que la parallélisation (stratégie B)
   puisse produire un gain mesurable. Le nombre de cas est réglable via la
   variable d'environnement ``CALIBRATION_N`` (défaut : 1000 en local ; on
   l'augmente pour les campagnes de mesure en CI).
"""

from __future__ import annotations

import os
import random
from decimal import Decimal

import pytest

from app.amortization import compute_schedule

CALIBRATION_N = int(os.environ.get("CALIBRATION_N", "1000"))


def _sum_capital(echeances) -> Decimal:
    return sum((e.capital for e in echeances), start=Decimal("0.00"))


def test_longueur_egale_a_la_duree():
    echeances = compute_schedule(Decimal("10000.00"), Decimal("0.05"), 24)
    assert len(echeances) == 24
    assert echeances[0].numero == 1
    assert echeances[-1].numero == 24


def test_invariants_taux_positif():
    montant = Decimal("12000.00")
    echeances = compute_schedule(montant, Decimal("0.06"), 36)
    assert _sum_capital(echeances) == montant
    assert echeances[-1].capital_restant == Decimal("0.00")


def test_mensualite_constante_hors_derniere():
    echeances = compute_schedule(Decimal("20000.00"), Decimal("0.045"), 48)
    mensualites = {e.mensualite for e in echeances[:-1]}
    assert len(mensualites) == 1  # constante sur toutes les échéances sauf la dernière


def test_interet_decroissant_taux_positif():
    echeances = compute_schedule(Decimal("15000.00"), Decimal("0.08"), 24)
    interets = [e.interet for e in echeances]
    assert all(
        a >= b for a, b in zip(interets, interets[1:], strict=False)
    )  # intérêts décroissants


def test_taux_nul_est_lineaire():
    montant = Decimal("12000.00")
    echeances = compute_schedule(montant, Decimal("0"), 12)
    assert all(e.interet == Decimal("0.00") for e in echeances)
    assert echeances[0].capital == Decimal("1000.00")
    assert _sum_capital(echeances) == montant
    assert echeances[-1].capital_restant == Decimal("0.00")


def test_arrondi_absorbe_par_la_derniere_echeance():
    # 10 000 / 3 ne tombe pas juste : la dernière échéance solde le reste.
    montant = Decimal("10000.00")
    echeances = compute_schedule(montant, Decimal("0"), 3)
    assert _sum_capital(echeances) == montant
    assert echeances[-1].capital_restant == Decimal("0.00")


@pytest.mark.parametrize(
    "montant, taux, duree",
    [
        (Decimal("0.00"), Decimal("0.05"), 12),
        (Decimal("-1.00"), Decimal("0.05"), 12),
    ],
)
def test_montant_invalide_leve_valueerror(montant, taux, duree):
    with pytest.raises(ValueError):
        compute_schedule(montant, taux, duree)


def test_taux_negatif_leve_valueerror():
    with pytest.raises(ValueError):
        compute_schedule(Decimal("1000.00"), Decimal("-0.01"), 12)


def test_duree_invalide_leve_valueerror():
    with pytest.raises(ValueError):
        compute_schedule(Decimal("1000.00"), Decimal("0.05"), 0)


class TestCalibration:
    """Invariants sur un grand nombre de cas déterministes (graine fixe)."""

    def test_invariants_sur_contrats_aleatoires_reproductibles(self):
        rng = random.Random(42)  # graine fixe => exécution reproductible
        for _ in range(CALIBRATION_N):
            montant = Decimal(rng.randint(100_000, 50_000_000)) / Decimal(100)
            taux = Decimal(rng.randint(0, 1500)) / Decimal(10_000)  # 0 % à 15 %
            duree = rng.randint(6, 360)

            echeances = compute_schedule(montant, taux, duree)

            assert len(echeances) == duree
            assert _sum_capital(echeances) == montant
            assert echeances[-1].capital_restant == Decimal("0.00")
