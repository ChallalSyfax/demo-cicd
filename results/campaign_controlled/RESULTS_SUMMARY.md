# Résultats de la campagne contrôlée CI/CD

## Protocole

La campagne contrôlée compare trois stratégies CI/CD exécutées manuellement avec `workflow_dispatch` sur la branche `main`.

- Stratégie A : pipeline séquentiel.
- Stratégie B : pipeline parallèle avec cache pip.
- Stratégie C : pipeline conditionnel, exécuté ici en mode complet via `workflow_dispatch`.

Chaque stratégie a été exécutée 10 fois. Les exécutions ont été lancées de manière contrôlée, une par une, afin de limiter l'effet de file d'attente GitHub Actions.

Les fichiers de données associés sont :

- `runs_A.csv`, `jobs_A.csv`
- `runs_B.csv`, `jobs_B.csv`
- `runs_C.csv`, `jobs_C.csv`
- `aggregate.csv`
- `trivy_counts.csv`
- `trivy_summary.csv`

## Résultats globaux

| Stratégie | Runs | Succès | Taux de succès | Moyenne durée | Médiane durée | Min | Max | Écart-type | Minutes facturables moyennes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 10 | 10 | 100 % | 47,2 s | 48,0 s | 36,0 s | 55,0 s | 6,8 s | 1,0 |
| B | 10 | 10 | 100 % | 43,8 s | 42,0 s | 34,0 s | 61,0 s | 8,4 s | 5,0 |
| C | 10 | 10 | 100 % | 43,9 s | 42,5 s | 36,0 s | 52,0 s | 5,2 s | 5,0 |

## Interprétation performance

Les trois stratégies obtiennent un taux de succès de 100 %, ce qui montre que les trois conceptions de pipeline sont fonctionnelles.

La stratégie A, séquentielle, présente une durée moyenne de 47,2 secondes et une médiane de 48 secondes. Les stratégies B et C sont légèrement plus rapides en durée murale, avec environ 43,8 secondes pour B et 43,9 secondes pour C.

Par rapport à A, la stratégie B réduit la durée moyenne d'environ 7,2 %, tandis que la stratégie C réduit la durée moyenne d'environ 7,0 %. En médiane, B passe de 48 secondes à 42 secondes, et C à 42,5 secondes.

Cependant, cette amélioration de durée s'accompagne d'une consommation plus élevée de minutes facturables. A consomme en moyenne 1 minute facturable par run, tandis que B et C consomment environ 5 minutes facturables par run, car les jobs sont séparés et arrondis individuellement par GitHub Actions.

Le résultat montre donc un compromis classique : le parallélisme peut réduire légèrement le temps d'attente utilisateur, mais augmente le coût d'exécution estimé.

## Résultats Trivy

| Stratégie | Rapports | UNKNOWN | LOW | MEDIUM | HIGH | CRITICAL | Total moyen |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 10 | 0 | 1 | 0 | 0 | 0 | 1 |
| B | 10 | 0 | 1 | 0 | 0 | 0 | 1 |
| C | 10 | 0 | 1 | 0 | 0 | 0 | 1 |

Les résultats Trivy sont identiques sur les trois stratégies : une vulnérabilité de sévérité LOW est détectée, sans vulnérabilité MEDIUM, HIGH ou CRITICAL.

Ce résultat est cohérent, car les trois stratégies analysent le même dépôt applicatif. La différence entre les stratégies ne porte donc pas sur le résultat de sécurité obtenu, mais sur la manière d'organiser et d'optimiser l'exécution du pipeline.

## Conclusion expérimentale

La stratégie A constitue une base simple, lisible et peu coûteuse. Elle est légèrement plus lente en durée murale, mais elle consomme moins de minutes facturables.

La stratégie B améliore légèrement la durée observée grâce au parallélisme et au cache, mais augmente fortement le coût estimé en minutes facturables.

La stratégie C obtient des performances proches de B en mode complet. Son intérêt principal n'est pas seulement la performance brute, mais surtout l'adaptation contextuelle : elle peut exécuter un pipeline allégé sur pull request et un pipeline complet sur push ou exécution manuelle.

Ainsi, dans ce projet, la stratégie C apparaît comme la plus équilibrée d'un point de vue DevSecOps, car elle combine automatisation, contrôles sécurité, adaptation au contexte et séparation claire des responsabilités.
