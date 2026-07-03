# 📚 Librarian

> Your curated skill & agent library for AI coding assistants. One library. Any project. Any assistant.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue)]()
[![Claude Code](https://img.shields.io/badge/Claude%20Code-supported-6f42c1)]()
[![OpenCode](https://img.shields.io/badge/OpenCode-supported-000000)]()
[![GitHub Copilot](https://img.shields.io/badge/GitHub%20Copilot-supported-000000)]()

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

Librarian is a **curated skill and agent library** for AI-assisted development.

It's a single source of truth for your best development workflows — skills and agents organized by use case, with automatic stack matching for your project type.

**How it works:**

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  Your AI Assistant  │     │    Librarian Lib.   │     │   Your Project      │
│                     │     │                     │     │                     │
│  /librarian recommend│────▶│  Skills             │────▶│  .claude/skills/    │
│  /librarian stack   │     │  Agents             │────▶│  .opencode/skills/  │
│  /librarian publish │     │  Stacks             │────▶│  .github/copilot/   │
│                     │     │  catalog.json       │     │  library-manifest   │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘

1. You open a project in Claude Code, OpenCode, or Copilot
2. You type: /librarian recommend
3. Librarian analyzes your project, matches skills, and recommends a toolkit
4. You say "yes" — skills are installed automatically
```

**In 30 seconds:** Open project → type `/librarian recommend` → get a complete, pre-matched skill set.

---

## 📥 Installation

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

# Publish skills/stacks to a target project
python3 scripts/publish-to-project.py --project . --stack ros2-robotics --platform claude-code
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

| Agent | Role |
|-------|------|
| 📚 **librarian** | Skill discovery & management |
| 🐛 **gsd-debugger** | Autonomous debugging |
| ⚡ **gsd-executor** | Task execution |
| 📋 **gsd-planner** | Project planning |
| ✅ **gsd-verifier** | Verification |

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
│   ├── validate.py             Library integrity validation (9 checks)
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

### Curation Workflow

```
Skills_Pool/ (raw sources)
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
- ✅ **Validation** — `validate.py` runs 9 integrity checks (SKILL.md presence, provenance, frontmatter, catalog completeness, duplicate IDs, reference validity, collections, stacks)

---

## 🙋 FAQ

**Q: Can I use this without Claude Code?**  
A: Yes. Skills are plain Markdown files. They work with OpenCode, GitHub Copilot, or any tool that reads `.md` files.

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
- [`06-implementation-phases.md`](docs/06-implementation-phases.md) — Roadmap

---

## 🧑‍💻 Author

**d.khai** — [hoangkhai6893](https://github.com/hoangkhai6893)

---

*Built for AI-assisted development. One library. Any project. Any assistant.*
