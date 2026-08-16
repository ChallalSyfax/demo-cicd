"""Package applicatif : mini-API de crédit-bail servant de support d'expérimentation CI/CD.

L'application n'est pas l'objet d'étude : c'est un *instrument* volontairement
contrôlé et reproductible, dont la logique métier (calcul d'échéancier
d'amortissement) donne de la matière aux tests, à la couverture et à l'analyse
de qualité, et dont la charge de test est calibrable de façon déterministe.
"""

from app.main import create_app

__all__ = ["create_app"]
