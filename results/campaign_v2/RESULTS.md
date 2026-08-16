# Exp.1 — Performance / coût A vs B vs C (campagne v2, 2026-08-16)

Runs : A n=10, B n=11, C n=11 (workflow_dispatch, branche v2-devsecops), **30/30 succès (fiabilité 100 %)**.
Durée = makespan (chemin critique, hors file d'attente). Coût = minutes facturables (ceil par job).

## Durées (secondes)
| | médiane | moyenne | σ | CV | plage |
|---|---|---|---|---|---|
| A (séquentiel, sans cache) | 77,5 | 90,8 | 38,6 | **42,6 %** | 68–199 |
| B (parallèle + cache) | 69,0 | 66,0 | 6,1 | 9,3 % | 54–71 |
| C (conditionnel, complet) | 69,0 | 68,7 | 3,9 | 5,7 % | 62–74 |

## Tests statistiques (durée, Mann-Whitney bilatéral, Holm)
- A vs B : p_Holm = 0,0014 **significatif** — Cliff δ = +0,88 (grand) — IC95 Δmédianes [+5 ; +22] s
- A vs C : p_Holm = 0,0014 **significatif** — Cliff δ = +0,86 (grand) — IC95 Δmédianes [+4 ; +21] s

## Coût (minutes facturables)
A ≈ 2 min/run · B ≈ 7 · C ≈ 7 → **B/C ≈ 3,5× le coût de A**.

## Décomposition par job (B/C) — le goulot
`Tests + coverage` ≈ 62–64 s domine ; les 5 autres contrôles (lint, SAST, secret, SBOM, SCA)
≈ 9–13 s chacun tournent **en parallèle sous l'ombre du job de test**. `SonarCloud` est bien
**skippé** en dispatch (exclu du chronométrage). Le makespan de B/C ≈ job de test + orchestration.

## Lecture honnête
1. B et C sont **significativement plus rapides** que A (effet grand), mais le **gain absolu est modeste**
   (~9 s de médiane) car le **chemin critique = le job de test** (non parallélisable) et A évite de
   répéter 6× l'installation.
2. Surtout, A est **beaucoup plus variable** (CV 42,6 % vs 6–9 %) : le séquentiel sans cache est
   imprévisible (démarrages à froid). B/C = **rapides ET stables**.
3. Ce gain **coûte ~3,5×** plus de minutes. Arbitrage vitesse+stabilité vs coût.
4. A→B/C mêle deux effets (parallélisme + cache) : une campagne cache-froid pour B les distinguerait.
