# Exp.3 — Durcissement d'image : slim vs distroless (mesuré en local)

Build **rootless** (podman, sans démon Docker) et scan **Trivy v0.74.0**, le
**2026-08-16**, même base de vulnérabilités pour les deux images. Les deux images
démarrent (uvicorn « Application startup complete » vérifié dans chaque conteneur).

## Images construites (base + dépendances Python) — `built_image_cve_comparison.csv`

| variante | image | CRITICAL | HIGH | MEDIUM | LOW | TOTAL | Taille |
|---|---|---|---|---|---|---|---|
| slim | `python:3.11-slim-bookworm` | 6 | 26 | 79 | 101 | 212 | 151,1 Mo |
| distroless | `gcr.io/distroless/python3-debian12:nonroot` | 2 | 46 | 114 | 71 | 233 | 71,2 Mo |

## Images de base seules — `base_image_cve_comparison.csv`

| variante | CRITICAL | HIGH | MEDIUM | LOW | TOTAL |
|---|---|---|---|---|---|
| slim | 6 | 20 | 75 | 97 | 198 |
| distroless | 2 | 40 | 110 | 67 | 219 |

## Lecture honnête (résultat non trivial)

- **Distroless est ~2× plus petite** (71 vs 151 Mo) et a **moins de CRITICAL**
  (2 vs 6), mais **plus de CVE au total** (233 vs 212) à cet instant.
- Le bénéfice de distroless n'est donc **pas** le *nombre* de CVE, mais la
  **réduction de surface d'attaque** (ni shell, ni gestionnaire de paquets, ni
  utilitaires → exploitation post-compromission bien plus difficile) et la
  **taille**. Le décompte dépend aussi de la **fraîcheur de rebuild** des images
  et de la base Trivy du jour.
- Les dépendances Python (fastapi, uvicorn, pydantic…) ajoutent quelques CVE
  identiques aux deux images (elles ne différencient pas slim de distroless).

## Reproduire

```bash
podman build -f Dockerfile            -t demo-cicd:slim .
podman build -f Dockerfile.distroless -t demo-cicd:distroless .
podman save -o img.tar demo-cicd:slim
trivy image --input img.tar --scanners vuln --severity CRITICAL,HIGH,MEDIUM,LOW
```
Le scan des images de base directement : `trivy image <image_de_base>`.
