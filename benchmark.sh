#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
SHOP_DIR="$REPO_ROOT/benchmarks/shop"
WORKFLOW_ID="end_to_end"
WORKFLOW_FILE="$SHOP_DIR/workflows/${WORKFLOW_ID}.md"
AGENT_YAML="$SHOP_DIR/AGENT.yaml"

[[ -f "$REPO_ROOT/main.py" ]]  || { echo "main.py not found at $REPO_ROOT" >&2; exit 1; }
[[ -d "$SHOP_DIR" ]]           || { echo "shop dir not found: $SHOP_DIR" >&2; exit 1; }
[[ -f "$WORKFLOW_FILE" ]]      || { echo "workflow not found: $WORKFLOW_FILE" >&2; exit 1; }
[[ -f "$AGENT_YAML" ]]         || { echo "AGENT.yaml not found: $AGENT_YAML" >&2; exit 1; }

cd "$SHOP_DIR"

echo "==> workspace: $SHOP_DIR"
echo "==> workflow:  $WORKFLOW_FILE"
echo

echo "==> step 1/2: init"
uv run --project "$REPO_ROOT" python "$REPO_ROOT/main.py" init

echo
echo "==> step 2/2: run workflow"
exec uv run --project "$REPO_ROOT" python "$REPO_ROOT/main.py" run workflow "$WORKFLOW_ID"