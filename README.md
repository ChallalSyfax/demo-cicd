# demo-cicd

Petite API Flask servant de **support d'expérimentation** à la comparaison de trois
stratégies de pipeline CI/CD DevSecOps (mémoire de Master 1). L'application est
volontairement minimale : pas de base de données, pas d'authentification, pas de
frontend, stockage en mémoire.

## Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET`  | `/health`        | Sonde de disponibilité (`{"status": "ok"}`) |
| `GET`  | `/items`         | Liste tous les items |
| `POST` | `/items`         | Crée un item (JSON : `name` requis, `description` optionnel) |
| `GET`  | `/items/<id>`    | Renvoie un item par son identifiant |

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Lancer l'application

```bash
python -m app.app
# API disponible sur http://127.0.0.1:5000
```

Exemple :

```bash
curl http://127.0.0.1:5000/health
curl -X POST http://127.0.0.1:5000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "exemple", "description": "un item"}'
curl http://127.0.0.1:5000/items
```

## Tests & couverture

```bash
pytest
```

La configuration (dans `pyproject.toml`) génère automatiquement le rapport de
couverture en console et un fichier `coverage.xml` (réutilisé plus tard par
l'analyse qualité).

## Qualité (lint)

```bash
ruff check .
```

## CI/CD

Le workflow `.github/workflows/pipeline-a-sequential.yml` (**Pipeline A**, stratégie
séquentielle) sert de baseline de référence. Il s'exécute **manuellement**
(`workflow_dispatch`) et enchaîne, dans un seul job : tests + couverture, Ruff,
SonarCloud, SBOM (Syft), scan de vulnérabilités (Trivy), puis archivage des rapports
(`coverage.xml`, `sbom.cyclonedx.json`, `trivy-fs.json`).

### À configurer sur GitHub

| Type | Nom | Rôle |
|------|-----|------|
| Secret | `SONAR_TOKEN` | Jeton d'analyse SonarCloud. **Seule valeur sensible.** Tant qu'il est absent, l'étape SonarCloud est automatiquement sautée (le reste du pipeline tourne normalement) ; dès qu'il est défini, elle s'active sans modifier les workflows. |

> Détail d'implémentation : `SONAR_TOKEN` est déclaré au niveau du **job**, et non de
> l'étape. Le bloc `env:` d'une étape n'est pas visible depuis le `if:` de cette même
> étape — le placer au niveau du job est ce qui rend la condition `if: env.SONAR_TOKEN != ''`
> réellement fonctionnelle.

Les valeurs non sensibles (`sonar.projectKey`, `sonar.organization`, chemin de
couverture) sont versionnées dans `sonar-project.properties` — à ajuster aux valeurs
réelles de ton organisation / projet sur [sonarcloud.io](https://sonarcloud.io).
