# Scripts de mesure

Outils de collecte et d'exploitation des résultats des runs GitHub Actions, pour
alimenter le chapitre d'analyse du mémoire. **Aucune dépendance externe** : Python 3.11+
et la bibliothèque standard suffisent.

| Script | Rôle | Entrée | Sortie |
|--------|------|--------|--------|
| `collect_metrics.py` | Interroge l'API Actions, récupère runs + jobs | API GitHub | `runs_<X>.csv`, `jobs_<X>.csv` |
| `aggregate_metrics.py` | Statistiques par stratégie | `runs_*.csv` | `aggregate.csv` |
| `extract_trivy_counts.py` | Comptage vulnérabilités par sévérité | rapports Trivy JSON | `trivy_counts.csv` |

## Prérequis

Un jeton d'accès personnel GitHub (lecture des Actions), exporté avant la collecte :

```bash
export GITHUB_TOKEN=ghp_xxxxxxxx
```

Nécessaire pour un dépôt privé et pour éviter la limite de débit de l'API.

## Dérouler une campagne de mesure

**1. Lancer les runs.** Pour comparer A, B et C de façon honnête, déclenche-les
**tous en `workflow_dispatch`** (chaîne complète). Répète chaque workflow
**au moins 10 fois** (idéalement plus) pour lisser la variabilité des runners.

**2. Collecter les métriques de durée / coût / statut :**

```bash
python scripts/collect_metrics.py --repo ChallalSyfax/demo-cicd \
    --workflow pipeline-a-sequential.yml --event workflow_dispatch --limit 10
python scripts/collect_metrics.py --repo ChallalSyfax/demo-cicd \
    --workflow pipeline-b-parallel-cache.yml --event workflow_dispatch --limit 10
python scripts/collect_metrics.py --repo ChallalSyfax/demo-cicd \
    --workflow pipeline-c-conditional.yml --event workflow_dispatch --limit 10
```

**3. Agréger :**

```bash
python scripts/aggregate_metrics.py runs_A.csv runs_B.csv runs_C.csv --out aggregate.csv
```

**4. Compter les vulnérabilités Trivy.** Télécharge les artefacts `trivy-report`
(fichiers `trivy-fs.json`) depuis l'onglet Actions, renomme-les pour distinguer la
stratégie, puis :

```bash
python scripts/extract_trivy_counts.py trivy_A.json trivy_B.json trivy_C.json --out trivy_counts.csv
```

> Le téléchargement des artefacts Trivy est **manuel** pour l'instant (volontairement
> simple). Une automatisation via l'API pourra être ajoutée plus tard.

## Comment sont calculées les métriques

- **Durée totale (wall-clock)** : `updated_at − run_started_at` du run.
- **Durée par job** : `completed_at − started_at` de chaque job.
- **Minutes facturables (estimées)** : somme, sur les jobs du run, de
  `arrondi_supérieur(durée_job / 60)`, coefficient **1** pour Linux — ce qui reproduit
  l'arrondi par job appliqué par GitHub.
- **Taux de succès** : proportion de runs dont `conclusion == success`.

## Limites méthodologiques (à mentionner dans le mémoire)

1. **Variabilité des runners** : matériel et réseau partagés → bruit sur les durées.
   D'où ≥ 10 runs, et lecture **moyenne + écart-type** plutôt qu'une valeur unique.
   Ne pas sur-interpréter de petits écarts.
2. **Effet du cache** : le premier run de B/C part d'un cache froid ; l'état du cache
   conditionne fortement la durée. Marquer ou exclure ce premier run.
3. **Arrondi de facturation** : les minutes facturables ≠ wall-clock. L'arrondi par job
   gonfle mécaniquement les stratégies parallèles (B) — arbitrage temps/coût à discuter.
4. **Base de vulnérabilités Trivy évolutive** : à dépendances identiques, les comptes
   peuvent varier selon la date du scan (base mise à jour ~quotidiennement). Noter la
   fenêtre de mesure.
5. **SonarCloud externe** : latence variable, et étape sautée sans `SONAR_TOKEN`. Garder
   la présence du token **constante** sur toute la campagne, sinon les runs ne sont pas
   comparables.
6. **Comparaison valide en `workflow_dispatch` uniquement** (chaîne complète pour A/B/C).
   Les runs `pull_request` / `push` de C s'analysent séparément.
7. **Petit échantillon, environnement non contrôlé** → statistiques **descriptives**,
   sans prétention à la significativité statistique.
