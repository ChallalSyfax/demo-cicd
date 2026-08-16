#!/usr/bin/env python3
"""Analyse statistique des durées de pipeline (Exp.1).

Lit les fichiers ``runs_<STRATEGIE>.csv`` produits par ``collect_metrics.py`` et
compare les stratégies sur la DURÉE d'exécution (chemin critique, colonne
``duration_total_s``), avec une approche non paramétrique adaptée aux petits
échantillons :

- statistiques descriptives (médiane, IQR, moyenne, écart-type, CV) ;
- test de Mann-Whitney U (chaque stratégie vs baseline) ;
- taille d'effet de Cliff (delta) avec interprétation ;
- IC à 95 % de la différence de médianes (bootstrap, graine fixe) ;
- correction de Holm-Bonferroni sur la famille de tests déclarée.

Les MINUTES FACTURABLES sont déterministes : rapportées comme faits exacts
(médiane, total), JAMAIS testées statistiquement.

Prérequis : ``pip install -r scripts/requirements-stats.txt``

Exemple :
    python scripts/analyze_durations.py --results-dir results/campaign_controlled \\
        --out results/campaign_controlled/analysis_durations.csv
"""

from __future__ import annotations

import argparse
import csv
import os

import numpy as np
from scipy.stats import mannwhitneyu


def load_metric(path: str, metric: str, only_success: bool = True) -> np.ndarray:
    """Charge une colonne numérique d'un runs_*.csv (runs réussis uniquement)."""
    values: list[float] = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if only_success and row.get("conclusion") != "success":
                continue
            raw = row.get(metric, "")
            if raw not in ("", None):
                values.append(float(raw))
    return np.array(values, dtype=float)


def describe(values: np.ndarray) -> dict[str, float]:
    """Statistiques descriptives d'un échantillon."""
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if values.size > 1 else 0.0
    return {
        "n": int(values.size),
        "median": float(np.median(values)),
        "q1": float(np.percentile(values, 25)),
        "q3": float(np.percentile(values, 75)),
        "mean": mean,
        "std": std,
        "cv": (std / mean) if (values.size > 1 and mean) else 0.0,
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> tuple[float, str]:
    """Taille d'effet de Cliff : (#(x>y) − #(x<y)) / (nx·ny)."""
    greater = sum(int(np.sum(xi > y)) for xi in x)
    lesser = sum(int(np.sum(xi < y)) for xi in x)
    total = x.size * y.size
    delta = (greater - lesser) / total if total else 0.0
    magnitude = abs(delta)
    if magnitude < 0.147:
        label = "négligeable"
    elif magnitude < 0.33:
        label = "petite"
    elif magnitude < 0.474:
        label = "moyenne"
    else:
        label = "grande"
    return delta, label


def bootstrap_median_diff_ci(
    x: np.ndarray, y: np.ndarray, n_boot: int = 10000, seed: int = 42, alpha: float = 0.05
) -> tuple[float, float]:
    """IC de la différence de médianes (médiane_x − médiane_y) par bootstrap."""
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        bx = rng.choice(x, size=x.size, replace=True)
        by = rng.choice(y, size=y.size, replace=True)
        diffs[i] = np.median(bx) - np.median(by)
    lo = float(np.percentile(diffs, 100 * alpha / 2))
    hi = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
    return lo, hi


def holm_bonferroni(
    pairs: list[tuple[str, float]], alpha: float = 0.05
) -> dict[str, tuple[float, bool]]:
    """Correction de Holm-Bonferroni. Renvoie {label: (p_ajusté, rejet)}."""
    order = sorted(range(len(pairs)), key=lambda i: pairs[i][1])
    result: dict[str, tuple[float, bool]] = {}
    running_max = 0.0
    for rank, idx in enumerate(order):
        label, p = pairs[idx]
        p_adj = max(min(1.0, p * (len(pairs) - rank)), running_max)  # monotone
        running_max = p_adj
        result[label] = (p_adj, p_adj <= alpha)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--results-dir", required=True, help="Dossier des runs_*.csv")
    parser.add_argument("--strategies", nargs="+", default=["A", "B", "C"])
    parser.add_argument("--baseline", default="A", help="Stratégie de référence")
    parser.add_argument("--out", default=None, help="CSV de sortie (optionnel)")
    args = parser.parse_args()

    durations: dict[str, np.ndarray] = {}
    billable: dict[str, np.ndarray] = {}
    for strat in args.strategies:
        path = os.path.join(args.results_dir, f"runs_{strat}.csv")
        if not os.path.exists(path):
            raise SystemExit(f"fichier manquant : {path}")
        durations[strat] = load_metric(path, "duration_total_s")
        billable[strat] = load_metric(path, "billable_minutes_linux")

    print("=== Durée d'exécution (s) — descriptif ===")
    for strat in args.strategies:
        d = describe(durations[strat])
        print(
            f"{strat}: n={d['n']} médiane={d['median']:.1f} "
            f"IQR=[{d['q1']:.1f};{d['q3']:.1f}] moy={d['mean']:.1f} "
            f"σ={d['std']:.1f} CV={d['cv']:.1%} [{d['min']:.0f};{d['max']:.0f}]"
        )

    print("\n=== Minutes facturables (déterministe, NON testé) ===")
    for strat in args.strategies:
        b = billable[strat]
        print(f"{strat}: médiane={np.median(b):.0f}  total={np.sum(b):.0f}  (n={b.size})")

    base = args.baseline
    pairs: list[tuple[str, float]] = []
    details: dict[str, tuple[float, float, str, float, float]] = {}
    for strat in args.strategies:
        if strat == base:
            continue
        x, y = durations[base], durations[strat]
        _, p = mannwhitneyu(x, y, alternative="two-sided")
        delta, magnitude = cliffs_delta(x, y)
        lo, hi = bootstrap_median_diff_ci(x, y)
        label = f"{base} vs {strat}"
        pairs.append((label, float(p)))
        details[label] = (float(p), delta, magnitude, lo, hi)

    holm = holm_bonferroni(pairs)
    print(f"\n=== Durée : comparaisons vs {base} (Mann-Whitney bilatéral) ===")
    for label, (p, delta, magnitude, lo, hi) in details.items():
        p_adj, reject = holm[label]
        verdict = "SIGNIFICATIF" if reject else "non significatif"
        print(
            f"{label}: p={p:.4f} p_Holm={p_adj:.4f} [{verdict} @5%] | "
            f"Cliff δ={delta:+.3f} ({magnitude}) | "
            f"IC95 Δmédianes=[{lo:+.1f};{hi:+.1f}] s"
        )

    print(
        "\nRappel : un résultat non significatif est un résultat pré-enregistré, "
        "pas un échec — la durée est bornée par le chemin critique."
    )

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["comparison", "p_value", "p_holm", "significant_5pct",
                 "cliffs_delta", "effect_magnitude", "ci95_low_s", "ci95_high_s"]
            )
            for label, (p, delta, magnitude, lo, hi) in details.items():
                p_adj, reject = holm[label]
                writer.writerow(
                    [label, f"{p:.6f}", f"{p_adj:.6f}", reject,
                     f"{delta:.4f}", magnitude, f"{lo:.2f}", f"{hi:.2f}"]
                )
        print(f"\nRésumé écrit dans {args.out}")


if __name__ == "__main__":
    main()
