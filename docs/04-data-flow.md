# 04 — Luong Du Lieu (Data Flow)

> Tai lieu mo ta chi tiet luong du lieu end-to-end cua he thong **Agent Hub** —
> tu nguon goc (source projects) den thu vien trung tam (library), den khi
> skill/agent duoc publish vao project cua nguoi dung.

---

## Muc luc

1. [So do tong quan End-to-End](#1-so-do-tong-quan-end-to-end)
2. [Flow 1: Import Pipeline](#2-flow-1-import-pipeline)
3. [Flow 2: Proactive Discovery (Session Hook)](#3-flow-2-proactive-discovery-session-hook)
4. [Flow 3: On-Demand Discovery (/librarian)](#4-flow-3-on-demand-discovery-librarian)
5. [Flow 4: Contribution — Them Skill Moi](#5-flow-4-contribution--them-skill-moi)
6. [Flow 5: Update Skills](#6-flow-5-update-skills)
7. [State Diagram — Vong doi cua mot Skill](#7-state-diagram--vong-doi-cua-mot-skill)
8. [Data Ownership & Flow Direction](#8-data-ownership--flow-direction)

---

## 1. So do tong quan End-to-End

```
 SOURCE PROJECTS (read-only)          AGENT HUB LIBRARY (trung tam)            TARGET PROJECT (cua nguoi dung)
 ==============================       ====================================      ================================

 superpowers/                    ┌──────────────────────────────────────┐
   skills/*/SKILL.md        ────>│                                      │
   agents/*.md               ────>│  ~/Agent_Hub/agent-hub-index/        │
 everything-claude-code/         │                                      │
   skills/*/SKILL.md        ────>│  ┌──────────────┐  ┌──────────────┐ │
   agents/*.md               ────>│  │ registry.json │  │ registry-    │ │
   commands/*.md             ────>│  │ (full, 407    │  │ index.json   │ │
   rules/**/*.md             ────>│  │  entries)     │  │ (lightweight)│ │
 gstack/                         │  └──────┬───────┘  └──────┬───────┘ │
   */SKILL.md                ────>│         │                  │         │
 get-shit-done/                  │         v                  v         │
   agents/*.md               ────>│  ┌──────────────────────────────┐   │
   commands/gsd/*.md         ────>│  │     search.py / /find-skills │   │
 openspec/                       │  │     (scoring + matching)      │   │
   .claude/skills/*/SKILL.md ───>│  └──────────────┬───────────────┘   │
 learn-claude-code/              │                  │                    │
   skills/*/SKILL.md         ───>│                  │                    │
                                 └──────────────────┼────────────────────┘
                                                    │
                                                    │  Publish / Install
                                                    v
                                 ┌──────────────────────────────────────────┐
                                 │  ~/my-project/                           │
                                 │    .claude/                              │
                                 │      skills/                             │
                                 │        systematic-debugging/SKILL.md     │
                                 │        brainstorming/SKILL.md            │
                                 │      commands/                           │
                                 │        find-skills.md                    │
                                 │    library-manifest.yaml                 │
                                 └──────────────────────────────────────────┘
```

### Huong di cua du lieu (tong quat)

```
  [1] SCAN          [2] BUILD           [3] SEARCH          [4] PUBLISH
  ─────────>        ─────────>          ─────────>           ─────────>

  Source       build-registry.py    registry.json       .claude/skills/
  Projects     (parse + infer)      registry-index.json library-manifest.yaml
  (6 repos)                         domain-keywords.json
```

**Nguyen tac cot loi:**
- Du lieu chay MOT CHIEU: Source --> Library --> Project
- Source projects la READ-ONLY (khong bao gio ghi nguoc lai)
- Project nhan BAN SAO (copy), khong phai symlink
- Library la SINGLE SOURCE OF TRUTH cho metadata

---

## 2. Flow 1: Import Pipeline

### 2.1 Tong quan

```
  Source Project (.md files)
         │
         │  [A] build-registry.py scan
         v
  Parse YAML frontmatter + body text
         │
         │  [B] Infer metadata (domains, technologies, phases)
         v
  Normalized registry entry (dict)
         │
         │  [C] Write JSON
         v
  registry.json + registry-index.json
```

### 2.2 Buoc A — Scan & Discovery

**Script:** `~/Agent_Hub/agent-hub-index/build-registry.py`

**Input:** Cau hinh SOURCES dict dinh nghia 6 source projects:

```python
SOURCES = {
    "superpowers": {
        "root": "~/Agent_Hub/superpowers",
        "patterns": [
            ("skills/*/SKILL.md", "skill"),    # glob pattern → type
            ("agents/*.md", "agent"),
        ],
        "platforms": ["claude-code", "codex", "opencode", "cursor"],
        "stability": "stable",
    },
    "everything-claude-code": {
        "root": "~/Agent_Hub/everything-claude-code",
        "patterns": [
            ("skills/*/SKILL.md", "skill"),
            ("agents/*.md", "agent"),
            ("commands/*.md", "command"),
            ("rules/**/*.md", "rule"),
        ],
        "platforms": None,  # doc tu manifests
        "stability": "stable",
        "manifests": "manifests/install-modules.json",
    },
    "gstack": {
        "root": "~/Agent_Hub/gstack",
        "patterns": [("*/SKILL.md", "skill")],
        "platforms": ["claude-code"],
        "stability": "beta",
        "exclude_dirs": ["browse", "test", "scripts", ...],
    },
    # ... get-shit-done, openspec, learn-claude-code
}
```

**Qua trinh Discovery:**

```
  root = ~/Agent_Hub/superpowers
         │
         │  glob("skills/*/SKILL.md")
         v
  [Path("skills/systematic-debugging/SKILL.md"), ...]
         │
         │  Loc exclude_dirs (node_modules, dist, .git, ...)
         v
  [(Path, "skill"), (Path, "skill"), ...]   ← danh sach (file, type)
```

**File I/O tai buoc nay:**
- Doc: `root.glob(pattern)` — chi doc ten file, chua doc noi dung
- Loc: kiem tra `path.relative_to(root).parts` khong chua exclude_dirs

### 2.3 Buoc B — Parse & Infer Metadata

**Cho moi file tim thay, goi `build_entry()`:**

```
  Input file: ~/Agent_Hub/superpowers/skills/systematic-debugging/SKILL.md
         │
         │  [B1] parse_md_file() — tach YAML frontmatter + body
         v
  frontmatter = {
      "name": "systematic-debugging",
      "description": "A structured approach to debugging...",
      "tools": ["Bash", "Read", "Grep"],
      "model": null,
      "version": "1.0"
  }
  body = "# Systematic Debugging\n\nWhen investigating bugs..."
         │
         │  [B2] Infer domains, technologies, phases
         v
  combined_text = name + description + body[:2000]
         │
         ├── infer_from_text(combined_text, DOMAIN_KEYWORDS)
         │     → domains = ["debugging"]
         │     (vi body chua "debug", "root cause", "trace")
         │
         ├── infer_from_text(combined_text, TECH_KEYWORDS)
         │     → technologies = []
         │     (khong match tech cu the nao)
         │
         ├── infer_from_text(combined_text, PHASE_KEYWORDS)
         │     → phases = ["debugging", "development"]
         │
         ├── infer_relevance_keywords(combined_text, kw_data)
         │     → ["debug", "root-cause", "trace", "investigation", ...]
         │     (toi da 60 keywords)
         │
         ├── infer_cost(path)
         │     → "medium"  (file size 5KB-20KB)
         │
         └── infer_stability(body, "stable")
               → "stable"  (khong chua "experimental", "wip", ...)
```

**Bang keyword matching (vi du):**

```
  domain-keywords.json:
  ┌──────────────┬──────────────────────────────────────────────────┐
  │ Domain       │ Keywords (match trong text)                      │
  ├──────────────┼──────────────────────────────────────────────────┤
  │ "robotics"   │ ros, ros2, lidar, slam, sensor, robot, nav2 ... │
  │ "debugging"  │ debug, bug, error, root cause, trace, crash ... │
  │ "web-frontend│ react, vue, angular, css, html, typescript ...  │
  │ "ai-ml"      │ llm, agent, embedding, model, pytorch ...       │
  └──────────────┴──────────────────────────────────────────────────┘
```

### 2.4 Buoc C — Build Registry Entry & Write JSON

**Output cua `build_entry()`:**

```json
{
  "id": "superpowers:systematic-debugging",
  "name": "systematic-debugging",
  "type": "skill",
  "source": "superpowers",
  "path": "$HOME/Agent_Hub/superpowers/skills/systematic-debugging/SKILL.md",
  "description": "A structured approach to debugging...",
  "domains": ["debugging"],
  "technologies": [],
  "phases": ["debugging", "development"],
  "platforms": ["claude-code", "codex", "cursor", "opencode"],
  "tools": ["Bash", "Read", "Grep"],
  "model": null,
  "preambleTier": null,
  "version": "1.0",
  "argumentHint": null,
  "relevanceKeywords": ["debug", "root-cause", "trace", ...],
  "cost": "medium",
  "stability": "stable",
  "relatedIds": [],
  "indexedAt": "2026-03-30T05:48:49.400094+00:00"
}
```

**Ghi 2 file output:**

```
  Toan bo entries (407 muc)
         │
         ├──> registry.json (FULL — ~950 KB)
         │    {
         │      "version": 1,
         │      "builtAt": "2026-03-30T05:48:49+00:00",
         │      "totalEntries": 407,
         │      "sources": ["superpowers", "everything-claude-code", ...],
         │      "entries": [ ... moi entry day du ... ]
         │    }
         │
         └──> registry-index.json (LIGHTWEIGHT — ~670 KB)
              {
                "version": 1,
                "builtAt": "2026-03-30T05:48:49+00:00",
                "totalEntries": 407,
                "entries": [
                  {
                    "id": "superpowers:systematic-debugging",
                    "name": "systematic-debugging",
                    "type": "skill",
                    "source": "superpowers",
                    "description": "A structured approach to debug...",  ← cat 300 ky tu
                    "domains": ["debugging"],
                    "technologies": [],
                    "phases": ["debugging", "development"],
                    "platforms": ["claude-code", "codex", "cursor", "opencode"],
                    "relevanceKeywords": [...],                          ← cat 40 keywords
                    "cost": "medium",
                    "stability": "stable"
                  }
                  // ... 406 entries khac
                ]
              }
```

**Khac biet giua 2 file:**

```
  ┌──────────────────────┬─────────────────────┬─────────────────────┐
  │ Truong               │ registry.json       │ registry-index.json │
  ├──────────────────────┼─────────────────────┼─────────────────────┤
  │ path                 │ Co (absolute path)  │ KHONG               │
  │ tools                │ Co                  │ KHONG               │
  │ model                │ Co                  │ KHONG               │
  │ preambleTier         │ Co                  │ KHONG               │
  │ version              │ Co                  │ KHONG               │
  │ argumentHint         │ Co                  │ KHONG               │
  │ relatedIds           │ Co                  │ KHONG               │
  │ indexedAt            │ Co                  │ KHONG               │
  │ description          │ Day du              │ Cat 300 ky tu       │
  │ relevanceKeywords    │ Toi da 60           │ Toi da 40           │
  │ Kich thuoc           │ ~950 KB             │ ~670 KB             │
  │ Muc dich             │ Full reference      │ Slash command search│
  └──────────────────────┴─────────────────────┴─────────────────────┘
```

### 2.5 So do toan bo Import Pipeline

```
  ~/Agent_Hub/superpowers/skills/systematic-debugging/SKILL.md
  ~/Agent_Hub/superpowers/skills/brainstorming/SKILL.md
  ~/Agent_Hub/superpowers/agents/dispatch-agent.md
  ~/Agent_Hub/everything-claude-code/skills/*/SKILL.md
  ~/Agent_Hub/gstack/*/SKILL.md
  ~/Agent_Hub/get-shit-done/agents/*.md
  ~/Agent_Hub/.claude/skills/openspec-*/SKILL.md
  ~/Agent_Hub/learn-claude-code/skills/*/SKILL.md
         │
         │  python build-registry.py
         │
         ├─[1]─ discover_files() cho moi source
         │       glob patterns → danh sach (Path, type)
         │
         ├─[2]─ parse_md_file() cho moi file
         │       regex FRONTMATTER_RE → (frontmatter_dict, body_text)
         │
         ├─[3]─ build_entry() cho moi file
         │       ├── extract name, description tu frontmatter
         │       ├── infer domains   ← domain-keywords.json DOMAIN_KEYWORDS
         │       ├── infer tech      ← domain-keywords.json TECH_KEYWORDS
         │       ├── infer phases    ← domain-keywords.json PHASE_KEYWORDS
         │       ├── infer cost      ← file size (light/medium/heavy)
         │       ├── infer stability ← body text + source default
         │       ├── extract tools   ← frontmatter "tools" hoac "allowed-tools"
         │       ├── extract related ← regex pattern "source:name" trong body
         │       └── relevance kw    ← tat ca keyword match + word extraction
         │
         ├─[4]─ Deduplicate by ID
         │       Neu trung id → append "-{count}" suffix
         │
         └─[5]─ json.dump()
                 ├── registry.json       (full, 407 entries, ~950 KB)
                 └── registry-index.json (light, 407 entries, ~670 KB)
```

---

## 3. Flow 2: Proactive Discovery (Session Hook)

### 3.1 Tong quan

Khi nguoi dung bat dau Claude Code trong mot project moi, session-start hook
tu dong phat hien stack cong nghe va de xuat skills phu hop.

```
  Nguoi dung bat dau Claude Code trong ~/my-ros2-project/
         │
         │  [A] Session-start hook fires
         v
  Kiem tra: co .claude/library-manifest.yaml khong?
         │
         ├── CO  → Doc manifest, kiem tra updates (→ Flow 5)
         │
         └── KHONG CO → Tiep tuc proactive discovery
                │
                │  [B] Scan project files
                v
         Scan: package.json, CMakeLists.txt, pyproject.toml,
               Cargo.toml, go.mod, package.xml, CLAUDE.md, ...
                │
                │  [C] Extract signals
                v
         technologies = ["cpp", "ros2", "python"]
         domains = ["robotics"]
         frameworks = ["nav2", "moveit"]
                │
                │  [D] Match against registry
                v
         search.py scoring → top matches
                │
                │  [E] Present recommendation
                v
         Librarian: "Du an nay dung ROS2 + C++. De xuat stack:
                     - systematic-debugging (score: 72)
                     - brainstorming (score: 65)
                     - ..."
                │
                │  [F] Nguoi dung chap nhan
                v
         Publish skills → .claude/skills/ + library-manifest.yaml
```

### 3.2 Buoc B — Scan Project Files

**Cac file duoc scan va tin hieu chung cung cap:**

```
  ┌──────────────────────┬──────────────────────────────────────────────┐
  │ File                 │ Tin hieu (Signal)                            │
  ├──────────────────────┼──────────────────────────────────────────────┤
  │ package.json         │ Node.js project                              │
  │                      │   dependencies → react, express, vue, ...    │
  │                      │   devDependencies → jest, vitest, ...        │
  ├──────────────────────┼──────────────────────────────────────────────┤
  │ CMakeLists.txt       │ C++ project                                  │
  │                      │   find_package(catkin) → ROS1                │
  │                      │   find_package(rclcpp) → ROS2                │
  │                      │   find_package(OpenCV) → computer vision     │
  ├──────────────────────┼──────────────────────────────────────────────┤
  │ pyproject.toml       │ Python project                               │
  │                      │   [tool.poetry] → dependencies               │
  │                      │   [build-system] → setuptools/flit/hatch     │
  ├──────────────────────┼──────────────────────────────────────────────┤
  │ package.xml          │ ROS2 package                                 │
  │                      │   <depend> → ros2 dependencies               │
  │                      │   <build_type> → ament_cmake / ament_python  │
  ├──────────────────────┼──────────────────────────────────────────────┤
  │ Cargo.toml           │ Rust project                                 │
  │                      │   [dependencies] → crate ecosystem           │
  ├──────────────────────┼──────────────────────────────────────────────┤
  │ go.mod               │ Go project                                   │
  │                      │   require → module dependencies              │
  ├──────────────────────┼──────────────────────────────────────────────┤
  │ Dockerfile           │ Container usage → devops domain              │
  ├──────────────────────┼──────────────────────────────────────────────┤
  │ CLAUDE.md            │ Existing Claude Code config                  │
  │                      │   Hints ve workflow, conventions             │
  ├──────────────────────┼──────────────────────────────────────────────┤
  │ .github/workflows/   │ CI/CD → devops, testing domains             │
  └──────────────────────┴──────────────────────────────────────────────┘
```

### 3.3 Buoc C — Extract Signals (Vi du cu the)

**Vi du: project ~/my-ros2-project/**

```
  Tim thay: CMakeLists.txt, package.xml, src/*.cpp, launch/*.py
         │
         │  Doc CMakeLists.txt:
         │    find_package(rclcpp REQUIRED)
         │    find_package(sensor_msgs REQUIRED)
         │    find_package(nav2_core REQUIRED)
         │
         │  Doc package.xml:
         │    <depend>rclcpp</depend>
         │    <depend>nav2_msgs</depend>
         │    <depend>tf2_ros</depend>
         v

  project_profile = {
      "technologies": ["cpp", "ros2"],
      "domains": ["robotics"],
      "keywords": ["rclcpp", "nav2", "sensor_msgs", "tf2_ros",
                    "navigation", "transforms"],
      "phases": []    ← khong xac dinh, match tat ca phases
  }
```

### 3.4 Buoc D — Match Against Registry

**Su dung `search.py` scoring algorithm:**

```python
# Cong thuc tinh diem (score_entry):

  Technology match:   20 diem/match truc tiep, 10 diem/match keyword
                      (toi da 40 diem)
  Domain match:       15 diem/match (toi da 30 diem)
  Phase overlap:      4 diem/match  (toi da 20 diem)
  Keyword in name:    3 diem/match  (toi da 10 diem)
  Keyword in entry:   2 diem/match  (khong gioi han)
```

**Vi du scoring cho project ROS2 + C++ o tren:**

```
  Entry: superpowers:systematic-debugging
  ┌──────────────────────────────────────────┬───────┐
  │ Tieu chi                                 │ Diem  │
  ├──────────────────────────────────────────┼───────┤
  │ Technology "cpp"? → KHONG match domains  │  +0   │
  │ Technology "ros2"? → KHONG match domains │  +0   │
  │ Domain "robotics"? → KHONG               │  +0   │
  │ Domain "debugging"? → khong co           │  +0   │
  │ Phases overlap (debugging, development)  │  +8   │
  │ Keyword "debug" in name/desc             │  +3   │
  │ Keyword matches in relevanceKeywords     │  +6   │
  ├──────────────────────────────────────────┼───────┤
  │ TONG                                     │  17   │
  └──────────────────────────────────────────┴───────┘

  Entry: gstack:investigate  (gia su co ros2 keywords)
  ┌──────────────────────────────────────────┬───────┐
  │ Technology "ros2" match                  │ +20   │
  │ Technology "cpp" match keyword           │ +10   │
  │ Domain "robotics" match                  │ +15   │
  │ Phases overlap                           │  +8   │
  │ Keyword matches                          │ +12   │
  ├──────────────────────────────────────────┼───────┤
  │ TONG                                     │  65   │
  └──────────────────────────────────────────┴───────┘
```

**Ket qua cuoi cung (sap xep theo diem, loc > 10):**

```json
{
  "query": "cpp ros2 robotics nav2 sensor_msgs tf2_ros",
  "profile": {
    "domains": ["robotics"],
    "technologies": ["cpp", "ros2"],
    "phases": [],
    "keywords": ["rclcpp", "nav2", "sensor_msgs", "tf2_ros"]
  },
  "totalMatches": 12,
  "grouped": {
    "development": [
      {"score": 65, "id": "gstack:investigate", ...},
      {"score": 52, "id": "superpowers:brainstorming", ...}
    ],
    "debugging": [
      {"score": 42, "id": "superpowers:systematic-debugging", ...}
    ],
    "planning": [
      {"score": 38, "id": "superpowers:writing-plans", ...}
    ]
  }
}
```

### 3.5 Buoc E — Librarian Presents Recommendation

```
  Librarian output (hien thi cho nguoi dung):
  ─────────────────────────────────────────────

  ## Recommended Skills & Agents for: ROS2 C++ Robotics Project

  **Tech:** cpp, ros2 | **Domains:** robotics
  *12 matches found across 3 phases*

  ### Phase: Development
  | Priority | Name           | Source      | Type  | Why                          |
  |----------|----------------|-------------|-------|------------------------------|
  | **HIGH** | `investigate`  | gstack      | skill | Deep code investigation...   |
  | HIGH     | `brainstorming`| superpowers | skill | Explore intent before impl.. |

  ### Phase: Debugging
  | MED      | `systematic-debugging` | superpowers | skill | Structured debugging... |

  ### Phase: Planning
  | MED      | `writing-plans`| superpowers | skill | Create detailed plans... |

  ---
  ## Activation Instructions
  **superpowers:**
  ```bash
  ln -s $HOME/Agent_Hub/superpowers ~/.claude/skills/superpowers
  ```
```

### 3.6 Buoc F — Publish to Project

**Sau khi nguoi dung chap nhan (approve):**

```
  Nguoi dung: "Yes, install systematic-debugging va brainstorming"
         │
         │  [F1] Copy SKILL.md files
         v
  ~/my-ros2-project/.claude/skills/
    ├── systematic-debugging/
    │   └── SKILL.md           ← ban sao tu superpowers
    └── brainstorming/
        └── SKILL.md           ← ban sao tu superpowers
         │
         │  [F2] Tao/cap nhat library-manifest.yaml
         v
  ~/my-ros2-project/.claude/library-manifest.yaml
```

**Noi dung `library-manifest.yaml` sau khi publish:**

```yaml
# Auto-generated by Agent Hub Librarian
# DO NOT EDIT MANUALLY — managed by /librarian
version: 1
generatedAt: "2026-03-30T12:00:00+07:00"
projectProfile:
  technologies: [cpp, ros2]
  domains: [robotics]
  detectedFrom: [CMakeLists.txt, package.xml]

publishedSkills:
  - id: "superpowers:systematic-debugging"
    name: "systematic-debugging"
    type: skill
    source: superpowers
    sourcePath: "$HOME/Agent_Hub/superpowers/skills/systematic-debugging/SKILL.md"
    publishedTo: ".claude/skills/systematic-debugging/SKILL.md"
    publishedAt: "2026-03-30T12:00:00+07:00"
    registryVersion: "1.0"
    checksum: "sha256:a1b2c3d4..."

  - id: "superpowers:brainstorming"
    name: "brainstorming"
    type: skill
    source: superpowers
    sourcePath: "$HOME/Agent_Hub/superpowers/skills/brainstorming/SKILL.md"
    publishedTo: ".claude/skills/brainstorming/SKILL.md"
    publishedAt: "2026-03-30T12:00:00+07:00"
    registryVersion: null
    checksum: "sha256:e5f6g7h8..."

stackApplied: null
totalPublished: 2
```

---

## 4. Flow 3: On-Demand Discovery (/librarian)

### 4.1 Tong quan

Nguoi dung chu dong yeu cau Librarian tim skill bang lenh `/librarian`.

```
  User: /librarian "I need debugging skills"
         │
         │  [A] Parse user intent
         v
  query = "debugging skills"
  intent = SEARCH
         │
         │  [B] Doc registry-index.json
         v
  407 entries loaded
         │
         │  [C] Extract profile tu query
         v
  profile = {
      "domains": ["debugging"],
      "technologies": [],
      "phases": ["debugging"],
      "keywords": ["debug", "skills"]
  }
         │
         │  [D] Score + Filter
         v
  scored_entries (sap xep giam dan theo diem)
         │
         │  [E] Doc library-manifest.yaml (neu co)
         v
  already_installed = ["superpowers:brainstorming"]
         │
         │  [F] Loc ra chi nhung skill CHUA cai
         v
  new_recommendations = scored_entries - already_installed
         │
         │  [G] Hien thi de xuat
         v
  Librarian presents recommendation
         │
         │  [H] Nguoi dung chon
         v
  Publish selected → .claude/skills/ + cap nhat manifest
```

### 4.2 Buoc C — Profile Extraction (Chi tiet)

```python
# search.py → extract_profile("I need debugging skills")

  query_lower = "i need debugging skills"
         │
         ├── DOMAIN_KEYWORDS scan:
         │     "debugging" keywords: ["debug", "root cause", "trace", ...]
         │     "debug" FOUND in query → domains = ["debugging"]
         │
         ├── TECH_KEYWORDS scan:
         │     Khong keyword nao match → technologies = []
         │
         ├── PHASE_KEYWORDS scan:
         │     "debugging" keywords: ["debug", "bug", "fix", ...]
         │     "debug" FOUND → phases = ["debugging"]
         │
         └── Extra keywords:
               words = ["need", "debugging", "skills"]
               filter STOP words → ["debugging", "skills"]
```

### 4.3 Buoc D — Scoring Chi Tiet

```
  Voi profile = {domains: ["debugging"], phases: ["debugging"]}

  ┌──────────────────────────────────────┬──────┬──────────────────────────────┐
  │ Entry                                │ Score│ Ly do                        │
  ├──────────────────────────────────────┼──────┼──────────────────────────────┤
  │ superpowers:systematic-debugging     │  52  │ domain=debugging(+15),       │
  │                                      │      │ phase=debugging(+4),         │
  │                                      │      │ "debug" in name(+3),         │
  │                                      │      │ keyword matches(+30)         │
  ├──────────────────────────────────────┼──────┼──────────────────────────────┤
  │ gstack:investigate                   │  28  │ phase match(+4),             │
  │                                      │      │ keyword partial(+24)         │
  ├──────────────────────────────────────┼──────┼──────────────────────────────┤
  │ superpowers:verification-before-     │  22  │ review phase overlap(+4),    │
  │ completion                           │      │ keyword matches(+18)         │
  ├──────────────────────────────────────┼──────┼──────────────────────────────┤
  │ everything-claude-code:bug-fixer     │  45  │ domain=debugging(+15),       │
  │                                      │      │ phase=debugging(+4),         │
  │                                      │      │ "bug" in name(+3),           │
  │                                      │      │ keywords(+23)               │
  └──────────────────────────────────────┴──────┴──────────────────────────────┘
```

### 4.4 Buoc E+F — Check Installed & Filter

```
  # Doc library-manifest.yaml cua project hien tai
  already_installed_ids = {
      "superpowers:brainstorming"    ← da cai tu truoc
  }

  # Loc:
  recommendations BEFORE filter:
    1. superpowers:systematic-debugging  (52)
    2. everything-claude-code:bug-fixer  (45)
    3. gstack:investigate                (28)
    4. superpowers:brainstorming         (22)  ← DA CAI

  recommendations AFTER filter:
    1. superpowers:systematic-debugging  (52)  ← MOI
    2. everything-claude-code:bug-fixer  (45)  ← MOI
    3. gstack:investigate                (28)  ← MOI
```

### 4.5 Buoc G — Hien Thi Ket Qua

```
  Librarian:

  Tim thay 3 skills moi phu hop voi yeu cau "debugging":

  1. [CRITICAL] systematic-debugging (superpowers)
     Mo ta: Structured approach to debugging with root cause analysis
     Phu hop: domain=debugging, phase=debugging

  2. [HIGH] bug-fixer (everything-claude-code)
     Mo ta: Automated bug investigation and fix suggestion
     Phu hop: domain=debugging

  3. [MED] investigate (gstack)
     Mo ta: Deep investigation into code issues
     Phu hop: phase=debugging

  (brainstorming da duoc cai, bo qua)

  Ban muon cai dat nhung skills nao? (all / chon so / cancel)
```

### 4.6 Buoc H — Publish va Cap Nhat Manifest

```
  User: "1, 2"  (chon systematic-debugging va bug-fixer)
         │
         │  Copy files
         v
  ~/my-ros2-project/.claude/skills/
    ├── brainstorming/SKILL.md            ← da co tu truoc
    ├── systematic-debugging/SKILL.md     ← MOI
    └── bug-fixer/SKILL.md                ← MOI
         │
         │  Cap nhat library-manifest.yaml
         v

  # library-manifest.yaml (sau cap nhat):
  publishedSkills:
    - id: "superpowers:brainstorming"          # cu
      publishedAt: "2026-03-30T12:00:00+07:00"

    - id: "superpowers:systematic-debugging"   # MOI
      publishedAt: "2026-03-30T14:30:00+07:00"

    - id: "everything-claude-code:bug-fixer"   # MOI
      publishedAt: "2026-03-30T14:30:00+07:00"

  totalPublished: 3   ← tang tu 1 len 3
```

---

## 5. Flow 4: Contribution — Them Skill Moi

### 5.1 Tong quan

```
  User: /librarian "I want to add a skill about ROS2 TF debugging"
         │
         │  [A] Parse intent → CONTRIBUTE (khong phai SEARCH)
         v
  Librarian nhan biet: "add a skill" → che do tao moi
         │
         │  [B] Tim kiem registry → khong co match chinh xac
         v
  search("ROS2 TF debugging") → khong entry nao co id "ros2-tf-debugging"
         │
         │  [C] Hoi intake questions
         v
  Librarian hoi nguoi dung cac cau hoi
         │
         │  [D] Generate SKILL.md skeleton
         v
  Tao ban nhap SKILL.md
         │
         │  [E] Nguoi dung review va chinh sua
         v
  SKILL.md hoan chinh
         │
         │  [F] Ghi vao library
         v
  ~/Agent_Hub/agent-hub-index/skills/ros2-tf-debugging/SKILL.md
         │
         │  [G] Tao provenance.yaml
         v
  ~/Agent_Hub/agent-hub-index/skills/ros2-tf-debugging/provenance.yaml
         │
         │  [H] Rebuild registry
         v
  python build-registry.py → registry.json (408 entries)
         │
         │  [I] Goi y them vao stack
         v
  "De xuat them ros2-tf-debugging vao ros2-robotics stack?"
```

### 5.2 Buoc C — Intake Questions

```
  Librarian:

  Toi se giup ban tao skill moi. Xin tra loi mot so cau hoi:

  1. SKILL nay giai quyet van de gi?
     User: "Debug ROS2 TF transform tree — tim loi khi TF frames
            bi thieu, sai orientation, hoac bi delay"

  2. Khi nao nen su dung skill nay?
     User: "Khi gặp lỗi tf2 lookup, transform timeout,
            hoặc robot di chuyển sai hướng"

  3. Cac cong cu (tools) can thiet?
     User: "Bash (ros2 run tf2_tools view_frames),
            Read (doc log files)"

  4. Technology/Domain nao?
     User: "ROS2, C++, Python — robotics domain"

  5. Co buoc nao bat buoc theo thu tu khong?
     User: "1. Chay view_frames.py de xem TF tree
            2. Kiem tra static vs dynamic transforms
            3. Kiem tra timestamp synchronization
            4. Fix va verify"
```

### 5.3 Buoc D — Generate SKILL.md Skeleton

```markdown
---
name: ros2-tf-debugging
description: >
  Debug ROS2 TF transform tree — phat hien va sua loi khi TF frames
  bi thieu, sai orientation, hoac bi delay.
tools:
  - Bash
  - Read
  - Grep
---

# ROS2 TF Transform Debugging

## Khi nao su dung
- Khi gap loi `tf2::LookupException` hoac `transform timeout`
- Khi robot di chuyen sai huong do TF sai
- Khi can verify TF tree sau khi thay doi URDF/xacro

## Quy trinh

### Buoc 1: Xem TF Tree hien tai
```bash
ros2 run tf2_tools view_frames
# Output: frames.pdf — so do TF tree
```

### Buoc 2: Kiem tra Static vs Dynamic Transforms
```bash
ros2 topic echo /tf_static --once
ros2 topic echo /tf --once
```

### Buoc 3: Kiem tra Timestamp Synchronization
```bash
ros2 topic hz /tf
ros2 topic delay /tf
```

### Buoc 4: Fix va Verify
- Sua URDF/xacro neu frame bi thieu
- Kiem tra static_transform_publisher parameters
- Verify: chay view_frames lai → confirm tree dung

## Anti-patterns
- KHONG doan transform — luon verify bang view_frames
- KHONG bo qua timestamp warnings
```

### 5.4 Buoc F+G — Ghi vao Library

**Cau truc file sau khi ghi:**

```
  ~/Agent_Hub/agent-hub-index/skills/ros2-tf-debugging/
    ├── SKILL.md              ← noi dung skill
    └── provenance.yaml       ← metadata nguon goc
```

**Noi dung `provenance.yaml`:**

```yaml
# Provenance metadata — auto-generated by Librarian
id: "agent-hub-index:ros2-tf-debugging"
createdBy: user
createdAt: "2026-03-30T15:00:00+07:00"
origin: custom                        # khong phai import tu source project
sourceProject: null                   # khong co source project goc
contributors:
  - dkhai
tags: [ros2, tf2, transforms, debugging, robotics]
changelog:
  - version: "1.0"
    date: "2026-03-30"
    note: "Initial creation via /librarian intake"
```

### 5.5 Buoc H — Rebuild Registry

```
  python build-registry.py
         │
         │  Scan tat ca sources BAO GOM agent-hub-index/skills/
         v

  NEW entry duoc tao:
  {
    "id": "agent-hub-index:ros2-tf-debugging",
    "name": "ros2-tf-debugging",
    "type": "skill",
    "source": "agent-hub-index",
    "path": "$HOME/Agent_Hub/agent-hub-index/skills/ros2-tf-debugging/SKILL.md",
    "description": "Debug ROS2 TF transform tree...",
    "domains": ["debugging", "robotics"],
    "technologies": ["cpp", "python", "ros2"],
    "phases": ["debugging"],
    "platforms": ["claude-code"],
    "tools": ["Bash", "Read", "Grep"],
    "relevanceKeywords": ["ros2", "tf2", "transform", "debug", ...],
    "cost": "medium",
    "stability": "stable",
    "indexedAt": "2026-03-30T15:01:00+00:00"
  }

  registry.json: 407 → 408 entries
  registry-index.json: 407 → 408 entries
```

### 5.6 Buoc I — Goi Y Stack

```
  Librarian:

  Skill "ros2-tf-debugging" da duoc them thanh cong!

  Nhan thay skill nay phu hop voi nhom ROS2/robotics.
  Hien tai co cac skills lien quan:
    - superpowers:systematic-debugging  (domains: debugging)
    - gstack:investigate                (domains: debugging)

  Ban co muon tao mot "ros2-robotics" stack gom:
    - ros2-tf-debugging
    - systematic-debugging
    - brainstorming
    - writing-plans
  de tu dong de xuat cho cac du an ROS2 sau nay khong?
```

---

## 6. Flow 5: Update Skills

### 6.1 Tong quan

```
  User: /librarian "Update my skills"
         │
         │  [A] Doc library-manifest.yaml
         v
  publishedSkills = [
    {id: "superpowers:systematic-debugging",
     publishedAt: "2026-03-30T12:00:00",
     checksum: "sha256:a1b2c3d4..."},
    {id: "superpowers:brainstorming",
     publishedAt: "2026-03-30T12:00:00",
     checksum: "sha256:e5f6g7h8..."},
    {id: "everything-claude-code:bug-fixer",
     publishedAt: "2026-03-30T14:30:00",
     checksum: "sha256:i9j0k1l2..."}
  ]
         │
         │  [B] So sanh voi library version
         v
  Cho moi entry:
    doc source file → tinh checksum hien tai
    so sanh voi checksum da luu
         │
         │  [C] Xac dinh entries can update
         v
  updates_available = [
    {id: "superpowers:systematic-debugging",
     reason: "source file changed",
     publishedChecksum: "sha256:a1b2c3d4...",
     currentChecksum:   "sha256:x9y8z7w6..."}
  ]
         │
         │  [D] Trinh bay cho nguoi dung
         v
  Librarian: "1 skill co ban cap nhat: systematic-debugging"
         │
         │  [E] Nguoi dung chap nhan
         v
  Re-publish va cap nhat manifest
```

### 6.2 Buoc B — So sanh Versions (Chi tiet)

```
  # Cho moi publishedSkill trong manifest:

  entry = {
      id: "superpowers:systematic-debugging",
      sourcePath: "$HOME/Agent_Hub/superpowers/skills/systematic-debugging/SKILL.md",
      checksum: "sha256:a1b2c3d4..."    ← checksum luc publish
  }

  # Doc file nguon hien tai:
  current_file = read(entry.sourcePath)
  current_checksum = sha256(current_file)
         │
         ├── current_checksum == entry.checksum
         │     → KHONG CAN UPDATE (file khong thay doi)
         │
         └── current_checksum != entry.checksum
               → CAN UPDATE (file da thay doi ke tu lan publish cuoi)
               │
               ├── Kiem tra them: file co ton tai khong?
               │     Khong → DEPRECATED (source da xoa)
               │
               └── Co → tinh diff va bao cao thay doi
```

### 6.3 Buoc D — Bao Cao Updates

```
  Librarian:

  === Kiem tra cap nhat skills ===

  Da kiem tra 3 skills trong project nay:

  ┌─────────────────────────────┬────────────┬─────────────────────┐
  │ Skill                       │ Trang thai │ Chi tiet            │
  ├─────────────────────────────┼────────────┼─────────────────────┤
  │ systematic-debugging        │ CO UPDATE  │ Source thay doi     │
  │ (superpowers)               │            │ 2026-03-30 vs       │
  │                             │            │ 2026-03-28 (publish)│
  ├─────────────────────────────┼────────────┼─────────────────────┤
  │ brainstorming (superpowers) │ Moi nhat   │ Khong thay doi      │
  ├─────────────────────────────┼────────────┼─────────────────────┤
  │ bug-fixer (ecc)             │ Moi nhat   │ Khong thay doi      │
  └─────────────────────────────┴────────────┴─────────────────────┘

  1 skill co ban cap nhat. Cap nhat? (yes/no)
```

### 6.4 Buoc E — Re-publish

```
  User: "yes"
         │
         │  [E1] Copy file moi
         v
  cp $HOME/Agent_Hub/superpowers/skills/systematic-debugging/SKILL.md \
     ~/my-ros2-project/.claude/skills/systematic-debugging/SKILL.md
         │
         │  [E2] Cap nhat manifest
         v

  # library-manifest.yaml (TRUOC):
  - id: "superpowers:systematic-debugging"
    publishedAt: "2026-03-28T10:00:00+07:00"
    checksum: "sha256:a1b2c3d4..."

  # library-manifest.yaml (SAU):
  - id: "superpowers:systematic-debugging"
    publishedAt: "2026-03-30T16:00:00+07:00"       ← cap nhat
    checksum: "sha256:x9y8z7w6..."                  ← checksum moi
    previousChecksum: "sha256:a1b2c3d4..."          ← luu checksum cu
    updatedAt: "2026-03-30T16:00:00+07:00"
    updateNote: "Source file updated in superpowers repo"
```

---

## 7. State Diagram — Vong doi cua mot Skill

### 7.1 So do States

```
                          ┌──────────────────────┐
                          │                      │
                          │    [IN SOURCE]       │
                          │                      │
                          │  File .md ton tai    │
                          │  trong source project│
                          └──────────┬───────────┘
                                     │
                  build-registry.py  │  Dieu kien: file match glob pattern
                  scan + parse       │  va khong trong exclude_dirs
                                     v
                          ┌──────────────────────┐
                          │                      │
                          │  [INDEXED IN         │
                          │   REGISTRY]          │
                          │                      │
                          │  Entry trong         │
                          │  registry.json       │
                          └──────────┬───────────┘
                                     │
                  /librarian hoac    │  Dieu kien: nguoi dung chap nhan
                  session hook       │  de xuat cua Librarian
                  → publish          │
                                     v
                          ┌──────────────────────┐
                          │                      │
                          │  [PUBLISHED TO       │
                          │   PROJECT]           │
                          │                      │
                          │  Ban sao trong       │
                          │  .claude/skills/     │
                          │  + manifest entry    │
                          └──────────┬───────────┘
                                     │
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    v                v                v
          ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
          │              │ │              │ │                  │
          │ [UPDATED]    │ │ [CURRENT]    │ │ [DEPRECATED]     │
          │              │ │              │ │                  │
          │ Source thay  │ │ Khong thay   │ │ Source bi xoa    │
          │ doi → re-    │ │ doi, hoat    │ │ hoac khong con   │
          │ publish      │ │ dong binh   │ │ trong registry   │
          │              │ │ thuong       │ │                  │
          └──────┬───────┘ └──────────────┘ └──────────────────┘
                 │
                 │  Sau khi re-publish
                 │  thanh cong
                 v
          ┌──────────────┐
          │ [PUBLISHED   │
          │  TO PROJECT] │ ← quay ve trang thai published
          └──────────────┘
```

### 7.2 Bang chuyen trang thai

```
  ┌──────────────────┬──────────────────┬─────────────────────────────────────┐
  │ Tu trang thai    │ Den trang thai   │ Dieu kien / Trigger                 │
  ├──────────────────┼──────────────────┼─────────────────────────────────────┤
  │ IN SOURCE        │ INDEXED          │ build-registry.py chay thanh cong,  │
  │                  │                  │ file match pattern, parse OK        │
  ├──────────────────┼──────────────────┼─────────────────────────────────────┤
  │ INDEXED          │ PUBLISHED        │ Nguoi dung approve qua /librarian   │
  │                  │                  │ hoac session hook                   │
  ├──────────────────┼──────────────────┼─────────────────────────────────────┤
  │ PUBLISHED        │ CURRENT          │ checksum match — khong can lam gi   │
  ├──────────────────┼──────────────────┼─────────────────────────────────────┤
  │ PUBLISHED        │ UPDATED          │ checksum khac — source da thay doi  │
  ├──────────────────┼──────────────────┼─────────────────────────────────────┤
  │ PUBLISHED        │ DEPRECATED       │ Source file bi xoa hoac entry bi    │
  │                  │                  │ loai khoi registry                  │
  ├──────────────────┼──────────────────┼─────────────────────────────────────┤
  │ UPDATED          │ PUBLISHED        │ Nguoi dung chap nhan re-publish     │
  ├──────────────────┼──────────────────┼─────────────────────────────────────┤
  │ DEPRECATED       │ (removed)        │ Nguoi dung dong y xoa khoi project  │
  ├──────────────────┼──────────────────┼─────────────────────────────────────┤
  │ (khong co)       │ IN SOURCE        │ User tao skill moi qua /librarian   │
  │                  │                  │ contribution flow (Flow 4)          │
  └──────────────────┴──────────────────┴─────────────────────────────────────┘
```

### 7.3 Lich su Skill trong Manifest

```yaml
# Mot skill da trai qua nhieu trang thai:
- id: "superpowers:systematic-debugging"
  name: "systematic-debugging"
  type: skill
  source: superpowers
  state: published              # trang thai hien tai

  history:
    - action: published
      at: "2026-03-28T10:00:00+07:00"
      checksum: "sha256:a1b2c3d4..."

    - action: update-available
      at: "2026-03-30T08:00:00+07:00"
      note: "Source changed — new checksum detected"

    - action: updated
      at: "2026-03-30T16:00:00+07:00"
      checksum: "sha256:x9y8z7w6..."
      previousChecksum: "sha256:a1b2c3d4..."
```

---

## 8. Data Ownership & Flow Direction

### 8.1 Bang Ownership

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                          DATA OWNERSHIP MAP                            │
  ├────────────────────┬────────────────────┬───────────────────────────────┤
  │ Component          │ Owner              │ Quyen truy cap                │
  ├════════════════════╪════════════════════╪═══════════════════════════════┤
  │                    │                    │                               │
  │ SOURCE PROJECTS    │                    │                               │
  │ (6 repositories)   │                    │                               │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ skills/*/SKILL.md  │ Source project     │ READ-ONLY boi Agent Hub.      │
  │ agents/*.md        │ maintainers        │ Agent Hub chi doc, KHONG BAO  │
  │ commands/*.md      │                    │ GIO ghi nguoc lai.            │
  │ rules/**/*.md      │                    │                               │
  ├════════════════════╪════════════════════╪═══════════════════════════════┤
  │                    │                    │                               │
  │ AGENT HUB LIBRARY  │                    │                               │
  │ (agent-hub-index)  │                    │                               │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ registry.json      │ Agent Hub          │ WRITE boi build-registry.py.  │
  │                    │ (build script)     │ READ boi search.py,           │
  │                    │                    │ /find-skills, Librarian.      │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ registry-index.json│ Agent Hub          │ WRITE boi build-registry.py.  │
  │                    │ (build script)     │ READ boi search.py (offline). │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ domain-keywords.json│ Agent Hub         │ READ-ONLY config.             │
  │                    │ (manual config)    │ Chinh sua thu cong khi can    │
  │                    │                    │ them domain/tech keywords.    │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ registry.schema.json│ Agent Hub         │ READ-ONLY schema validation.  │
  │                    │ (manual config)    │                               │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ skills/ (custom)   │ Agent Hub          │ WRITE boi Librarian khi user  │
  │                    │ (user-contributed) │ tao skill moi (Flow 4).       │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ scripts/search.py  │ Agent Hub          │ EXECUTE boi /find-skills.     │
  │                    │                    │ READ registry-index.json.     │
  ├════════════════════╪════════════════════╪═══════════════════════════════┤
  │                    │                    │                               │
  │ TARGET PROJECT     │                    │                               │
  │ (cua nguoi dung)   │                    │                               │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ .claude/skills/    │ Project            │ WRITE boi Librarian khi       │
  │ (ban sao)          │ (nguoi dung)       │ publish. READ boi Claude Code │
  │                    │                    │ runtime. Nguoi dung co the    │
  │                    │                    │ xoa/sua truc tiep.            │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ .claude/commands/  │ Project            │ WRITE boi Librarian.          │
  │ (ban sao)          │ (nguoi dung)       │ READ boi Claude Code runtime. │
  ├────────────────────┼────────────────────┼───────────────────────────────┤
  │ library-manifest   │ Project            │ WRITE boi Librarian.          │
  │ .yaml              │ (Librarian quanly) │ READ boi Librarian de kiem    │
  │                    │                    │ tra installed/update.         │
  │                    │                    │ Nguoi dung KHONG NEN sua      │
  │                    │                    │ thu cong.                     │
  └────────────────────┴────────────────────┴───────────────────────────────┘
```

### 8.2 Huong Di Cua Du Lieu (Data Flow Direction)

```
  SOURCE PROJECTS                AGENT HUB LIBRARY              TARGET PROJECT
  ================               ====================           ===============

  superpowers/          ──READ──>  build-registry.py
  everything-claude-code/ ─READ─>      │
  gstack/               ──READ──>      │
  get-shit-done/        ──READ──>      │
  openspec/             ──READ──>      │
  learn-claude-code/    ──READ──>      │
                                       │ WRITE
                                       v
                                  registry.json
                                  registry-index.json
                                       │
                                       │ READ
                                       v
                                  search.py / Librarian
                                       │
                                       │ READ source files
                                       │ (resolve path tu registry entry)
                                       v
  superpowers/skills/   <──READ───  Librarian doc SKILL.md goc
  brainstorming/SKILL.md              │
                                       │ WRITE (copy)
                                       v
                                  .claude/skills/         ← TARGET PROJECT
                                  brainstorming/SKILL.md
                                  library-manifest.yaml
```

### 8.3 Nguyen tac du lieu quan trong

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  NGUYEN TAC #1: Mot chieu (Unidirectional)                          │
  │                                                                      │
  │    Source ───────> Library ───────> Project                          │
  │           (scan)           (publish)                                 │
  │                                                                      │
  │    KHONG BAO GIO: Project ──x──> Source                             │
  │    KHONG BAO GIO: Library ──x──> Source                             │
  └──────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │  NGUYEN TAC #2: Ban sao (Copy, not Reference)                       │
  │                                                                      │
  │    Project nhan BAN SAO cua SKILL.md, KHONG PHAI symlink.           │
  │    Ly do:                                                            │
  │    - Project co the hoat dong doc lap (offline)                      │
  │    - Xoa Agent Hub khong lam hong project                           │
  │    - Version control: biet chinh xac version nao dang dung          │
  └──────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │  NGUYEN TAC #3: Library la Single Source of Truth                    │
  │                                                                      │
  │    registry.json chua TOAN BO metadata da chuan hoa.                │
  │    Moi thao tac tim kiem, matching, scoring deu dua tren            │
  │    registry, KHONG doc truc tiep source projects.                   │
  │                                                                      │
  │    Ngoai tru: luc publish (can doc file goc de copy).               │
  └──────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │  NGUYEN TAC #4: Manifest theo doi trang thai                        │
  │                                                                      │
  │    library-manifest.yaml trong moi project theo doi:                │
  │    - Nhung gi da duoc cai dat (published skills)                    │
  │    - Khi nao cai dat (timestamps)                                   │
  │    - Phien ban nao (checksums)                                      │
  │    - Profile project (technologies, domains)                         │
  │                                                                      │
  │    Day la nguon du lieu DUY NHAT de Librarian biet                  │
  │    trang thai cua project ma khong can scan lai.                    │
  └──────────────────────────────────────────────────────────────────────┘
```

### 8.4 So Do Tong Hop — Tat Ca Files & Ownership

```
  ~/Agent_Hub/
  ├── superpowers/                          ← [OWNER: superpowers repo]
  │   ├── skills/
  │   │   ├── systematic-debugging/
  │   │   │   └── SKILL.md                  ← READ-ONLY boi Agent Hub
  │   │   ├── brainstorming/
  │   │   │   └── SKILL.md                  ← READ-ONLY boi Agent Hub
  │   │   └── ... (14 skills)
  │   └── agents/*.md                       ← READ-ONLY boi Agent Hub
  │
  ├── everything-claude-code/               ← [OWNER: ecc repo]
  │   ├── skills/*/SKILL.md                 ← READ-ONLY
  │   ├── agents/*.md                       ← READ-ONLY
  │   ├── commands/*.md                     ← READ-ONLY
  │   └── rules/**/*.md                     ← READ-ONLY
  │
  ├── gstack/                               ← [OWNER: gstack repo]
  │   └── */SKILL.md                        ← READ-ONLY
  │
  ├── get-shit-done/                        ← [OWNER: gsd repo]
  │   ├── agents/*.md                       ← READ-ONLY
  │   └── commands/gsd/*.md                 ← READ-ONLY
  │
  ├── learn-claude-code/                    ← [OWNER: lcc repo]
  │   └── skills/*/SKILL.md                 ← READ-ONLY
  │
  ├── .claude/skills/openspec-*/SKILL.md    ← [OWNER: openspec]
  │
  └── agent-hub-index/                      ← [OWNER: Agent Hub]
      ├── build-registry.py                 ← Build script (EXECUTE)
      ├── domain-keywords.json              ← Config (READ, manual edit)
      ├── registry.schema.json              ← Schema (READ)
      ├── registry.json                     ← GENERATED (WRITE by build)
      ├── registry-index.json               ← GENERATED (WRITE by build)
      ├── scripts/
      │   └── search.py                     ← Search engine (EXECUTE)
      ├── skills/                           ← User-contributed skills
      │   ├── find-skills/                  ← [OWNER: Agent Hub]
      │   └── ros2-tf-debugging/            ← [OWNER: User via Librarian]
      │       ├── SKILL.md
      │       └── provenance.yaml
      └── docs/
          └── 04-data-flow.md               ← Tai lieu nay

  ~/my-project/                              ← [OWNER: Nguoi dung]
  ├── .claude/
  │   ├── skills/
  │   │   ├── systematic-debugging/
  │   │   │   └── SKILL.md                  ← BAN SAO (WRITE by Librarian)
  │   │   └── brainstorming/
  │   │       └── SKILL.md                  ← BAN SAO (WRITE by Librarian)
  │   └── commands/
  │       └── find-skills.md                ← BAN SAO (WRITE by Librarian)
  └── .claude/library-manifest.yaml         ← MANAGED by Librarian
```

---

## Phu luc: Tom tat cac dinh dang du lieu

### A. Registry Entry (JSON) — schema day du

```json
{
  "id":                "string — '{source}:{name}', VD: 'superpowers:systematic-debugging'",
  "name":              "string — ten skill/agent/command",
  "type":              "enum — 'skill' | 'agent' | 'command' | 'rule'",
  "source":            "enum — 'superpowers' | 'everything-claude-code' | 'gstack' | 'get-shit-done' | 'openspec' | 'learn-claude-code'",
  "path":              "string — duong dan tuyet doi den file .md goc",
  "description":       "string — mo ta ngan",
  "domains":           "string[] — ['robotics', 'debugging', 'web-frontend', ...]",
  "technologies":      "string[] — ['python', 'cpp', 'ros2', 'react', ...]",
  "phases":            "string[] — ['planning', 'development', 'debugging', ...]",
  "platforms":         "string[] — ['claude-code', 'opencode', 'codex', 'cursor', 'copilot']",
  "tools":             "string[] — ['Bash', 'Read', 'Grep', ...]",
  "model":             "string|null — model requirement",
  "preambleTier":      "int|null — muc uu tien (gstack)",
  "version":           "string|null — phien ban skill",
  "argumentHint":      "string|null — goi y tham so (get-shit-done)",
  "relevanceKeywords": "string[] — keywords de match (toi da 60)",
  "cost":              "enum — 'light' | 'medium' | 'heavy'",
  "stability":         "enum — 'experimental' | 'beta' | 'stable'",
  "relatedIds":        "string[] — IDs cua skills lien quan",
  "indexedAt":         "string — ISO timestamp luc index"
}
```

### B. Library Manifest (YAML) — trong project nguoi dung

```yaml
version: 1
generatedAt: "ISO timestamp"
projectProfile:
  technologies: [string]
  domains: [string]
  detectedFrom: [string]        # ten cac file da scan

publishedSkills:
  - id: "string"                # registry entry ID
    name: "string"
    type: "string"
    source: "string"
    sourcePath: "string"        # duong dan tuyet doi den file goc
    publishedTo: "string"       # duong dan tuong doi trong project
    publishedAt: "ISO timestamp"
    registryVersion: "string|null"
    checksum: "string"          # sha256 cua file luc publish
    updatedAt: "ISO timestamp"  # (optional) lan cap nhat cuoi
    previousChecksum: "string"  # (optional) checksum truoc khi update

stackApplied: "string|null"     # ten stack da ap dung (neu co)
totalPublished: int
```

### C. Provenance (YAML) — cho skill tao boi nguoi dung

```yaml
id: "string"                    # registry entry ID
createdBy: "string"             # user identifier
createdAt: "ISO timestamp"
origin: "custom|imported"       # custom = tao moi, imported = tu source
sourceProject: "string|null"    # ten source project (neu imported)
contributors: [string]
tags: [string]
changelog:
  - version: "string"
    date: "YYYY-MM-DD"
    note: "string"
```
