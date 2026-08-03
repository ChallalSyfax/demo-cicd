# Protocole de mesure

Ce document décrit le protocole expérimental utilisé pour comparer trois stratégies
de pipeline CI/CD DevSecOps sur GitHub Actions. Il est pensé pour être repris
directement dans le chapitre méthodologique du mémoire.

---

## 1. But de l'expérimentation

L'objectif est de **comparer trois stratégies d'orchestration** d'un même pipeline
CI/CD DevSecOps, appliqué à une petite application Flask, et de mesurer leur impact
sur la **durée**, le **coût en minutes runner**, la **fiabilité** et la **sécurité**
(vulnérabilités détectées).

Point important : **l'application n'est pas l'objet d'étude**. Elle sert uniquement de
support. Ce que l'on compare, ce sont les **stratégies de pipeline**, pas la qualité de
l'application. Le travail réalisé par le pipeline (tests, couverture, analyse qualité,
SBOM, scan de vulnérabilités) est **identique** dans les trois cas : seule
l'orchestration change. C'est cette contrainte qui rend la comparaison valide.

---

## 2. Rôle des trois stratégies

| Stratégie | Fichier | Principe | Question posée |
|-----------|---------|----------|----------------|
| **A** | `pipeline-a-sequential.yml` | Un seul job, étapes en séquence, **sans cache** | Combien coûte le pipeline « naïf » de référence ? |
| **B** | `pipeline-b-parallel-cache.yml` | Plusieurs **jobs parallèles** + **cache pip** | La parallélisation et le cache font-ils gagner du temps, et à quel coût ? |
| **C** | `pipeline-c-conditional.yml` | Contrôles **adaptés au contexte** (PR / main / manuel) | Peut-on économiser des ressources en n'exécutant que les contrôles pertinents ? |

- **A — baseline séquentielle.** Sert de point de comparaison. Volontairement non
  optimisée : pas de cache, pas de parallélisme.
- **B — parallélisation + cache.** Même travail que A, mais `test`, `lint`, `sbom` et
  `trivy` s'exécutent en parallèle, et les dépendances Python sont mises en cache.
  On attend une baisse du temps « horloge », à discuter face au coût facturé.
- **C — conditionnel.** Change de logique : il n'essaie pas d'aller plus vite, mais
  d'exécuter **le bon niveau de contrôle au bon moment**. Sur une pull request, seuls
  les contrôles rapides tournent ; sur `main` ou en lancement manuel, la chaîne
  complète s'exécute.

---

## 3. Pourquoi lancer les campagnes en `workflow_dispatch`

Pour comparer A, B et C **de façon honnête**, il faut que les trois exécutent
exactement le **même ensemble de contrôles**. Or C adapte son comportement selon le
déclencheur : une pull request ne lance pas le SBOM ni Trivy.

Le mode `workflow_dispatch` (déclenchement manuel) résout ce problème :

- les **trois** workflows y exécutent la **chaîne complète** ;
- on maîtrise **quand** chaque run part (utile pour une campagne régulière) ;
- on évite les runs parasites liés à des `push` ou des PR pendant la mesure.

**Règle :** la comparaison chiffrée A vs B vs C se fait uniquement sur des runs
`workflow_dispatch`. Les runs `pull_request` et `push` de C sont analysés séparément
(voir §8 et §9).

---

## 4. Combien de runs par stratégie

**Au moins 10 runs par stratégie**, idéalement davantage.

Un seul run ne prouve rien : les runners GitHub sont des machines partagées, donc deux
exécutions identiques peuvent différer de plusieurs dizaines de secondes. Répéter les
runs permet de calculer une **moyenne** et un **écart-type**, et donc de raisonner sur
une tendance plutôt que sur une valeur isolée.

Concrètement : lancer 10 fois A, 10 fois B, 10 fois C en `workflow_dispatch`, puis
collecter les métriques.

---

## 5. Distinguer cache froid et cache chaud

Le cache (stratégies B et C) change fortement les résultats :

- **Cache froid** : premier run après création ou expiration du cache. Les dépendances
  sont téléchargées depuis PyPI → durée plus longue. C'est aussi le cas quand la clé de
  cache change (modification de `requirements-dev.txt`).
- **Cache chaud** : runs suivants, où les dépendances sont restaurées depuis le cache →
  installation quasi instantanée.

**Recommandation :** lors d'une campagne, **noter (ou exclure) le premier run** de B et
C, qui part cache froid, pour ne pas fausser la moyenne. On peut aussi présenter les
deux cas séparément dans le mémoire (« premier run » vs « runs stabilisés »), ce qui
illustre justement l'apport du cache.

---

## 6. Métriques à collecter

| Métrique | Définition | Source |
|----------|------------|--------|
| **Durée totale (wall-clock)** | `updated_at − run_started_at` du run | API Actions |
| **Durée par job** | `completed_at − started_at` de chaque job | API Actions |
| **Statut / conclusion** | `success`, `failure`, `cancelled` | API Actions |
| **Taux de succès** | proportion de runs en `success` | calculé |
| **Minutes runner (estimées)** | ∑ `ceil(durée_job / 60)` × 1 (Linux) | calculé |
| **Vulnérabilités Trivy** | nombre par sévérité : CRITICAL, HIGH, MEDIUM, LOW | rapport Trivy JSON |

Remarques :

- La **durée par job** est essentielle pour B et C : elle montre quels jobs tournent en
  parallèle et lesquels attendent (`sonar` attend `test`).
- Les **minutes runner** sont une **estimation** reproduisant l'arrondi de GitHub
  (chaque job arrondi à la minute supérieure), pas la facture exacte (voir §9).
- Le **comptage Trivy** sert surtout de **contrôle de cohérence** : à dépendances
  identiques, A, B et C doivent détecter les mêmes vulnérabilités. C'est une dimension
  sécurité, pas un critère qui départage les stratégies.

---

## 7. Utilisation des scripts de mesure

Les scripts se trouvent dans `scripts/` et n'utilisent que la bibliothèque standard de
Python (aucune dépendance à installer). Un token GitHub est nécessaire :

```bash
export GITHUB_TOKEN=ghp_xxxxxxxx
```

**Collecter les durées / coûts / statuts** (pour chaque stratégie) :

```bash
python scripts/collect_metrics.py --repo ChallalSyfax/demo-cicd \
    --workflow pipeline-a-sequential.yml --event workflow_dispatch --limit 10
python scripts/collect_metrics.py --repo ChallalSyfax/demo-cicd \
    --workflow pipeline-b-parallel-cache.yml --event workflow_dispatch --limit 10
python scripts/collect_metrics.py --repo ChallalSyfax/demo-cicd \
    --workflow pipeline-c-conditional.yml --event workflow_dispatch --limit 10
```

→ produit `runs_A.csv`, `jobs_A.csv`, etc.

**Agréger les résultats** :

```bash
python scripts/aggregate_metrics.py runs_A.csv runs_B.csv runs_C.csv --out aggregate.csv
```

→ un tableau par stratégie : nombre de runs, taux de succès, moyenne/médiane/min/max/
écart-type de la durée, moyenne des minutes estimées.

**Compter les vulnérabilités Trivy** (rapports téléchargés manuellement depuis les
artefacts) :

```bash
python scripts/extract_trivy_counts.py trivy_A.json trivy_B.json trivy_C.json \
    --out trivy_counts.csv
```

---

## 8. Interprétation des résultats

Quelques principes de lecture, à reprendre dans l'analyse :

- **A vs B — temps et coût.** On s'attend à ce que B réduise la **durée horloge** grâce
  au parallélisme et au cache. Mais attention : les minutes **facturées** peuvent
  **augmenter**, car chaque job parallèle refait `checkout` + `setup Python` et est
  facturé à part, arrondi à la minute. C'est l'**arbitrage temps vs coût** à mettre en
  avant : « plus rapide » ne veut pas dire « moins cher ».
- **C — deux temps de lecture.**
  1. En `workflow_dispatch` (chaîne complète), C se compare directement à A et B.
  2. Sur `pull_request`, C ne lance que les contrôles rapides → on mesure les
     **ressources économisées** par rapport à une chaîne complète. C'est là qu'est
     l'intérêt de la stratégie conditionnelle.
- **Toujours lire moyenne + écart-type.** Un écart de quelques secondes entre deux
  stratégies n'est pas significatif si l'écart-type est du même ordre.
- **Sécurité.** Vérifier que le comptage Trivy est **cohérent** entre A, B et C ; toute
  différence signalerait un problème de périmètre de scan, pas un avantage de stratégie.

---

## 9. Limites méthodologiques

À mentionner explicitement dans le mémoire pour rester honnête sur la portée des
résultats :

1. **Variabilité des runners GitHub.** Machines partagées, matériel et réseau non
   maîtrisés → bruit sur les durées. D'où la répétition des runs et la lecture en
   moyenne + écart-type. Les petits écarts ne doivent pas être sur-interprétés.
2. **Latence SonarCloud.** SonarCloud est un service externe : sa durée dépend du réseau
   et de la charge du service. Il faut garder sa présence **constante** sur toute la
   campagne (token configuré ou non), sinon les runs ne sont plus comparables.
3. **Base de vulnérabilités Trivy évolutive.** La base est mise à jour très
   régulièrement. À dépendances identiques, le nombre de vulnérabilités peut donc
   **varier selon la date** du scan. Il faut noter la **fenêtre temporelle** de mesure.
4. **Petit échantillon.** Une dizaine de runs dans un environnement non contrôlé
   n'autorise que des statistiques **descriptives** (tendances), pas de conclusions à
   prétention statistique forte.
5. **Coût estimé, pas facture exacte.** Les minutes runner sont **calculées** à partir
   des durées de jobs (arrondi à la minute supérieure, coefficient 1 pour Linux). C'est
   une approximation de la logique de facturation de GitHub, pas la facture réelle.
6. **Comparaison de C en deux temps.** C ne se compare à A et B qu'en mode manuel
   (chaîne complète). Son comportement conditionnel (PR vs `main`) doit être analysé
   **séparément**, comme une démonstration d'économie de ressources, et non mélangé à la
   comparaison chronométrée A/B/C.

---

*Ce protocole accompagne les trois workflows (`.github/workflows/`) et les scripts de
mesure (`scripts/`) du dépôt.*
