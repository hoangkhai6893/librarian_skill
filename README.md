# 📚 Librarian

> Your curated skill & agent library for AI coding assistants. One library. Any project. Any assistant.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue)]()
[![Claude Code](https://img.shields.io/badge/Claude%20Code-supported-6f42c1)]()
[![OpenCode](https://img.shields.io/badge/OpenCode-skills%20only-yellow)]()
[![GitHub Copilot CLI](https://img.shields.io/badge/Copilot%20CLI-skills%20only-yellow)]()
[![VS Code Copilot Chat](https://img.shields.io/badge/VS%20Code%20Copilot-manual-lightgrey)]()
[![Codex CLI](https://img.shields.io/badge/Codex%20CLI-skills%20only-yellow)]()

---

## 🤔 The Problem

Every new project starts from zero. Again.

You've built great AI workflows before — TDD, systematic debugging, security scanning, code review practices. But when you start a fresh project, **none of it travels with you**.

**What you face:**

- ❌ **No consistent toolkit** — Each project gets a different skill set. One has TDD, another doesn't.
- ❌ **Skill discovery is hard** — You know certain skills exist but can't remember which one helps with what.
- ❌ **Copy-paste chaos** — Manually copying `.md` files from project to project is error-prone and forgettable.
- ❌ **No cross-project consistency** — Your best debugging workflow from last quarter? Gone.
- ❌ **Platform fragmentation** — Claude Code, OpenCode, Copilot each need different file formats and paths.

**You shouldn't have to rebuild your AI toolkit for every project.**

---

## 🎯 What Is Librarian?

Librarian is a **curated skill/agent warehouse + publishing pipeline** — not a search engine over hundreds of raw sources. `library/` holds ~73 hand-curated entries (skills, agents, stacks, collections); scripts **copy** the ones a project needs straight into that project's own directory. Nothing is symlinked — once published, a project keeps working even if this repo is deleted.

Two different jobs happen here:

- **Consumer** — you have a project and need skills. Ask `/librarian recommend` or `/librarian stack <id>`, get a short shortlist with reasons, confirm, done.
- **Curator** — you're growing the library itself. `/librarian import <path>` scans an external repo of skills/agents and, after you pick which ones, folds them into `library/` for every future project to use.

**How publishing actually works:**

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  /librarian command │     │  library/ (this repo│     │   Your Project      │
│                     │     │  = the warehouse)   │     │                     │
│  recommend / stack  │────▶│  skills/  agents/   │──copy──▶ .claude/skills/  │
│  publish / import   │     │  stacks/ collections│──copy──▶ .opencode/skills/│
│                     │     │  catalog.json       │──copy──▶ .github/copilot/ │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘

1. You open a project and type: /librarian recommend
2. detect-project.py scans package.json / CMakeLists.txt / requirements.txt / etc.
   and matches it against library/stacks/*.yaml
3. Librarian shows a short shortlist with WHY for each skill — it never auto-publishes
4. You confirm → publish-to-project.py copies the chosen SKILL.md files in and
   records them in library-manifest.yaml
```

**In 30 seconds (Claude Code):** Open project → type `/librarian recommend` → confirm → skills land in `.claude/skills/`.

> The `/librarian` slash command ships two ways — as a Claude Code plugin, and auto-attached to every publish on any platform. See [Two Copies of `/librarian`](#two-copies-of-librarian) for why, and [Known Limitations](#-known-limitations) for what's verified where.

---

## 📥 Installation
### Claude
Librarian ships as a self-hosted Claude Code plugin marketplace — no separate installer needed.

```
/plugin marketplace add https://github.com/hoangkhai6893/librarian_skill.git
/plugin install librarian_skill@librarian_skill
```

Cloned locally instead? Point at the folder:

```
/plugin marketplace add /path/to/librarian_skill
/plugin install librarian_skill@librarian_skill
```

Requires Python 3.12+. The `pyyaml` dependency (`requirements.txt`) is auto-installed on first session start if missing.

### OpenCode
git clone https://github.com/hoangkhai6893/librarian_skill.git 
cd librarian_skill 
cp -rf  commands/librarian.md ~/.config/opencode/commands/

**Skills need no conversion at all** — OpenCode reads Claude Code's `.claude/skills/` directory directly (verified against opencode.ai docs), alongside its own `.opencode/skills/`. So the simplest path is to just publish with the Claude Code target, even without installing the plugin:
OpenCode will pick up `.claude/skills/` on its own. If you'd rather use OpenCode-native paths, `--platform opencode` writes to `.opencode/skills/{id}/SKILL.md` instead — functionally equivalent.

**`/librarian` as a command:** OpenCode's real custom-command format (`.opencode/commands/*.md`, frontmatter needs a `template` field) is different from `library/agents/librarian.md` — that file publishes to `.opencode/agents/librarian.md`, which OpenCode treats as a **sub-agent**, not a slash command. A sub-agent still works (OpenCode can dispatch to it by description-matching), but `/librarian` won't be typeable verbatim yet. See [Known Limitations](#-known-limitations).

### GitHub Copilot CLI

The standalone `copilot` terminal tool (`npm install -g @github/copilot`) — not the VS Code extension, not the older `gh copilot`.

**Skills need no conversion** — Copilot CLI reads the shared `.agents/skills/` convention directly, and `.claude/skills/` too. Publish with `--platform claude-code` as above, or drop skill folders straight into `.agents/skills/`.

**`/librarian` as a command:** Copilot CLI has no custom slash-command/prompt-file mechanism (open feature request, not built yet). The closest fit is a custom **sub-agent** (`.agent.md` files, project dir `.github/agents/`, global `~/.copilot/agents/`), invoked with `--agent librarian` or `/agent`:

```bash
mkdir -p .github/agents
cp librarian_skill/library/agents/librarian.md .github/agents/librarian.agent.md
```

`publish-to-project.py --platform github-copilot` does **not** write to this path today (see [Known Limitations](#-known-limitations)) — copy manually for now.

### VS Code (GitHub Copilot Chat)

The editor extension — different product from the CLI tools above, and it has no "Skills" concept at all. Use its own **prompt files** and **custom agents** instead:

```bash
# Slash-command-style: one prompt file per skill, invoked as /{id}
mkdir -p .github/prompts
cp librarian_skill/library/skills/brainstorming/SKILL.md .github/prompts/brainstorming.prompt.md

# Custom agent: the Librarian itself
mkdir -p .github/agents
cp librarian_skill/library/agents/librarian.md .github/agents/librarian.agent.md
```

`publish-to-project.py --platform github-copilot` currently writes to `.github/copilot/` and `.vscode/*.agent.md` — **neither path matches VS Code's real current convention** (`.github/prompts/`, `.github/agents/`), confirmed against current VS Code docs. Copy manually to the paths above until the script is updated. See [Known Limitations](#-known-limitations).

### Codex CLI

OpenAI's `codex` (`npm install -g @openai/codex`). Skills need no conversion — Codex reads the same `.agents/skills/` convention as OpenCode/Copilot CLI (project: `.agents/skills/`, global: `~/.agents/skills/`).

**`/librarian` as a command:** Codex deprecated custom slash-command prompts in favor of Skills, so the natural port is to ship the Librarian *as a skill*, not a command:

```bash
mkdir -p .agents/skills/librarian
cp librarian_skill/commands/librarian.md .agents/skills/librarian/SKILL.md
```

Codex auto-loads skills into context when relevant. Not yet wired into `publish-to-project.py`.

---

## ⚡ Quick Start

### 1. Use slash commands (recommended)

In your AI assistant:

```
/librarian                  → Show command menu (cheat sheet)
/librarian help             → Same as above
/librarian recommend        → Analyze project and recommend skills
/librarian stack <id>       → Show and install a stack (e.g. ros2-robotics)
/librarian create-stack     → Draft a new reusable stack from current project
/librarian publish <skills> → Install specific skills (space-separated IDs)
/librarian import <path>    → Bring new skills from an external repo into the library
/librarian browse           → List all entries in the library
/librarian search <query>   → Search catalog by keyword
/librarian update           → Check if installed skills have updates
```

### 2. Or use the CLI

```bash
# Preview a stack
python3 scripts/publish-to-project.py --project /path/to/project --stack ros2-robotics --dry-run

# Install a stack for a specific platform
python3 scripts/publish-to-project.py --project /path/to/project --stack ros2-robotics --platform opencode
python3 scripts/publish-to-project.py --project /path/to/project --stack ros2-robotics --platform github-copilot

# Install specific skills
python3 scripts/publish-to-project.py --project . --skills brainstorming systematic-debugging
```

---

## 📦 Available Stacks

Pre-configured skill bundles for common project types:

| Stack | Project Type |
|-------|-------------|
| 🤖 **ros2-robotics** | ROS2 / Robotics |
| 🌐 **web-fullstack-typescript** | React + TypeScript |
| 🔬 **ml-research-pytorch** | ML Research |
| ⚡ **api-service-go** | Go Backend |

A stack is scoped to a **project type**. `/librarian stack <id>` or `--stack <id>` installs all of its `core_skills` + `workflow_skills` in one shot.

---

## 📚 Available Collections

Pre-ordered skill **sequences** for a workflow, independent of project type — install with `--collection <id>`:

| Collection | Workflow |
|------------|----------|
| `tdd-first` | Requirements → TDD implementation → review |
| `debugging-deep-dive` | Root-cause analysis → fix → verify → review |
| `plan-driven-development` | Planning → architecture decisions → execution |
| `devops-ship-cycle` | Review → security scan → QA → deploy → monitor |

```bash
python3 scripts/publish-to-project.py --project . --collection tdd-first
```

---

## 🛠️ Usage

### Slash Commands (primary)

```
/librarian                  → Show command menu (cheat sheet)
/librarian help             → Same as above
/librarian recommend        → Analyze project and recommend skills
/librarian stack <id>       → Show and install a stack (e.g. ros2-robotics)
/librarian create-stack     → Draft a new reusable stack from current project
/librarian publish <skills> → Install specific skills (space-separated IDs)
/librarian import <path>    → Bring new skills from an external repo into the library
/librarian browse           → List all entries in the library
/librarian search <query>   → Search catalog by keyword
/librarian update           → Check if installed skills have updates
```

### CLI Scripts (secondary)

**Consumer side (install skills into a project):**

```bash
# Detect tech signals and suggest best-fit stack
python3 scripts/detect-project.py /path/to/project

# Publish skills/stacks/collections to a target project
python3 scripts/publish-to-project.py --project . --stack ros2-robotics --platform claude-code
python3 scripts/publish-to-project.py --project . --collection tdd-first
python3 scripts/publish-to-project.py --project . --skills brainstorming --dry-run

# Check for available updates
python3 scripts/check-updates.py /path/to/project

# Validate library integrity
python3 scripts/validate.py
python3 scripts/validate.py --strict --json
```

**Curator side (import from Skills_Pool sources):**

```bash
# Scan Skills_Pool/ and detect structure
python3 scripts/detect-skills-pool.py
python3 scripts/detect-skills-pool.py --dir ros2-engineering-skills --json

# Import specific skills from a source
python3 scripts/import-skill.py --source superpowers --skill brainstorming --dry-run
python3 scripts/import-skill.py --source superpowers --skill brainstorming systematic-debugging --force

# Auto-import: scan → detect → import → rebuild catalog
python3 scripts/auto-import.py --dry-run
python3 scripts/auto-import.py --force
python3 scripts/auto-import.py --dir new-repo

# Rebuild catalog index
python3 scripts/build-catalog.py
```

### Platform Output Paths

| Platform | Skills | Agents |
|----------|--------|--------|
| **Claude Code** | `.claude/skills/{id}/SKILL.md` | `.claude/commands/{id}.md` |
| **OpenCode** | `.opencode/skills/{id}/SKILL.md` | `.opencode/agents/{id}.md` |
| **GitHub Copilot** | `.github/copilot/{id}.prompt.md` | `.vscode/{id}.agent.md` |

---

## 🧩 Skills by Category

**Planning & Workflow** — `brainstorming` · `writing-plans` · `executing-plans` · `writing-skills`

**Testing & QA** — `test-driven-development` · `tdd-workflow` · `e2e-testing` · `qa`

**Debugging** — `systematic-debugging` · `investigate`

**Code Review** — `code-review` · `requesting-code-review` · `receiving-code-review`

**DevOps** — `ship` · `land-and-deploy` · `canary` · `guard` · `docker-patterns`

**Architecture** — `api-design` · `backend-patterns` · `frontend-patterns` · `mcp-server-patterns`

**Language-Specific** — `python-patterns` · `golang-patterns` · `postgres-patterns`

**Platform-Specific** — `ros2-engineering` · `pytorch-patterns` · `cad` · `gcode` · `yolo-object-detection`

**AI Agents** — `subagent-driven-development` · `dispatching-parallel-agents` · `agent-builder`

---

## 🤖 Agents

Curated agents live in `library/agents/` and publish as sub-agents (Claude Code) or converted `.agent.md` files (other platforms):

| Agent | Role |
|-------|------|
| 📚 **librarian** | Published copy of the `/librarian` command itself — see [Two Copies of `/librarian`](#two-copies-of-librarian) |
| 🔍 **code-reviewer** | Reviews a completed step/PR for correctness and quality |
| 📋 **gsd-planner** | Creates executable phase plans with task breakdown |
| ⚡ **gsd-executor** | Executes GSD plans with atomic commits and checkpoints |
| ✅ **gsd-verifier** | Verifies a phase actually delivered its goal |
| 🐛 **gsd-debugger** | Investigates bugs with a scientific-method debug loop |
| 🧭 **gsd-plan-checker** · **gsd-codebase-mapper** · **gsd-advisor-researcher** | Supporting GSD-pipeline roles — see `library/agents/` for details |

> On Claude Code, the primary `/librarian` experience still comes from the plugin's `commands/librarian.md`, not this entry — see [Two Copies of `/librarian`](#two-copies-of-librarian) in Key Concepts.

---

## 📁 Project Structure

```
agent-hub-index/
├── library/                    Curated skill collection
│   ├── skills/                 Skill definitions (SKILL.md per skill)
│   ├── agents/                 Agent definitions
│   ├── stacks/                 Pre-configured stack bundles (YAML)
│   ├── collections/            Workflow sequences (YAML)
│   ├── provenance/             Import provenance per entry
│   ├── enrichment/             Curator metadata overrides
│   ├── import-log.yaml         Import history audit trail
│   └── catalog.json            Auto-generated master index
├── scripts/                    CLI tools
│   ├── detect-project.py       Tech/domain signal detection
│   ├── publish-to-project.py   Multi-platform skill publishing
│   ├── check-updates.py        Update checking via sha256
│   ├── validate.py             Library integrity validation (10 checks)
│   ├── detect-skills-pool.py   Skills_Pool structure detection
│   ├── import-skill.py         Curated skill import from sources
│   ├── auto-import.py          Full pipeline orchestrator
│   └── build-catalog.py        Catalog index builder
├── commands/                   Slash command definitions
├── data/
│   └── skills-pool-registry.yaml   Source project registry
└── docs/                       Architecture docs
```

---

## 🔑 Key Concepts

### Stack vs Collection

**Stack** = bundle for a **project type** (e.g. `ros2-robotics`)
**Collection** = sequence for a **workflow** (e.g. `tdd-first`)

### Two Copies of `/librarian`

There are two `librarian.md` files in this repo, and both are load-bearing:

| File | Ships when... | How it finds `library/`/`scripts/` |
|------|----------------|-------------------------------------|
| `commands/librarian.md` | This repo is installed as a **Claude Code plugin** (see Installation) | Relative paths — the whole repo is copied into the plugin cache together, so `library/` and `scripts/` are always right next to it |
| `library/agents/librarian.md` | A skill/stack is **published** into *any* project via `publish-to-project.py` — lands as `.claude/commands/`, `.opencode/agents/`, or `.vscode/*.agent.md` | Reads `library_source` from that project's `library-manifest.yaml` (written on every publish) — it can't assume the warehouse is next door, because it usually isn't |

Same dispatch logic, same subcommands, two different install paths with two
different path-resolution needs. They're kept in sync **manually** — each
file has a comment pointing at the other, and `validate.py` warns
(`LIBRARIAN_COPIES_IN_SYNC`) if their subcommand lists drift apart.

### Curation Workflow

```
Skills_Project_Folder/ (raw sources)
    │
    ▼
detect-skills-pool.py  →  registry.yaml (scan results)
    │
    ▼
import-skill.py / auto-import.py  →  library/ (curated entries)
    │
    ▼
build-catalog.py  →  catalog.json (master index)
```

### Provenance & Enrichment

- **provenance.yaml** — tracks source, import time, hash for each entry
- **enrichment.yaml** — curator overrides for domains, technologies, use_with, conflicts_with, project_types

### Safety

- ✅ **Dry-run first** — Preview before installing or importing
- ✅ **Conflict detection** — Won't overwrite customized skills (use `--force` to override)
- ✅ **Hash verification** — sha256 checksums detect outdated or modified skills
- ✅ **File locking** — `publish-to-project.py` uses flock to prevent concurrent corruption
- ✅ **Validation** — `validate.py` runs 10 integrity checks (SKILL.md presence, provenance, agent frontmatter, [librarian.md copies in sync](#two-copies-of-librarian), catalog completeness, duplicate IDs, reference validity, collections, stacks)

---

## ⚠️ Known Limitations

Verified against the actual scripts, not just design docs:

- **Fixed:** `publish-to-project.py` auto-attaches the Librarian command whenever you publish skills/a stack (unless `--no-librarian`). This used to silently no-op — `library/agents/librarian.md` was missing, so it always printed `[SKIP]` and `catalog.json` had a dangling `librarian` entry. Both are fixed now: publishing to any platform also drops a file into that project (`.claude/commands/`, `.opencode/agents/`, or `.vscode/*.agent.md`), confirmed with real (non-dry-run) publishes to all three platforms. See [Two Copies of `/librarian`](#two-copies-of-librarian) for how the two files divide the work.
- **Confirmed (not just unverified) against each platform's real current docs:** `--platform opencode` publishes the Librarian to `.opencode/agents/librarian.md`, which OpenCode treats as a **sub-agent**, not a slash command — `/librarian` typed verbatim will not work there today; OpenCode's real command format lives at `.opencode/commands/*.md` with a `template` frontmatter field this repo doesn't produce yet.
- **Confirmed bug:** `--platform github-copilot` writes to `.github/copilot/{id}.prompt.md` and `.vscode/{id}.agent.md` — **neither path matches any real product.** VS Code's actual convention is `.github/prompts/*.prompt.md` + `.github/agents/*.agent.md`; the standalone GitHub Copilot CLI has no prompt-file system at all and uses `.github/agents/*.agent.md` for sub-agents instead. This platform target needs a rewrite — see the manual copy steps under Installation for VS Code / GitHub Copilot CLI in the meantime.
- **Good news, confirmed:** OpenCode, GitHub Copilot CLI, and Codex CLI all read the shared `.agents/skills/` directory convention directly (OpenCode and Copilot CLI also read `.claude/skills/` directly) — so for **skills** (not the `/librarian` command itself), publishing once with `--platform claude-code` is often enough; no per-platform conversion needed.

---

## 🙋 FAQ

**Q: Can I use this without Claude Code?**  
A: Yes. Skills are plain Markdown files, and `/librarian` itself now publishes to OpenCode and GitHub Copilot too (not just Claude Code) — see [Known Limitations](#-known-limitations) for what's verified vs. not on each platform.

**Q: What if I customize a published skill?**  
A: Librarian detects the change and won't overwrite it. Use `--force` to pull the latest.

**Q: How do I know when skills have updates?**  
A: Run `python3 scripts/check-updates.py /path/to/project`.

**Q: Can I create my own stacks?**  
A: Yes. Run `/librarian create-stack` in your project, or add a YAML file to `library/stacks/` and run `build-catalog.py`.

**Q: How do I import skills from a new source?**  
A: Clone the source into `~/Agent_Hub/Skills_Pool/`, then run `python3 scripts/auto-import.py --dry-run` to preview, followed by `python3 scripts/auto-import.py` to import.

---

## 📚 Documentation

Detailed docs in `docs/`:

- [`01-architecture.md`](docs/01-architecture.md) — System architecture
- [`02-data-models.md`](docs/02-data-models.md) — Schema definitions
- [`03-algorithms.md`](docs/03-algorithms.md) — Core algorithms
- [`04-data-flow.md`](docs/04-data-flow.md) — Data flow diagrams
- [`05-librarian-agent.md`](docs/05-librarian-agent.md) — Librarian spec


---

## 🧑‍💻 Author

**d.khai** — [hoangkhai6893](https://github.com/hoangkhai6893)

---

*Built for AI-assisted development. One library. Any project. Any assistant.*
