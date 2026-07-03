# Agent Hub - Tai lieu Kien truc He thong

> **Phien ban:** 1.0
> **Ngay:** 2026-03-30
> **Trang thai:** CONFIRMED - San sang de implement

## Muc luc

1. [Tong quan](#1-tong-quan)
2. [Nguyen tac Thiet ke](#2-nguyen-tac-thiet-ke)
3. [So do Thanh phan (Component Diagram)](#3-so-do-thanh-phan)
4. [Kien truc Hai tang (Two-Tier Architecture)](#4-kien-truc-hai-tang)
5. [Cau truc Thu muc](#5-cau-truc-thu-muc)
6. [Mo ta Chi tiet Thanh phan](#6-mo-ta-chi-tiet-thanh-phan)
7. [Luong Du lieu (Data Flow)](#7-luong-du-lieu)
8. [Thiet ke Ho tro Da nen tang](#8-thiet-ke-ho-tro-da-nen-tang)
9. [Schema va Dinh dang](#9-schema-va-dinh-dang)
10. [Session Hook va Proactive Mode](#10-session-hook-va-proactive-mode)
11. [Ke hoach Trien khai](#11-ke-hoach-trien-khai)

---

## 1. Tong quan

**Agent Hub** la thu vien ca nhan chua cac Skills va Agents cho cac nen tang AI Agent (Claude Code, OpenCode, Codex, GitHub Copilot). He thong duoc thiet ke theo mo hinh "Thu vien" (Library) — noi cac skill da duoc chon loc, chuan hoa va san sang de publish vao bat ky project nao.

### Van de can giai quyet

Hien tai co 6 source project nam tai `~/Agent_Hub/`:

| # | Project                 | Noi dung chinh                          | So luong skill/agent/command |
|---|-------------------------|-----------------------------------------|------------------------------|
| 1 | `superpowers`           | Skills, agents, session hooks           | ~14 skills, 1 agent          |
| 2 | `everything-claude-code`| Commands, skills, agents, rules         | ~57 commands, 28 agents      |
| 3 | `gstack`                | Agents, tools, workflows                | Agents + tools               |
| 4 | `get-shit-done`         | Commands, agents, hooks                 | 1 command, 18 agents         |
| 5 | `openspec`              | Change management specs                 | Specs + config               |
| 6 | `learn-claude-code`     | Tutorial agents, skills                 | ~12 agents, 4 skills         |

**Van de:** Cac skill nam rai rac o 6 project, khong co cach thong nhat de tim, chon va publish vao project moi. He thong cu (build-registry.py, search.py, registry.json) tao ra 407+ entries khong duoc chon loc — **se bi loai bo hoan toan**.

**Giai phap:** Xay dung mot **Central Warehouse** chua ~50 skills/agents da duoc curated, voi mot **Librarian agent** giup nguoi dung tim va publish skill phu hop vao project cua ho.

---

## 2. Nguyen tac Thiet ke

### 2.1. "Library not Search"

```
  CU (Loai bo)                        MOI (Agent Hub)
  ============                        ================

  User hoi "tim skill debug"          User noi "toi can debug"
       |                                    |
       v                                    v
  search.py query registry.json        Librarian doc catalog.json
       |                                    |
       v                                    v
  Tra ve 47 ket qua                    Goi y 2-3 skill phu hop
       |                                    |
       v                                    v
  User tu copy file                    Librarian publish vao .claude/
```

Skills nam **local** trong library/, khong phai la external references. Khi publish, skill duoc **copy** vao project — khong can mang, khong can registry server.

### 2.2. "Librarian not Catalog"

Thay vi nguoi dung tu search bang keyword, **Librarian agent** se:
- Hieu context cua project (ngon ngu, framework, giai doan)
- Goi y skills phu hop tu catalog
- Publish truc tiep vao project

### 2.3. "Curated not Dumped"

```
  6 source projects        import-skill.py         library/
  ==================  --->  (chon loc, chuan hoa)  --->  ~50 entries
  407+ raw entries          con nguoi review              chat luong cao
```

Moi skill trong library/ da duoc:
- Doc va hieu noi dung
- Chuan hoa format (SKILL.md frontmatter)
- Gan tags/categories chinh xac
- Test tren it nhat 1 platform

### 2.4. "Publish not Link"

```
  KHONG lam (symlink):          CO lam (publish/copy):
  ====================          ======================

  project/.claude/              project/.claude/
    skills/                       skills/
      tdd -> ~/Agent_Hub/...        tdd/
      debug -> ~/Agent_Hub/...        SKILL.md  (ban copy doc lap)
                                    debug/
  Van de: bi hu khi move,           SKILL.md  (ban copy doc lap)
  khong customize duoc
                                Uu diem: doc lap, co the
                                customize cho tung project
```

---

## 3. So do Thanh phan

### 3.1. Tong quan He thong

```
+===========================================================================+
|                           ~/Agent_Hub/                                     |
|                                                                           |
|  +---------------------------+     +----------------------------------+   |
|  |    6 SOURCE PROJECTS      |     |        library/ (WAREHOUSE)      |   |
|  |    (giu nguyen vi tri)    |     |   (Trung tam chua skill curated) |   |
|  |                           |     |                                  |   |
|  | superpowers/              |     |  skills/                         |   |
|  | everything-claude-code/   |     |    tdd/SKILL.md                  |   |
|  | gstack/                   | ==> |    systematic-debugging/SKILL.md |   |
|  | get-shit-done/            |     |    code-review/SKILL.md          |   |
|  | openspec/                 |     |    ...(~50 entries)              |   |
|  | learn-claude-code/        |     |                                  |   |
|  |                           |     |  agents/                         |   |
|  | (chi doc, khong sua)      |     |    librarian.md                  |   |
|  +---------------------------+     |    code-reviewer.md              |   |
|          |                         |    planner.md                    |   |
|          | import-skill.py         |    ...                           |   |
|          | (thu cong, co review)   |                                  |   |
|          +------------------------>|  catalog.json                    |   |
|                                    |    (metadata cua tat ca entries) |   |
|                                    |                                  |   |
|                                    |  collections/                    |   |
|                                    |    web-fullstack.json            |   |
|                                    |    python-data.json              |   |
|                                    |    ...                           |   |
|                                    |                                  |   |
|                                    |  stacks/                         |   |
|                                    |    starter.json                  |   |
|                                    |    pro-developer.json            |   |
|                                    |    ...                           |   |
|                                    +----------------------------------+   |
|                                         |                                 |
|  +---------------------------+          |                                 |
|  |      scripts/             |          | publish-to-project.py           |
|  |                           |          | (Librarian goi script nay)      |
|  | import-skill.py           |          |                                 |
|  | build-catalog.py          |          v                                 |
|  | publish-to-project.py     |   +-------------------------------+        |
|  | validate.py               |   | TARGET PROJECT (my-project/)  |        |
|  +---------------------------+   |                               |        |
|                                  |  .claude/                     |        |
|                                  |    skills/                    |        |
|                                  |      tdd/SKILL.md             |        |
|                                  |      debug/SKILL.md           |        |
|                                  |    commands/                  |        |
|                                  |      librarian.md             |        |
|                                  |    settings.json (hooks)      |        |
|                                  +-------------------------------+        |
+===========================================================================+
```

### 3.2. Luong Librarian Agent

```
+-------+     "toi can debug skill"     +------------------+
| User  | ----------------------------> | Librarian Agent  |
+-------+                               | (trong project)  |
                                         +--------+---------+
                                                  |
                                    1. Doc catalog.json
                                                  |
                                                  v
                                         +--------+---------+
                                         | catalog.json     |
                                         | (library/)       |
                                         +--------+---------+
                                                  |
                                    2. Tim skill phu hop
                                       (tags, categories,
                                        description match)
                                                  |
                                                  v
                                         +--------+---------+
                                         | Goi y cho User:  |
                                         | - systematic-    |
                                         |   debugging      |
                                         | - tdd            |
                                         +--------+---------+
                                                  |
                               User chon:    "lay debugging"
                                                  |
                                                  v
                                         +--------+---------+
                                         | publish-to-      |
                                         | project.py       |
                                         +--------+---------+
                                                  |
                                    3. Copy SKILL.md tu
                                       library/skills/
                                       systematic-debugging/
                                                  |
                                                  v
                                         +--------+---------+
                                         | project/.claude/ |
                                         | skills/          |
                                         |   systematic-    |
                                         |   debugging/     |
                                         |     SKILL.md     |
                                         +------------------+
                                                  |
                                    4. Skill san sang su dung
                                       trong project
```

---

## 4. Kien truc Hai tang

### 4.1. Mo hinh Tong the

```
+==============================================+
|          TIER 1: CENTRAL WAREHOUSE           |
|          ~/Agent_Hub/library/                |
|                                              |
|  +--------+  +--------+  +-------------+    |
|  | skills/|  | agents/|  | catalog.json|    |
|  | (~40)  |  | (~10)  |  | (metadata)  |    |
|  +--------+  +--------+  +-------------+    |
|                                              |
|  +-------------+  +--------+                 |
|  | collections/|  | stacks/|                 |
|  | (nhom theo  |  | (nhom  |                 |
|  |  domain)    |  |  theo  |                 |
|  +-------------+  |  level)|                 |
|                    +--------+                |
+==============================================+
          |                          |
          | publish-to-project.py    | publish-to-project.py
          | (Librarian trigger)      | (Librarian trigger)
          v                          v
+==================+      +==================+
| TIER 2: PROJECT A|      | TIER 2: PROJECT B|
| my-web-app/      |      | my-api/          |
|   .claude/       |      |   .claude/       |
|     skills/      |      |     skills/      |
|       tdd/       |      |       tdd/       |
|       code-      |      |       systematic-|
|       review/    |      |       debugging/ |
|     commands/    |      |     commands/    |
|       librarian  |      |       librarian  |
+==================+      +==================+
```

### 4.2. Tier 1: Central Warehouse — `~/Agent_Hub/library/`

**Muc dich:** Kho trung tam chua TAT CA skills/agents da duoc curated. Day la "nguon su that duy nhat" (single source of truth) cho toan bo he thong.

**Dac diem:**
- Chua ~50 entries (skills + agents) da chon loc tu 6 source projects
- Moi entry co format chuan hoa
- catalog.json chua metadata de Librarian tra cuu
- Collections nhom skill theo domain (web, data, devops...)
- Stacks nhom skill theo level (starter, intermediate, pro)

**Ai truy cap:**
- `import-skill.py` — ghi vao khi import skill moi
- `build-catalog.py` — doc toan bo de tao catalog.json
- `publish-to-project.py` — doc skill de copy vao project
- Librarian agent — doc catalog.json de goi y

### 4.3. Tier 2: Project Library — `my-project/.claude/`

**Muc dich:** Chua CHI NHUNG skills/agents can thiet cho MOT project cu the. Day la ban sao doc lap, co the customize.

**Dac diem:**
- Chi chua skills duoc Librarian publish
- Moi project co tap skills khac nhau
- Skill da publish co the duoc sua de phu hop project
- Khong phu thuoc vao Agent_Hub/ de chay (doc lap hoan toan)
- Librarian command nam o day de user co the goi bat ky luc nao

**Luong Publish:**

```
  Tier 1 (Warehouse)                   Tier 2 (Project)
  ====================                 =================

  library/skills/tdd/                  project/.claude/skills/tdd/
    SKILL.md            -- copy -->      SKILL.md
                                         (ban doc lap, co the sua)

  library/agents/                      project/.claude/commands/
    librarian.md        -- copy -->      librarian.md
                                         (de user co the /librarian)
```

**Quan trong:** Publish la mot **phep copy** (khong phai symlink). Sau khi publish:
- Sua skill o Tier 1 **KHONG** anh huong Tier 2
- Project co the customize skill cho rieng minh
- Xoa Agent_Hub/ **KHONG** lam hu project

---

## 5. Cau truc Thu muc

### 5.1. Agent_Hub/ — Toan bo he thong

```
~/Agent_Hub/
|
|-- library/                          # TIER 1: Central Warehouse
|   |-- skills/                       # ~40 skills curated
|   |   |-- tdd/
|   |   |   +-- SKILL.md             # Noi dung skill (co frontmatter)
|   |   |-- systematic-debugging/
|   |   |   +-- SKILL.md
|   |   |-- code-review/
|   |   |   +-- SKILL.md
|   |   |-- writing-plans/
|   |   |   +-- SKILL.md
|   |   |-- brainstorming/
|   |   |   +-- SKILL.md
|   |   |-- executing-plans/
|   |   |   +-- SKILL.md
|   |   |-- verification-before-completion/
|   |   |   +-- SKILL.md
|   |   |-- git-worktrees/
|   |   |   +-- SKILL.md
|   |   |-- subagent-driven-development/
|   |   |   +-- SKILL.md
|   |   |-- dispatching-parallel-agents/
|   |   |   +-- SKILL.md
|   |   |-- finishing-dev-branch/
|   |   |   +-- SKILL.md
|   |   |-- requesting-code-review/
|   |   |   +-- SKILL.md
|   |   |-- receiving-code-review/
|   |   |   +-- SKILL.md
|   |   |-- writing-skills/
|   |   |   +-- SKILL.md
|   |   |-- build-fix/
|   |   |   +-- SKILL.md
|   |   |-- checkpoint/
|   |   |   +-- SKILL.md
|   |   |-- orchestrate/
|   |   |   +-- SKILL.md
|   |   |-- eval/
|   |   |   +-- SKILL.md
|   |   |-- refactor-clean/
|   |   |   +-- SKILL.md
|   |   |-- prompt-optimize/
|   |   |   +-- SKILL.md
|   |   |-- quality-gate/
|   |   |   +-- SKILL.md
|   |   |-- test-coverage/
|   |   |   +-- SKILL.md
|   |   |-- update-docs/
|   |   |   +-- SKILL.md
|   |   |-- save-session/
|   |   |   +-- SKILL.md
|   |   |-- resume-session/
|   |   |   +-- SKILL.md
|   |   |-- e2e/
|   |   |   +-- SKILL.md
|   |   |-- learn/
|   |   |   +-- SKILL.md
|   |   |-- context-budget/
|   |   |   +-- SKILL.md
|   |   +-- ... (them skill khac, tong ~40)
|   |
|   |-- agents/                       # ~10 agents curated
|   |   |-- librarian.md             # THE Librarian - agent chinh
|   |   |-- code-reviewer.md         # Code review agent
|   |   |-- planner.md               # Planning agent
|   |   |-- architect.md             # Architecture agent
|   |   |-- tdd-guide.md             # TDD guide agent
|   |   |-- debugger.md              # Debugging agent
|   |   |-- security-reviewer.md     # Security review agent
|   |   |-- doc-updater.md           # Documentation agent
|   |   |-- build-error-resolver.md  # Build fix agent
|   |   +-- e2e-runner.md            # E2E testing agent
|   |
|   |-- catalog.json                  # Metadata cua TAT CA entries
|   |
|   |-- collections/                  # Nhom theo domain/use-case
|   |   |-- web-fullstack.json       # Skills cho web dev
|   |   |-- python-data.json         # Skills cho Python/data
|   |   |-- devops-infra.json        # Skills cho DevOps
|   |   |-- code-quality.json        # Skills cho code quality
|   |   +-- session-management.json  # Skills cho session mgmt
|   |
|   +-- stacks/                       # Nhom theo level/preset
|       |-- starter.json             # Bo skill co ban cho moi project
|       |-- pro-developer.json       # Bo skill nang cao
|       +-- team-lead.json           # Bo skill cho team lead/reviewer
|
|-- scripts/                          # Cong cu automation
|   |-- import-skill.py              # Import skill tu source vao library/
|   |-- build-catalog.py             # Tao/cap nhat catalog.json
|   |-- publish-to-project.py        # Publish skill(s) vao project
|   +-- validate.py                  # Validate library/ integrity
|
|-- superpowers/                      # SOURCE 1 (giu nguyen, chi doc)
|-- everything-claude-code/           # SOURCE 2 (giu nguyen, chi doc)
|-- gstack/                           # SOURCE 3 (giu nguyen, chi doc)
|-- get-shit-done/                    # SOURCE 4 (giu nguyen, chi doc)
|-- openspec/                         # SOURCE 5 (giu nguyen, chi doc)
|-- learn-claude-code/                # SOURCE 6 (giu nguyen, chi doc)
|
+-- agent-hub-index/                  # Project nay (docs, old code)
    |-- docs/
    |   +-- 01-architecture.md       # TAI LIEU NAY
    +-- (old code - se bi xoa)
```

### 5.2. Target Project — Sau khi Publish

```
my-project/                           # Bat ky project nao cua user
|
|-- .claude/                          # TIER 2: Project Library
|   |-- skills/                       # Skills da publish cho project nay
|   |   |-- tdd/
|   |   |   +-- SKILL.md
|   |   |-- systematic-debugging/
|   |   |   +-- SKILL.md
|   |   +-- code-review/
|   |       +-- SKILL.md
|   |
|   |-- commands/                     # Slash commands
|   |   +-- librarian.md             # /librarian — goi Librarian agent
|   |
|   +-- settings.json                # Hook config (neu can)
|       (co the chua session hook
|        de proactive suggest skills)
|
|-- .codex/                           # Codex CLI support (neu can)
|   +-- AGENTS.md                    # Huong dan cho Codex
|
|-- .github/
|   +-- copilot-instructions.md      # GitHub Copilot instructions
|
|-- src/                              # Code cua project
|-- ...
+-- CLAUDE.md                         # Project instructions (co san)
```

---

## 6. Mo ta Chi tiet Thanh phan

### 6.1. library/skills/ — Kho Skill

| Thuoc tinh     | Gia tri                                            |
|----------------|----------------------------------------------------|
| **Muc dich**   | Chua toan bo skills da curated, moi skill 1 folder |
| **Input**      | SKILL.md files tu import-skill.py                  |
| **Output**     | SKILL.md files cho publish-to-project.py           |
| **Phu thuoc**  | Khong (doc lap)                                    |
| **Dinh dang**  | Markdown voi YAML frontmatter                      |

**Format cua moi SKILL.md:**

```markdown
---
name: systematic-debugging
description: Quy trinh debug co he thong, tu reproduce den verify fix
source: superpowers
version: "1.0"
tags: [debugging, testing, workflow]
categories: [development, debugging]
platforms: [claude-code, opencode, codex]
cost: medium
stability: stable
---

# Systematic Debugging

(Noi dung huong dan chi tiet cho AI agent...)
```

### 6.2. library/agents/ — Kho Agent

| Thuoc tinh     | Gia tri                                          |
|----------------|--------------------------------------------------|
| **Muc dich**   | Chua cac agent definitions (system prompts)      |
| **Input**      | Agent .md files tu import-skill.py               |
| **Output**     | Agent .md files cho publish-to-project.py        |
| **Phu thuoc**  | Khong (doc lap)                                  |
| **Dinh dang**  | Markdown (system prompt cho agent)               |

**Phan biet Skill va Agent:**

```
  SKILL                                 AGENT
  =====                                 =====

  Tap huong dan (instructions)          System prompt cho sub-agent
  Duoc load khi user/hook trigger       Duoc dispatch boi Skill tool
  Chay trong context hien tai           Chay trong context rieng
  Vi du: tdd, debugging steps           Vi du: code-reviewer (review code
                                        trong sandbox rieng)
```

### 6.3. library/catalog.json — Metadata Index

| Thuoc tinh     | Gia tri                                                   |
|----------------|-----------------------------------------------------------|
| **Muc dich**   | Index metadata cua tat ca entries de Librarian tra cuu    |
| **Input**      | Duoc tao boi build-catalog.py tu skills/ va agents/       |
| **Output**     | Duoc doc boi Librarian agent va publish-to-project.py     |
| **Phu thuoc**  | library/skills/*, library/agents/*                        |
| **Dinh dang**  | JSON                                                      |

**Schema catalog.json:**

```json
{
  "version": "1.0",
  "generated_at": "2026-03-30T00:00:00Z",
  "entries": [
    {
      "id": "skill:systematic-debugging",
      "type": "skill",
      "name": "systematic-debugging",
      "description": "Quy trinh debug co he thong...",
      "source": "superpowers",
      "tags": ["debugging", "testing", "workflow"],
      "categories": ["development", "debugging"],
      "platforms": ["claude-code", "opencode", "codex"],
      "cost": "medium",
      "stability": "stable",
      "path": "skills/systematic-debugging/SKILL.md"
    },
    {
      "id": "agent:code-reviewer",
      "type": "agent",
      "name": "code-reviewer",
      "description": "Agent review code tu dong...",
      "source": "everything-claude-code",
      "tags": ["review", "quality"],
      "categories": ["review"],
      "platforms": ["claude-code"],
      "cost": "heavy",
      "stability": "stable",
      "path": "agents/code-reviewer.md"
    }
  ],
  "collections": {
    "web-fullstack": "collections/web-fullstack.json",
    "python-data": "collections/python-data.json",
    "devops-infra": "collections/devops-infra.json"
  },
  "stacks": {
    "starter": "stacks/starter.json",
    "pro-developer": "stacks/pro-developer.json",
    "team-lead": "stacks/team-lead.json"
  }
}
```

### 6.4. library/collections/ — Nhom theo Domain

| Thuoc tinh     | Gia tri                                                 |
|----------------|---------------------------------------------------------|
| **Muc dich**   | Nhom skills theo domain/use-case de publish ca nhom     |
| **Input**      | Duoc tao thu cong hoac boi build-catalog.py             |
| **Output**     | Duoc doc boi Librarian khi user noi "toi lam web app"   |
| **Phu thuoc**  | catalog.json (tham chieu id)                            |
| **Dinh dang**  | JSON                                                    |

**Vi du `collections/web-fullstack.json`:**

```json
{
  "name": "Web Fullstack",
  "description": "Bo skill cho du an web fullstack (React/Vue + Node/Python)",
  "skills": [
    "skill:tdd",
    "skill:code-review",
    "skill:e2e",
    "skill:build-fix",
    "skill:quality-gate"
  ],
  "agents": [
    "agent:code-reviewer",
    "agent:build-error-resolver"
  ]
}
```

### 6.5. library/stacks/ — Nhom theo Level

| Thuoc tinh     | Gia tri                                                 |
|----------------|---------------------------------------------------------|
| **Muc dich**   | Preset nhom skills theo trinh do/role                   |
| **Input**      | Duoc tao thu cong                                       |
| **Output**     | Duoc doc boi Librarian de publish ca bo cung luc        |
| **Phu thuoc**  | catalog.json (tham chieu id)                            |
| **Dinh dang**  | JSON                                                    |

**Vi du `stacks/starter.json`:**

```json
{
  "name": "Starter",
  "description": "Bo skill co ban cho moi project moi",
  "skills": [
    "skill:tdd",
    "skill:systematic-debugging",
    "skill:writing-plans",
    "skill:verification-before-completion",
    "skill:code-review"
  ],
  "agents": [
    "agent:librarian"
  ]
}
```

### 6.6. scripts/import-skill.py

| Thuoc tinh       | Gia tri                                                  |
|------------------|----------------------------------------------------------|
| **Muc dich**     | Import 1 skill tu source project vao library/            |
| **Input**        | Source path, skill name, metadata (tags, categories)     |
| **Output**       | SKILL.md trong library/skills/{name}/ (da chuan hoa)     |
| **Phu thuoc**    | Source projects (doc), library/ (ghi)                    |
| **Ngon ngu**     | Python 3.10+                                             |

**Chuc nang chi tiet:**

```
import-skill.py
  --source superpowers
  --skill systematic-debugging
  --tags debugging,testing
  --categories development,debugging
  --platforms claude-code,opencode,codex
  --cost medium
  --stability stable

Luong xu ly:
  1. Doc SKILL.md tu source project
  2. Parse frontmatter hien co (neu co)
  3. Them/ghi de frontmatter theo args
  4. Chuan hoa format (remove platform-specific sections neu can)
  5. Ghi vao library/skills/{name}/SKILL.md
  6. In summary de con nguoi review
```

**Quan trong:** Script nay KHONG tu dong chay. Con nguoi chon skill, chay script, roi REVIEW ket qua. Day la quy trinh thu cong co y thuc ("curated not dumped").

### 6.7. scripts/build-catalog.py

| Thuoc tinh       | Gia tri                                                  |
|------------------|----------------------------------------------------------|
| **Muc dich**     | Scan library/ va tao/cap nhat catalog.json               |
| **Input**        | library/skills/*/SKILL.md, library/agents/*.md           |
| **Output**       | library/catalog.json                                     |
| **Phu thuoc**    | library/skills/*, library/agents/*                       |
| **Ngon ngu**     | Python 3.10+                                             |

**Luong xu ly:**

```
build-catalog.py

  1. Scan library/skills/*/SKILL.md
     - Parse YAML frontmatter
     - Extract: name, description, tags, categories, platforms, cost, stability
     - Tao entry voi id = "skill:{name}"

  2. Scan library/agents/*.md
     - Parse YAML frontmatter (neu co) hoac dong dau tien lam description
     - Tao entry voi id = "agent:{name}"

  3. Scan library/collections/*.json
     - Doc ten va path moi collection

  4. Scan library/stacks/*.json
     - Doc ten va path moi stack

  5. Ghi catalog.json voi:
     - version
     - generated_at (ISO timestamp)
     - entries[] (tat ca skills + agents)
     - collections{} (map name -> path)
     - stacks{} (map name -> path)

  6. Validate:
     - Khong co id trung
     - Tat ca collection/stack references ton tai trong entries
     - In summary: X skills, Y agents, Z collections, W stacks
```

### 6.8. scripts/publish-to-project.py

| Thuoc tinh       | Gia tri                                                  |
|------------------|----------------------------------------------------------|
| **Muc dich**     | Copy skills/agents tu library/ vao project .claude/      |
| **Input**        | Project path, danh sach skill/agent IDs (hoac stack/collection name) |
| **Output**       | Files trong project/.claude/skills/ va .claude/commands/  |
| **Phu thuoc**    | library/ (doc), target project (ghi)                     |
| **Ngon ngu**     | Python 3.10+                                             |

**Luong xu ly:**

```
publish-to-project.py
  --project /path/to/my-project
  --skills tdd,systematic-debugging
  --agents code-reviewer
  --stack starter              # HOAC publish ca stack
  --collection web-fullstack   # HOAC publish ca collection
  --platform claude-code       # Target platform (default: claude-code)
  --force                      # Ghi de neu da ton tai
  --include-librarian          # Luon publish librarian command

Luong xu ly:
  1. Doc catalog.json de resolve IDs
  2. Neu --stack hoac --collection: expand thanh danh sach skills/agents
  3. Voi moi skill:
     a. Doc library/skills/{name}/SKILL.md
     b. (Optional) Transform cho target platform
     c. Copy vao project/.claude/skills/{name}/SKILL.md
  4. Voi moi agent:
     a. Doc library/agents/{name}.md
     b. Copy vao project/.claude/commands/{name}.md
        (de thanh slash command /name)
  5. Neu --include-librarian:
     a. Copy librarian.md vao project/.claude/commands/
  6. In summary:
     - Da publish X skills, Y agents
     - Vao project: /path/to/my-project/.claude/
```

**Platform Transform (buoc 3b):**

```
Platform         Output location              Transform
===========      =========================    ===========================
claude-code      .claude/skills/{name}/       Giu nguyen SKILL.md
                 SKILL.md

opencode         .opencode/plugins/skills/    Convert frontmatter thanh
                 {name}/SKILL.md              opencode format

codex            .codex/skills/{name}/        Them AGENTS.md wrapper,
                 SKILL.md                     them agents/openai.yaml

copilot          .github/copilot-             Merge noi dung vao 1 file
                 instructions.md              instructions chung
```

### 6.9. scripts/validate.py

| Thuoc tinh       | Gia tri                                                  |
|------------------|----------------------------------------------------------|
| **Muc dich**     | Kiem tra tinh toan ven cua library/                      |
| **Input**        | library/ directory                                       |
| **Output**       | Report (stdout): loi, canh bao, ok                       |
| **Phu thuoc**    | library/*                                                |
| **Ngon ngu**     | Python 3.10+                                             |

**Kiem tra:**

```
validate.py

  1. Moi skills/*/SKILL.md co frontmatter hop le
     - Required fields: name, description, tags, categories, platforms
     - name khop voi ten folder

  2. Moi agents/*.md co noi dung (khong rong)

  3. catalog.json:
     - Moi entry co file tuong ung ton tai
     - Moi file trong skills/ va agents/ co entry tuong ung
     - Khong co id trung

  4. collections/*.json:
     - Moi ID tham chieu ton tai trong catalog

  5. stacks/*.json:
     - Moi ID tham chieu ton tai trong catalog

  6. Report:
     [OK]   42 skills valid
     [OK]   8 agents valid
     [OK]   catalog.json consistent
     [WARN] collection web-fullstack references "skill:flutter" - not found
     [ERR]  skills/foo/ missing SKILL.md
```

### 6.10. Librarian Agent — `library/agents/librarian.md`

| Thuoc tinh       | Gia tri                                                  |
|------------------|----------------------------------------------------------|
| **Muc dich**     | Agent giup user tim va publish skills phu hop vao project |
| **Input**        | User request (tu nhien), catalog.json                    |
| **Output**       | Goi y skills, goi publish-to-project.py                  |
| **Phu thuoc**    | catalog.json, publish-to-project.py                      |
| **Dinh dang**    | Markdown (system prompt)                                 |

**Noi dung librarian.md (system prompt):**

```markdown
# Librarian Agent

Ban la Librarian cua Agent Hub — giup nguoi dung tim va
cai dat skills/agents phu hop cho project cua ho.

## Cach lam viec

1. Doc catalog.json tai ~/Agent_Hub/library/catalog.json
2. Hieu context cua project hien tai:
   - Ngon ngu lap trinh (doc package.json, requirements.txt, go.mod...)
   - Framework (React, Django, FastAPI...)
   - Giai doan (planning, development, testing, review...)
3. Khi user hoi ve skill:
   - Tim trong catalog.json theo tags, categories, description
   - Goi y 2-3 skill phu hop nhat
   - Giai thich ngan gon tai sao moi skill phu hop
4. Khi user chon skill:
   - Chay: python3 ~/Agent_Hub/scripts/publish-to-project.py
     --project {project_path} --skills {skill_name}
   - Xac nhan da publish thanh cong
5. Cung ho tro:
   - "publish stack starter" — publish ca bo starter
   - "publish collection web-fullstack" — publish nhom web
   - "list skills" — liet ke tat ca skills co san
   - "what skills do I have?" — liet ke skills da publish trong project

## Luu y
- LUON doc catalog.json truoc khi goi y (khong tu bias)
- Goi y IT nhung CHINH XAC (2-3 skill, khong phai 10)
- Giai thich tai sao skill phu hop voi context cua user
```

---

## 7. Luong Du lieu

### 7.1. Import Flow (Mot lan, thu cong)

```
                     Con nguoi chon skill
                            |
                            v
  Source Project        import-skill.py          library/skills/
  ==============        ===============          ===============

  superpowers/          1. Doc SKILL.md
  skills/               2. Parse frontmatter
  systematic-           3. Chuan hoa format
  debugging/            4. Them metadata          systematic-debugging/
  SKILL.md         ---> 5. Ghi vao library/  ---> SKILL.md (curated)
                        6. In summary
                            |
                            v
                     Con nguoi REVIEW
                     ket qua truoc khi
                     commit
```

### 7.2. Build Catalog Flow (Sau moi import)

```
  library/skills/*/SKILL.md
  library/agents/*.md          build-catalog.py        library/catalog.json
  library/collections/*.json   ================        ==================
  library/stacks/*.json
                          ---> 1. Scan tat ca files
                               2. Parse frontmatter
                               3. Validate
                               4. Ghi catalog.json ---> catalog.json (moi)
```

### 7.3. Publish Flow (User-triggered qua Librarian)

```
  User: "toi can skill debug"
          |
          v
  +------------------+
  | Librarian Agent  |
  +--------+---------+
           |
     1. Doc catalog.json
           |
           v
  +------------------+
  | "Toi goi y:      |
  |  - systematic-   |
  |    debugging     |
  |  - tdd"          |
  +--------+---------+
           |
     User: "lay debugging"
           |
           v
  +------------------+       +---------------------+
  | Librarian goi:   | ----> | publish-to-         |
  | publish-to-      |       | project.py          |
  | project.py       |       +----------+----------+
  +------------------+                  |
                                  2. Doc library/skills/
                                     systematic-debugging/
                                     SKILL.md
                                        |
                                  3. Copy vao project
                                        |
                                        v
                              +---------------------+
                              | project/.claude/    |
                              |   skills/           |
                              |     systematic-     |
                              |     debugging/      |
                              |       SKILL.md      |
                              +---------------------+
                                        |
                              4. Skill san sang!
                                 User co the dung
                                 ngay trong session
```

### 7.4. Full Lifecycle

```
  PHASE 1: Curate (mot lan)
  =========================

  6 sources --[import-skill.py]--> library/skills/ (~40)
  6 sources --[import-skill.py]--> library/agents/ (~10)
  library/  --[build-catalog.py]-> library/catalog.json
  library/  --[validate.py]------> Report OK/WARN/ERR


  PHASE 2: Publish (moi project)
  ==============================

  User bat dau project moi
       |
       v
  User: /librarian "setup project"
       |
       v
  Librarian doc catalog.json
  Librarian hoi: "project gi? ngon ngu gi?"
  User: "web app React + FastAPI"
       |
       v
  Librarian: "goi y collection web-fullstack hoac stack starter"
  User: "lay starter"
       |
       v
  publish-to-project.py --project . --stack starter
       |
       v
  Project co 5 skills + librarian command


  PHASE 3: Su dung (hang ngay)
  ============================

  User lam viec binh thuong
       |
       v
  Session hook (optional) nhan ra user dang debug
       |
       v
  Goi y: "ban co muon dung skill systematic-debugging?"
       |
       v
  Skill da co san trong .claude/skills/ -> load ngay
```

---

## 8. Thiet ke Ho tro Da nen tang

### 8.1. Tong quan Platform Support

```
+===============+====================+==================+=================+
| Thanh phan    | Claude Code        | OpenCode         | Codex           |
+===============+====================+==================+=================+
| Skills        | .claude/skills/    | .opencode/       | .codex/skills/  |
|               | {name}/SKILL.md    | plugins/skills/  | {name}/SKILL.md |
|               |                    | {name}/SKILL.md  |                 |
+---------------+--------------------+------------------+-----------------+
| Agents        | .claude/commands/  | .opencode/       | .codex/agents/  |
|               | {name}.md          | plugins/agents/  | {name}.md +     |
|               | (slash command)    | {name}.md        | openai.yaml     |
+---------------+--------------------+------------------+-----------------+
| Session Hook  | settings.json      | config hooks     | Khong ho tro    |
|               | hooks.SessionStart |                  |                 |
+---------------+--------------------+------------------+-----------------+
| Proactive     | Co (session hook)  | Co (config hook) | Khong           |
| Mode          |                    |                  |                 |
+---------------+--------------------+------------------+-----------------+
| Librarian     | /librarian         | /librarian       | /librarian      |
| Command       | (slash command)    | (command)        | (command)       |
+===============+====================+==================+=================+

+===============+=================+
| Thanh phan    | GitHub Copilot  |
+===============+=================+
| Skills        | .github/        |
|               | copilot-        |
|               | instructions.md |
|               | (merged)        |
+---------------+-----------------+
| Agents        | Khong ho tro    |
|               | truc tiep       |
+---------------+-----------------+
| Session Hook  | Khong ho tro    |
+---------------+-----------------+
| Proactive     | Khong           |
| Mode          |                 |
+---------------+-----------------+
| Librarian     | Khong (dung     |
| Command       | thu cong)       |
+===============+=================+
```

### 8.2. Claude Code (Primary Platform)

Claude Code la nen tang chinh, duoc ho tro day du nhat.

**Skills:**
```
project/.claude/skills/{skill-name}/SKILL.md

- Duoc load tu dong khi skill name match user request
- Frontmatter co name va description de Claude biet khi nao trigger
- Dung Skill tool de invoke
```

**Agents (Slash Commands):**
```
project/.claude/commands/{agent-name}.md

- Tro thanh slash command: /{agent-name}
- User goi: /librarian "tim skill debug"
- Noi dung file la system prompt cho command
```

**Session Hook (Proactive Mode):**
```json
// project/.claude/settings.json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cat ~/Agent_Hub/library/agents/session-context.md",
            "async": false
          }
        ]
      }
    ]
  }
}
```

Hook nay inject context vao dau moi session, giup Claude biet:
- Co nhung skills nao san trong project
- Goi y proactive khi nhan ra user can skill cu the

### 8.3. OpenCode

**Skills:**
```
project/.opencode/plugins/skills/{skill-name}/SKILL.md

- OpenCode doc skills tu .opencode/plugins/
- Format SKILL.md tuong tu Claude Code
- Config hooks trong .opencode/config
```

**Transform khi publish:**

```python
# publish-to-project.py --platform opencode

def publish_for_opencode(skill_path, project_path):
    # 1. Doc SKILL.md
    # 2. Copy vao .opencode/plugins/skills/{name}/SKILL.md
    # 3. (Optional) Tao .opencode/config entry
```

### 8.4. Codex CLI

**Skills:**
```
project/.codex/skills/{skill-name}/SKILL.md
project/.codex/skills/{skill-name}/agents/openai.yaml

- Codex doc skills tu .codex/
- Can them openai.yaml de Codex hieu metadata
- AGENTS.md o root .codex/ liet ke tat ca skills
```

**Transform khi publish:**

```python
# publish-to-project.py --platform codex

def publish_for_codex(skill_path, project_path):
    # 1. Doc SKILL.md
    # 2. Copy vao .codex/skills/{name}/SKILL.md
    # 3. Tao agents/openai.yaml tu frontmatter
    # 4. Update .codex/AGENTS.md voi entry moi
```

**Vi du `agents/openai.yaml` duoc generate:**

```yaml
name: systematic-debugging
description: Quy trinh debug co he thong
type: skill
triggers:
  - debug
  - fix
  - error
```

### 8.5. GitHub Copilot

**Instructions Fragment:**
```
project/.github/copilot-instructions.md

- Copilot chi doc 1 file instructions duy nhat
- Tat ca skills duoc merge thanh 1 file
- Khong ho tro agents hay session hooks
```

**Transform khi publish:**

```python
# publish-to-project.py --platform copilot

def publish_for_copilot(skill_path, project_path):
    # 1. Doc SKILL.md
    # 2. Extract noi dung (bo frontmatter)
    # 3. Append vao .github/copilot-instructions.md
    #    voi header "## {skill-name}"
    # 4. Khong ghi de — chi append
```

**Vi du output `.github/copilot-instructions.md`:**

```markdown
# Project Skills (Published by Agent Hub)

## systematic-debugging
(Noi dung skill...)

## tdd
(Noi dung skill...)
```

---

## 9. Schema va Dinh dang

### 9.1. SKILL.md Frontmatter Schema

```yaml
---
# === REQUIRED ===
name: string              # ID duy nhat, khop ten folder (vd: "tdd")
description: string       # Mo ta ngan 1-2 cau

# === METADATA ===
source: string            # Source project goc
                          # enum: superpowers | everything-claude-code |
                          #        gstack | get-shit-done | openspec |
                          #        learn-claude-code
version: string           # Phien ban (vd: "1.0")

# === CLASSIFICATION ===
tags: [string]            # Tags tu do (vd: [debugging, testing])
categories: [string]      # Categories chuan
                          # enum: planning | architecture | development |
                          #        testing | debugging | review |
                          #        deployment | documentation |
                          #        workflow | session-management |
                          #        code-quality | learning

# === PLATFORM ===
platforms: [string]       # Nen tang ho tro
                          # enum: claude-code | opencode | codex | copilot

# === ASSESSMENT ===
cost: string              # Token cost khi su dung
                          # enum: light | medium | heavy
stability: string         # Muc do on dinh
                          # enum: experimental | beta | stable
---
```

### 9.2. catalog.json Full Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "generated_at", "entries"],
  "properties": {
    "version": {
      "type": "string",
      "description": "Schema version"
    },
    "generated_at": {
      "type": "string",
      "format": "date-time",
      "description": "Thoi diem tao catalog"
    },
    "entries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type", "name", "description", "source",
                     "tags", "categories", "platforms", "cost",
                     "stability", "path"],
        "properties": {
          "id": {
            "type": "string",
            "pattern": "^(skill|agent):.+$",
            "description": "ID duy nhat: {type}:{name}"
          },
          "type": {
            "type": "string",
            "enum": ["skill", "agent"]
          },
          "name": {
            "type": "string",
            "description": "Ten skill/agent (khop ten folder/file)"
          },
          "description": {
            "type": "string",
            "description": "Mo ta ngan"
          },
          "source": {
            "type": "string",
            "enum": ["superpowers", "everything-claude-code",
                     "gstack", "get-shit-done", "openspec",
                     "learn-claude-code"]
          },
          "tags": {
            "type": "array",
            "items": { "type": "string" }
          },
          "categories": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": ["planning", "architecture", "development",
                       "testing", "debugging", "review",
                       "deployment", "documentation", "workflow",
                       "session-management", "code-quality", "learning"]
            }
          },
          "platforms": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": ["claude-code", "opencode", "codex", "copilot"]
            }
          },
          "cost": {
            "type": "string",
            "enum": ["light", "medium", "heavy"]
          },
          "stability": {
            "type": "string",
            "enum": ["experimental", "beta", "stable"]
          },
          "path": {
            "type": "string",
            "description": "Duong dan tuong doi tu library/"
          }
        }
      }
    },
    "collections": {
      "type": "object",
      "additionalProperties": {
        "type": "string",
        "description": "Path tuong doi den collection JSON"
      }
    },
    "stacks": {
      "type": "object",
      "additionalProperties": {
        "type": "string",
        "description": "Path tuong doi den stack JSON"
      }
    }
  }
}
```

### 9.3. Collection/Stack JSON Schema

```json
{
  "type": "object",
  "required": ["name", "description", "skills"],
  "properties": {
    "name": { "type": "string" },
    "description": { "type": "string" },
    "skills": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^skill:.+$"
      },
      "description": "Danh sach skill IDs"
    },
    "agents": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^agent:.+$"
      },
      "description": "Danh sach agent IDs (optional)"
    }
  }
}
```

---

## 10. Session Hook va Proactive Mode

### 10.1. Khai niem

Lay cam hung tu `superpowers/hooks/session-start`, he thong co the tu dong inject context vao dau moi session de:
- Cho AI biet nhung skills nao da duoc publish trong project
- Goi y proactive khi nhan ra user dang lam gi

### 10.2. Cach Superpowers Lam (Tham khao)

```
superpowers/hooks/hooks.json:
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|clear|compact",
      "hooks": [{
        "type": "command",
        "command": "session-start script",
        "async": false
      }]
    }]
  }
}

session-start script:
  1. Doc using-superpowers/SKILL.md
  2. Escape cho JSON
  3. Output JSON voi hookSpecificOutput.additionalContext
  => Claude doc context nay va biet cach dung skills
```

### 10.3. Agent Hub Session Hook

**Thiet ke cho Agent Hub:**

```
project/.claude/settings.json:
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/Agent_Hub/scripts/session-context.py",
            "async": false
          }
        ]
      }
    ]
  }
}
```

**scripts/session-context.py:**

```python
#!/usr/bin/env python3
"""
Session hook script — inject Agent Hub context vao moi session.
Output JSON theo format Claude Code hooks yeu cau.
"""
import json
import os
import glob

def get_installed_skills():
    """Liet ke skills da publish trong project hien tai."""
    skills_dir = os.path.join(os.getcwd(), ".claude", "skills")
    if not os.path.isdir(skills_dir):
        return []
    return [d for d in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, d))]

def build_context():
    skills = get_installed_skills()
    if not skills:
        return ""

    context = "## Agent Hub Skills Available\n\n"
    context += "Skills da cai trong project nay:\n"
    for s in skills:
        context += f"- {s}\n"
    context += "\nDung Skill tool de invoke bat ky skill nao."
    context += "\nDung /librarian de tim va cai them skills."
    return context

def main():
    context = build_context()
    if not context:
        print(json.dumps({}))
        return

    # Claude Code format
    output = {
        "hookSpecificOutput": {
            "additionalContext": context
        }
    }
    print(json.dumps(output))

if __name__ == "__main__":
    main()
```

### 10.4. Luong Proactive Mode

```
  User bat dau session moi
          |
          v
  SessionStart hook chay
          |
          v
  session-context.py:
    1. Kiem tra .claude/skills/ co gi
    2. Tao context string
    3. Output JSON
          |
          v
  Claude nhan context:
    "Agent Hub Skills Available:
     - tdd
     - systematic-debugging
     - code-review
     Dung Skill tool de invoke.
     Dung /librarian de tim them."
          |
          v
  User lam viec binh thuong...
  User noi: "code nay co bug"
          |
          v
  Claude nhan ra: co skill "systematic-debugging" da publish
  Claude goi y: "Ban co muon dung skill systematic-debugging
                 de debug co he thong?"
          |
          v
  User: "ok"  ->  Claude invoke Skill tool  ->  Skill loaded
```

---

## 11. Ke hoach Trien khai

### 11.1. Thu tu Implement

```
  PHASE 1: Foundation (ngay 1-2)
  ==============================
  [1] Tao cau truc library/ (folders rong)
  [2] Dinh nghia SKILL.md frontmatter schema
  [3] Viet import-skill.py (phien ban co ban)
  [4] Import 5 skills dau tien de test:
      - tdd (tu superpowers)
      - systematic-debugging (tu superpowers)
      - code-review (tu everything-claude-code)
      - writing-plans (tu superpowers)
      - verification-before-completion (tu superpowers)

  PHASE 2: Catalog (ngay 3)
  =========================
  [5] Viet build-catalog.py
  [6] Tao catalog.json tu 5 skills
  [7] Viet validate.py
  [8] Validate library/

  PHASE 3: Publish (ngay 4-5)
  ============================
  [9]  Viet publish-to-project.py (Claude Code first)
  [10] Viet librarian.md agent
  [11] Test: publish skills vao 1 project thuc
  [12] Test: /librarian command hoat dong

  PHASE 4: Scale (ngay 6-8)
  ==========================
  [13] Import them ~35 skills (dat ~40 total)
  [14] Import ~10 agents
  [15] Tao collections/ (3-5 collections)
  [16] Tao stacks/ (2-3 stacks)
  [17] Rebuild catalog.json

  PHASE 5: Multi-platform (ngay 9-10)
  =====================================
  [18] Them OpenCode support vao publish-to-project.py
  [19] Them Codex support
  [20] Them Copilot support (instructions fragment)

  PHASE 6: Session Hook (ngay 11-12)
  ====================================
  [21] Viet session-context.py
  [22] Test proactive mode
  [23] Tao settings.json template de publish cung skills
```

### 11.2. Dependency Graph

```
  import-skill.py
       |
       v
  library/skills/*  +  library/agents/*
       |
       v
  build-catalog.py
       |
       v
  catalog.json
       |
       +----------> validate.py (kiem tra)
       |
       v
  publish-to-project.py  <---  librarian.md (goi script nay)
       |
       v
  project/.claude/skills/*
       |
       v
  session-context.py (doc skills da publish, inject context)
```

### 11.3. Loai bo Code cu

Cac file sau trong `agent-hub-index/` se bi **XOA** sau khi library/ hoat dong:

```
  XOA:
  - agent-hub-index/build-registry.py
  - agent-hub-index/registry.json
  - agent-hub-index/registry-index.json
  - agent-hub-index/registry.schema.json
  - agent-hub-index/domain-keywords.json
  - agent-hub-index/scripts/          (search.py va cac script cu)
  - agent-hub-index/mcp-server/
  - agent-hub-index/commands/
  - agent-hub-index/skills/

  GIU:
  - agent-hub-index/docs/             (tai lieu nay va docs khac)
```

---

## Phu luc A: Gia dinh va Rang buoc

| # | Gia dinh / Rang buoc                                                     |
|---|--------------------------------------------------------------------------|
| 1 | Python 3.10+ co san tren may                                            |
| 2 | 6 source projects da duoc clone tai ~/Agent_Hub/ va KHONG bi di chuyen  |
| 3 | Scripts chi dung Python standard library (khong can pip install)         |
| 4 | Claude Code la platform chinh, cac platform khac la secondary           |
| 5 | ~50 entries la muc tieu ban dau, co the tang sau                        |
| 6 | Librarian agent can Claude Code Skill tool de hoat dong                 |
| 7 | Session hook chi hoat dong tren Claude Code va OpenCode                 |
| 8 | catalog.json duoc rebuild thu cong (chay build-catalog.py) khi co thay doi |

## Phu luc B: Glossary

| Thuat ngu     | Dinh nghia                                                          |
|---------------|---------------------------------------------------------------------|
| **Skill**     | Tap huong dan (SKILL.md) ma AI agent doc va lam theo                |
| **Agent**     | System prompt cho sub-agent, dispatch qua Skill tool                |
| **Catalog**   | File JSON chua metadata cua tat ca entries trong library            |
| **Collection**| Nhom skills theo domain/use-case (vd: web-fullstack)               |
| **Stack**     | Nhom skills theo level/preset (vd: starter, pro-developer)         |
| **Publish**   | Hanh dong copy skill tu library/ vao project/.claude/               |
| **Librarian** | Agent chinh giup user tim va publish skills                         |
| **Curate**    | Quy trinh chon loc, chuan hoa va review skill truoc khi nhap kho   |
| **Warehouse** | Tier 1 — kho trung tam ~/Agent_Hub/library/                        |
| **Project Library** | Tier 2 — skills da publish trong project/.claude/              |
| **Proactive Mode**  | Session hook tu dong goi y skills khi nhan ra context phu hop  |
