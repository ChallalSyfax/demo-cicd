#!/usr/bin/env python3
"""Agrège un ou plusieurs CSV de runs (produits par collect_metrics.py).

Regroupe les runs par stratégie (A/B/C) et calcule, par stratégie :
nombre de runs, taux de succès, et statistiques (moyenne, médiane, min, max,
écart-type) sur la durée totale et sur les minutes facturables estimées.

Utilise uniquement la bibliothèque standard (csv, statistics).

Exemple :
    python scripts/aggregate_metrics.py runs_A.csv runs_B.csv runs_C.csv --out aggregate.csv
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stats(values: list[float]) -> dict[str, float]:
    """Statistiques descriptives (écart-type = 0 si moins de 2 valeurs)."""
    if not values:
        return dict.fromkeys(("mean", "median", "min", "max", "stdev"), 0.0)
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_files", nargs="+", help="Un ou plusieurs runs_*.csv")
    parser.add_argument("--out", default=None, help="CSV de sortie (sinon affichage console)")
    args = parser.parse_args()

    durations: dict[str, list[float]] = defaultdict(list)
    billables: dict[str, list[float]] = defaultdict(list)
    total_runs: dict[str, int] = defaultdict(int)
    successes: dict[str, int] = defaultdict(int)

    for path in args.csv_files:
        try:
            with open(path, newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    strategy = row.get("strategy", "?")
                    total_runs[strategy] += 1
                    if row.get("conclusion") == "success":
                        successes[strategy] += 1
                    duration = _to_float(row.get("duration_total_s", ""))
                    if duration is not None:
                        durations[strategy].append(duration)
                    billable = _to_float(row.get("billable_minutes_linux", ""))
                    if billable is not None:
                        billables[strategy].append(billable)
        except FileNotFoundError:
            sys.exit(f"Fichier introuvable : {path}")

    header = [
        "strategy", "n_runs", "success_count", "success_rate_pct",
        "duration_mean_s", "duration_median_s", "duration_min_s",
        "duration_max_s", "duration_stdev_s",
        "billable_minutes_mean", "billable_minutes_median",
    ]

    rows = []
    for strategy in sorted(total_runs):
        n = total_runs[strategy]
        dur = _stats(durations[strategy])
        bill = _stats(billables[strategy])
        rows.append([
            strategy, n, successes[strategy],
            round(100 * successes[strategy] / n, 1) if n else 0.0,
            round(dur["mean"], 1), round(dur["median"], 1),
            round(dur["min"], 1), round(dur["max"], 1), round(dur["stdev"], 1),
            round(bill["mean"], 1), round(bill["median"], 1),
        ])

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"Agrégation écrite dans {args.out}")
    else:
        print(",".join(header))
        for row in rows:
            print(",".join(str(cell) for cell in row))


if __name__ == "__main__":
    main()
