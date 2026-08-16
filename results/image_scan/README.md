# Exp.3 — Scan des images de base (slim vs distroless)

Scan réalisé **en local** avec Trivy (sans démon Docker : Trivy tire les images
depuis le registre), le **2026-08-16**, Trivy **v0.74.0**, base de vulnérabilités
du jour. Les deux images sont scannées le même jour avec la même base CVE.

| variante | image | CRITICAL | HIGH | MEDIUM | LOW | TOTAL |
|---|---|---|---|---|---|---|
| slim | python:3.11-slim-bookworm | 6 | 20 | 75 | 97 | 198 |
| distroless | gcr.io/distroless/python3-debian12:nonroot | 2 | 40 | 110 | 67 | 219 |

**Lecture honnête.** Distroless a **moins de CRITICAL** mais **plus de CVE au total**
à cet instant. Le bénéfice de distroless n'est donc pas le *nombre* de CVE mais la
**réduction de surface d'attaque** (ni shell, ni gestionnaire de paquets, ni
utilitaires → exploitation post-compromission plus difficile). Le décompte dépend
aussi de la **fraîcheur de rebuild** des images et évolue avec la base Trivy.

**Portée.** Ceci scanne les **images de base** (couche OS), où se joue le différenciateur
slim/distroless. L'image **construite** (base + dépendances Python) est scannée en CI
par le workflow `supply-chain.yml` (vue complète, incluant les CVE des dépendances).

Reproduire : `trivy image --scanners vuln --severity CRITICAL,HIGH,MEDIUM,LOW <image>`
