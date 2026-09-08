#!/usr/bin/env bash
set -euo pipefail

: "${ARBM_WORKSPACE:=$(pwd)}"
: "${ZERO_SPEND_MODE:=HARD}"
: "${ARBM_EXTERNAL_EXEC:=true}"
: "${ARBM_FREE_CAPACITY_PROVEN:?ARBM_FREE_CAPACITY_PROVEN must be true after host qualification}"
: "${ARBM_RUNNER_NAME:=arbm-external}"

export ARBM_WORKSPACE ZERO_SPEND_MODE ARBM_EXTERNAL_EXEC
export ARBM_FREE_CAPACITY_PROVEN ARBM_RUNNER_NAME

python arbm_executor_contract.py | tee executor-context.json
python -m unittest -v test_arbm_executor_contract.py
python -m py_compile arbm_executor_contract.py p9-evaluator-observe.py

mkdir -p p9-eval
cp executor-context.json p9-eval/executor-context.json
sha256sum p9-eval/executor-context.json > p9-eval/executor-context.sha256
