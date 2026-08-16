#!/usr/bin/env bash
# Déclenche la campagne de mesure Exp.1 : N runs par stratégie (A/B/C), en
# ORDRE CONTRE-BALANCÉ (A B C C B A ...) et espacés dans le temps, pour
# neutraliser le confond temporel de la plateforme et limiter la contention.
#
# Prérequis : un PAT GitHub avec le scope "repo" (classique) ou "Actions:write".
#   export GITHUB_TOKEN=ghp_xxxxx
#   bash scripts/run_campaign.sh [N] [DELAY_S]
# Ex. : bash scripts/run_campaign.sh 10 90   # 10 runs/strat, 90 s entre chaque
set -euo pipefail

REPO="${REPO:-ChallalSyfax/demo-cicd}"
REF="${REF:-v2-devsecods}"
N="${1:-10}"
DELAY="${2:-90}"
: "${GITHUB_TOKEN:?Erreur : export GITHUB_TOKEN=<ton PAT> avant de lancer.}"

declare -A WF=(
  [A]=pipeline-a-sequential.yml
  [B]=pipeline-b-parallel-cache.yml
  [C]=pipeline-c-conditional.yml
)
ORDER=(A B C C B A)
declare -A done=([A]=0 [B]=0 [C]=0)

trigger() {
  curl -sS -X POST \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/$REPO/actions/workflows/$1/dispatches" \
    -d "{\"ref\":\"$REF\"}"
}

total=$((N * 3))
count=0
i=0
echo "Campagne : $N runs/stratégie ($total au total), ref=$REF, délai=${DELAY}s"
while (( done[A] < N || done[B] < N || done[C] < N )); do
  s=${ORDER[$((i % ${#ORDER[@]}))]}
  i=$((i + 1))
  if (( done[$s] >= N )); then continue; fi
  count=$((count + 1))
  echo "[$count/$total] déclenche $s (${WF[$s]})  $(date +%H:%M:%S)"
  trigger "${WF[$s]}"
  done[$s]=$((done[$s] + 1))
  if (( count < total )); then sleep "$DELAY"; fi
done
echo "OK : $total runs déclenchés. Attends leur fin (onglet Actions), puis lance la collecte + l'analyse."
