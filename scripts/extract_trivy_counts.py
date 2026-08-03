#!/usr/bin/env python3
"""Extrait le nombre de vulnérabilités par sévérité depuis des rapports Trivy JSON.

Lit un ou plusieurs fichiers JSON produits par Trivy (format `json`, scan `fs`) et
compte les vulnérabilités par sévérité (CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN).
Exporte un CSV, ou affiche un résumé si --out n'est pas fourni.

Utilise uniquement la bibliothèque standard (json, csv).

Exemple :
    python scripts/extract_trivy_counts.py trivy-fs.json --strategy A --out trivy_counts.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]


def count_severities(path: str) -> dict[str, int]:
    """Compte les vulnérabilités par sévérité dans un rapport Trivy."""
    counts = dict.fromkeys(SEVERITIES, 0)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        sys.exit(f"Fichier introuvable : {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"JSON invalide dans {path} : {exc}")

    for result in data.get("Results") or []:
        for vuln in result.get("Vulnerabilities") or []:
            severity = (vuln.get("Severity") or "UNKNOWN").upper()
            if severity not in counts:
                severity = "UNKNOWN"
            counts[severity] += 1
    return counts


def _guess_strategy(path: str) -> str:
    """Devine la stratégie (A/B/C) d'après le nom de fichier, sinon '?'."""
    name = path.lower()
    for letter in ("a", "b", "c"):
        if f"_{letter}" in name or f"-{letter}" in name:
            return letter.upper()
    return "?"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("json_files", nargs="+", help="Un ou plusieurs rapports Trivy JSON")
    parser.add_argument("--strategy", default=None,
                        help="Étiquette A/B/C (sinon devinée du nom de fichier)")
    parser.add_argument("--out", default=None, help="CSV de sortie (sinon affichage console)")
    args = parser.parse_args()

    header = ["source_file", "strategy", "critical", "high", "medium", "low", "unknown", "total"]
    rows = []
    for path in args.json_files:
        counts = count_severities(path)
        strategy = args.strategy or _guess_strategy(path)
        total = sum(counts.values())
        rows.append([
            path, strategy,
            counts["CRITICAL"], counts["HIGH"], counts["MEDIUM"],
            counts["LOW"], counts["UNKNOWN"], total,
        ])

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"Comptage écrit dans {args.out}")
    else:
        print(",".join(header))
        for row in rows:
            print(",".join(str(cell) for cell in row))


if __name__ == "__main__":
    main()
