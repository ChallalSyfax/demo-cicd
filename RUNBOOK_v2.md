# Runbook v2 — ce qu'il faut lancer sur GitHub

> Branche `v2-devsecops`. Tout le code est prêt ; il reste à **pousser** puis à
> **lancer les workflows** pour produire les vrais chiffres. Rien n'a été poussé.

## 0. Prérequis (une fois)

- Pousser la branche : `git push -u origin v2-devsecops`.
- Secret `SONAR_TOKEN` dans les *Settings → Secrets* du dépôt (pour le quality gate).
  Sans lui, l'analyse Sonar est sautée (le gate ne bloque pas).
- GHCR : rien à faire (le `GITHUB_TOKEN` du workflow a `packages: write`). Après le
  premier push d'image, penser à rendre le package **public** si tu veux que
  `cosign verify` / `trivy image` tirent sans authentification (sinon ils utilisent
  le login du workflow, ça marche aussi).

## 1. Exp.1 — Performance / coût (A vs B vs C)

Lancer **n fois** chacun des workflows en `workflow_dispatch` (onglet Actions →
« Run workflow ») :
- Pipeline A - Sequential
- Pipeline B - Parallel + Cache
- Pipeline C - Conditional (mode complet en dispatch)

Conseils de protocole (cf. mémoire) : **ordre contre-balancé** (A,B,C,C,B,A…),
étalé sur plusieurs plages horaires ; d'abord un **pilote de 5-8 runs** pour régler
`CALIBRATION_N` (dans les workflows, viser un job `test` ~20-40 s) et fixer `n`.

Collecte + analyse :
```bash
export GITHUB_TOKEN=ghp_xxx
for wf in pipeline-a-sequential pipeline-b-parallel-cache pipeline-c-conditional; do
  python scripts/collect_metrics.py --repo ChallalSyfax/demo-cicd \
    --workflow $wf.yml --event workflow_dispatch --limit 30 --out-dir results/campaign_v2
done
pip install -r scripts/requirements-stats.txt
python scripts/analyze_durations.py --results-dir results/campaign_v2 \
  --out results/campaign_v2/analysis_durations.csv
```
Rappel : la **durée** (makespan) peut rester non significative — c'est une loi du
chemin critique, pas un échec. Le **coût ×5** (minutes facturables) est le chiffre
exact et déterministe.

## 2. Exp.2 — Différenciateur sécurité (fenêtre d'exposition de C)

But : montrer que **C ne détecte pas** une dépendance vulnérable **sur une PR**
(contrôles lourds différés), alors que la chaîne complète la détecte sur `main`.

1. Créer une branche, ajouter une **dépendance à CVE connue** dans `requirements.txt`
   (DÉTECTION seulement, aucune exploitation — retirée après mesure). Candidats
   confirmés dans la base Trivy (choisir 1, vérifier le build) :
   - `PyYAML==5.3.1` (CVE-2020-14343, HIGH) — défaut suggéré ;
   - `requests==2.19.1` (plusieurs CVE) ; `urllib3==1.25.8`.
2. Ouvrir une **PR vers main** → observer : le job `trivy` (SCA) est **skippé**
   (fenêtre d'exposition) ; `test`/`lint`/`sast` + gate Sonar tournent.
3. Merger (ou `workflow_dispatch`) → la chaîne complète tourne, Trivy **remonte** la
   CVE. Consigner le **point de détection** par stratégie (matrice).
4. Retirer la dépendance vulnérable après mesure.

## 3. Exp.3 — Durcissement d'image (slim vs distroless)

Lancer **Supply chain (Couche 2)** en `workflow_dispatch`. Il build les 2 variantes,
les scanne (Trivy image), les signe (Cosign), génère la provenance SLSA et vérifie
l'admission. Récupérer les artefacts `supply-chain-slim` / `supply-chain-distroless`
(rapports Trivy + taille) et comparer nombre de CVE OS + taille.

## 4. Exp.4 — Portes bloquantes

- **Quality gate** : sur une PR, un commit qui fait chuter la couverture sous le
  seuil Sonar → le job `sonar` échoue (gate bloquant).
- **Admission** : dans `supply-chain.yml`, l'étape `cosign verify` / `gh attestation
  verify` échoue si l'image n'est pas signée par l'identité OIDC du dépôt.

## Risques de premier run (à surveiller — non testables hors GitHub)

- **Cosign keyless / SLSA** dépendent de Sigstore (Rekor/Fulcio) + OIDC. Si échec sur
  le free tier : les décrire comme démontrés une fois, ou relégués en perspective
  (repli honnête assumé dans le mémoire).
- **GHCR package privé par défaut** : `trivy image` / `cosign verify` s'appuient sur
  le login du workflow (OK) ; rendre le package public simplifie.
- **Versions d'actions** `docker/*`, `sigstore/cosign-installer@v3.7.0`,
  `actions/attest-build-provenance@v2` : à confirmer au premier run.
- **SONAR_TOKEN absent** → gate sauté (non bloquant).
