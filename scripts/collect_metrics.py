#!/usr/bin/env python3
"""Collecte des métriques de runs GitHub Actions pour un workflow donné.

Interroge l'API GitHub Actions (bibliothèque standard uniquement), récupère les
N derniers runs d'un workflow et leurs jobs, puis exporte deux CSV :

  - runs_<STRATEGIE>.csv : une ligne par run (durée totale, minutes estimées, statut) ;
  - jobs_<STRATEGIE>.csv : une ligne par job (durée par job).

Authentification : variable d'environnement GITHUB_TOKEN (nécessaire pour un dépôt
privé et pour éviter les limites de débit de l'API).

Minutes facturables : estimation « ceil par job » = somme, sur les jobs du run, de
arrondi_supérieur(durée_job / 60), avec un coefficient 1 pour Linux. C'est la logique
de facturation de GitHub (chaque job arrondi à la minute supérieure).

Exemple :
    export GITHUB_TOKEN=ghp_xxx
    python scripts/collect_metrics.py \\
        --repo ChallalSyfax/demo-cicd \\
        --workflow pipeline-a-sequential.yml \\
        --event workflow_dispatch --limit 10
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

API_ROOT = "https://api.github.com"

# Correspondance fichier de workflow -> stratégie (clé stable pour distinguer A/B/C).
STRATEGY_BY_FILE = {
    "pipeline-a-sequential.yml": "A",
    "pipeline-b-parallel-cache.yml": "B",
    "pipeline-c-conditional.yml": "C",
}

# Coefficient de facturation par système. Linux = 1 (cf. barème GitHub Actions).
LINUX_MULTIPLIER = 1


def _get_json(url: str, token: str | None) -> dict:
    """Effectue une requête GET authentifiée et renvoie le JSON décodé."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "demo-cicd-metrics",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")
        sys.exit(f"Erreur API GitHub ({exc.code}) sur {url} : {detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"Erreur réseau sur {url} : {exc.reason}")


def _parse_ts(value: str | None) -> datetime | None:
    """Convertit un timestamp ISO 8601 GitHub (…Z) en datetime."""
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _duration_s(start: str | None, end: str | None) -> float | None:
    """Durée en secondes entre deux timestamps, ou None si l'un manque."""
    start_dt, end_dt = _parse_ts(start), _parse_ts(end)
    if start_dt is None or end_dt is None:
        return None
    return (end_dt - start_dt).total_seconds()


def fetch_runs(repo: str, workflow: str, limit: int, event: str | None,
               branch: str | None, token: str | None) -> list[dict]:
    """Récupère les N derniers runs d'un workflow (une seule page d'API)."""
    if limit > 100:
        print("Attention : l'API renvoie au maximum 100 runs par page ; "
              f"la collecte est limitée à 100 au lieu de {limit}.", file=sys.stderr)
    params = {"per_page": str(min(limit, 100))}
    if event:
        params["event"] = event
    if branch:
        params["branch"] = branch
    query = urllib.parse.urlencode(params)
    url = f"{API_ROOT}/repos/{repo}/actions/workflows/{workflow}/runs?{query}"
    data = _get_json(url, token)
    return data.get("workflow_runs", [])[:limit]


def fetch_jobs(repo: str, run_id: int, token: str | None) -> list[dict]:
    """Récupère les jobs d'un run."""
    url = f"{API_ROOT}/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    return _get_json(url, token).get("jobs", [])


def estimate_billable_minutes(jobs: list[dict]) -> int:
    """Estime les minutes facturables : somme des jobs arrondis à la minute sup."""
    total = 0
    for job in jobs:
        duration = _duration_s(job.get("started_at"), job.get("completed_at"))
        if duration and duration > 0:
            total += math.ceil(duration / 60) * LINUX_MULTIPLIER
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="OWNER/REPO, ex. ChallalSyfax/demo-cicd")
    parser.add_argument("--workflow", required=True,
                        help="Nom du fichier de workflow (ex. pipeline-a-sequential.yml)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Nombre de runs récents (défaut : 10)")
    parser.add_argument("--event", default=None,
                        help="Filtre sur l'événement (ex. workflow_dispatch)")
    parser.add_argument("--branch", default=None, help="Filtre sur la branche")
    parser.add_argument("--strategy", default=None,
                        help="Étiquette A/B/C (sinon déduite du nom de workflow)")
    parser.add_argument("--out-dir", default=".", help="Dossier de sortie des CSV (défaut : .)")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Attention : GITHUB_TOKEN absent — l'API peut échouer sur un dépôt privé "
              "ou atteindre vite la limite de débit.", file=sys.stderr)

    strategy = args.strategy or STRATEGY_BY_FILE.get(args.workflow, "?")
    os.makedirs(args.out_dir, exist_ok=True)

    runs = fetch_runs(args.repo, args.workflow, args.limit, args.event, args.branch, token)
    if not runs:
        sys.exit("Aucun run trouvé pour ces critères.")

    runs_path = os.path.join(args.out_dir, f"runs_{strategy}.csv")
    jobs_path = os.path.join(args.out_dir, f"jobs_{strategy}.csv")

    with open(runs_path, "w", newline="", encoding="utf-8") as runs_file, \
         open(jobs_path, "w", newline="", encoding="utf-8") as jobs_file:

        runs_writer = csv.writer(runs_file)
        runs_writer.writerow([
            "strategy", "workflow_file", "run_id", "run_number", "run_attempt",
            "event", "head_branch", "status", "conclusion",
            "created_at", "run_started_at", "updated_at",
            "duration_total_s", "billable_minutes_linux",
        ])
        jobs_writer = csv.writer(jobs_file)
        jobs_writer.writerow([
            "strategy", "workflow_file", "run_id", "job_id", "job_name",
            "status", "conclusion", "started_at", "completed_at", "duration_s",
        ])

        for run in runs:
            run_id = run["id"]
            jobs = fetch_jobs(args.repo, run_id, token)

            duration_total = _duration_s(run.get("run_started_at") or run.get("created_at"),
                                         run.get("updated_at"))
            billable = estimate_billable_minutes(jobs)

            runs_writer.writerow([
                strategy, args.workflow, run_id, run.get("run_number"),
                run.get("run_attempt"), run.get("event"), run.get("head_branch"),
                run.get("status"), run.get("conclusion"),
                run.get("created_at"), run.get("run_started_at"), run.get("updated_at"),
                "" if duration_total is None else round(duration_total, 1), billable,
            ])

            for job in jobs:
                duration = _duration_s(job.get("started_at"), job.get("completed_at"))
                jobs_writer.writerow([
                    strategy, args.workflow, run_id, job.get("id"), job.get("name"),
                    job.get("status"), job.get("conclusion"),
                    job.get("started_at"), job.get("completed_at"),
                    "" if duration is None else round(duration, 1),
                ])

    print(f"[{strategy}] {len(runs)} runs -> {runs_path}, {jobs_path}")


if __name__ == "__main__":
    main()
