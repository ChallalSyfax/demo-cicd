# Exp.2 — Différenciateur sécurité : fenêtre d'exposition de la stratégie C

Démonstration déterministe (2026-08-16, Trivy v0.74.0, scan local, défensif — aucune exploitation).

## Détection prouvée
Injection d'une dépendance à CVE connue dans requirements.txt : `PyYAML==5.3.1`.
- Baseline (fastapi, uvicorn, python-multipart) : **7 CVE**.
- Avec injection : **8 CVE**. Delta = **CVE-2020-14343 (CRITICAL)** sur PyYAML 5.3.1.
→ Trivy détecte bien la vulnérabilité injectée.

## Le différenciateur = le MOMENT, pas la capacité
Les trois stratégies utilisent le MÊME scanner (Trivy) : l'orchestration ne change pas la
*capacité* de détection, seulement *quand* le scan a lieu.
- **A, B** (dispatch) : le job SCA tourne à chaque exécution → la CVE est détectée **immédiatement**.
- **C** : le job SCA est conditionnel (`if: github.event_name != 'pull_request'`). Sur une
  **pull request**, il est **skippé** → la CRITICAL n'est PAS détectée au moment de la PR ;
  elle ne l'est qu'au **push sur main** (ou dispatch complet).

## Fenêtre d'exposition (modèle paramétrique)
Fenêtre = délai entre l'introduction de la dépendance vulnérable (dans une PR) et sa détection
(au merge sur main). Pour A/B : **nulle**. Pour C : **= délai de revue/merge** (scénarios
illustratifs : merge immédiat → ~0 ; merge quotidien → jusqu'à ~1 j ; merge hebdo → jusqu'à ~7 j).
Arbitrage : C accélère le retour sur PR (pas de scan lourd) au prix de cette fenêtre.

## Preuve « en direct » (optionnelle)
Confirmable sur GitHub : ouvrir une PR avec la dépendance vulnérable → le job SCA de C apparaît
**skippé** ; au merge/dispatch, il **remonte la CVE**. (Nécessite les workflows v2 sur `main`.)
