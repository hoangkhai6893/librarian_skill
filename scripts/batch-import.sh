#!/usr/bin/env bash
# batch-import.sh — Import curated skills/agents into library
# Usage: bash scripts/batch-import.sh [--force] [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"   # cd to agent-hub-index/

FLAGS=""
for arg in "$@"; do
    FLAGS="$FLAGS $arg"
done

import() {
    # $1=source, $2=name, $3=optional type (skill|agent)
    local src="$1" name="$2" type_flag=""
    if [[ -n "${3:-}" ]]; then
        type_flag="--type $3"
    fi
    echo "  Importing $src:$name..."
    python3 scripts/import-skill.py --source "$src" --skill "$name" $type_flag $FLAGS || true
}

echo "=== Batch Import: Agent Hub Library ==="
echo ""

# ── superpowers: 14 skills ───────────────────────────────────────────────────
echo "[1/6] superpowers — skills"
import superpowers brainstorming
import superpowers systematic-debugging
import superpowers test-driven-development
import superpowers executing-plans
import superpowers writing-plans
import superpowers verification-before-completion
import superpowers requesting-code-review
import superpowers receiving-code-review
import superpowers finishing-a-development-branch
import superpowers subagent-driven-development
import superpowers dispatching-parallel-agents
import superpowers using-git-worktrees
import superpowers writing-skills
import superpowers using-superpowers

echo "[1/6] superpowers — agents"
import superpowers code-reviewer agent

# ── everything-claude-code: 20 skills ─────────────────────────────────────────
echo ""
echo "[2/6] everything-claude-code — skills"
import everything-claude-code api-design
import everything-claude-code architecture-decision-records
import everything-claude-code codebase-onboarding
import everything-claude-code database-migrations
import everything-claude-code deep-research
import everything-claude-code deployment-patterns
import everything-claude-code docker-patterns
import everything-claude-code e2e-testing
import everything-claude-code frontend-patterns
import everything-claude-code golang-patterns
import everything-claude-code golang-testing
import everything-claude-code postgres-patterns
import everything-claude-code python-patterns
import everything-claude-code python-testing
import everything-claude-code pytorch-patterns
import everything-claude-code security-scan
import everything-claude-code security-review
import everything-claude-code tdd-workflow
import everything-claude-code backend-patterns
import everything-claude-code mcp-server-patterns

# ── gstack: 6 skills ──────────────────────────────────────────────────────────
echo ""
echo "[3/6] gstack — skills"
import gstack investigate
import gstack guard
import gstack canary
import gstack qa
import gstack ship
import gstack land-and-deploy

# ── get-shit-done: 7 agents ───────────────────────────────────────────────────
echo ""
echo "[4/6] get-shit-done — agents"
import get-shit-done gsd-planner agent
import get-shit-done gsd-executor agent
import get-shit-done gsd-debugger agent
import get-shit-done gsd-codebase-mapper agent
import get-shit-done gsd-verifier agent
import get-shit-done gsd-plan-checker agent
import get-shit-done gsd-advisor-researcher agent

# ── learn-claude-code: 3 skills ───────────────────────────────────────────────
echo ""
echo "[5/6] learn-claude-code — skills"
import learn-claude-code agent-builder
import learn-claude-code code-review
import learn-claude-code pdf

echo ""
echo "=== Batch Import Done ==="
echo "Total expected: ~50 entries (skills + agents)"
echo ""
echo "Skills in library:"
ls library/skills/ 2>/dev/null | wc -l | xargs echo "  Count:"
echo "Agents in library:"
ls library/agents/ 2>/dev/null | wc -l | xargs echo "  Count:"
