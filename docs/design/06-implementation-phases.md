# 06 - Kế Hoạch Triển Khai Chi Tiết: Agent Hub

> **Dự án:** Agent Hub — Thư viện Skills/Agents cá nhân với AI Librarian
> **Tổng thời gian ước tính:** 9-16 giờ (5 phases chính + 1 phase tùy chọn)
> **Ngày tạo:** 2026-03-30
> **Cập nhật lần cuối:** 2026-03-30

---

## Mục Lục

- [Tổng Quan Kiến Trúc](#tổng-quan-kiến-trúc)
- [Phase 0: Dọn Dẹp (Cleanup)](#phase-0-dọn-dẹp-cleanup--30-phút)
- [Phase 1: Hạ Tầng Thư Viện (Library Infrastructure)](#phase-1-hạ-tầng-thư-viện-library-infrastructure--2-4-giờ)
- [Phase 2: Collections & Stacks](#phase-2-collections--stacks--2-3-giờ)
- [Phase 3: The Librarian](#phase-3-the-librarian--3-5-giờ)
- [Phase 4: Integration Test & Polish](#phase-4-integration-test--polish--1-2-giờ)
- [Phase 5: Multi-platform (Tùy chọn)](#phase-5-multi-platform-tùy-chọn--1-2-giờ)
- [Timeline Summary](#timeline-summary)
- [Risk Assessment](#risk-assessment)
- [Dependencies Graph](#dependencies-graph)

---

## Tổng Quan Kiến Trúc

```
Agent_Hub/
├── agent-hub-index/                    # <-- Dự án này
│   ├── docs/                           # Tài liệu thiết kế (GIỮ LẠI)
│   │   ├── 01-*.md ... 05-*.md
│   │   └── 06-implementation-phases.md # File này
│   ├── library/                        # THƯ VIỆN CHÍNH (MỚI)
│   │   ├── skills/                     # Skills đã import + chuẩn hóa
│   │   │   ├── systematic-debugging/
│   │   │   │   ├── SKILL.md
│   │   │   │   └── provenance.yaml
│   │   │   └── ...
│   │   ├── agents/                     # Agents đã import + Librarian
│   │   │   ├── code-reviewer/
│   │   │   │   ├── AGENT.md
│   │   │   │   └── provenance.yaml
│   │   │   ├── librarian.md            # AI Librarian (Phase 3)
│   │   │   └── ...
│   │   ├── collections/                # Bộ sưu tập theo workflow
│   │   │   ├── tdd-first.yaml
│   │   │   ├── debugging-deep-dive.yaml
│   │   │   ├── plan-driven-development.yaml
│   │   │   └── devops-ship-cycle.yaml
│   │   ├── stacks/                     # Bộ sưu tập theo tech stack
│   │   │   ├── ros2-robotics.yaml
│   │   │   ├── web-fullstack-typescript.yaml
│   │   │   ├── ml-research-pytorch.yaml
│   │   │   └── api-service-go.yaml
│   │   └── catalog.json               # Auto-generated catalog
│   ├── scripts/                        # Build & utility scripts (MỚI)
│   │   ├── import-skill.py
│   │   ├── build-catalog.py
│   │   ├── validate.py
│   │   ├── publish-to-project.py
│   │   └── rebuild.sh
│   ├── commands/                        # Slash commands
│   │   └── librarian.md
│   └── hooks/                           # Hook configuration
│       ├── hooks.json
│       └── session-start
│
├── superpowers/                         # Source: superpowers
├── everything-claude-code/              # Source: everything-claude-code
├── gstack/                              # Source: gstack
├── get-shit-done/                       # Source: get-shit-done
└── learn-claude-code/                   # Source: learn-claude-code
```

### Quy ước đặt tên

| Loại | Thư mục trong library/ | Tên entry | File chính |
|------|----------------------|-----------|------------|
| Skill | `skills/{slug}/` | `slug` (kebab-case) | `SKILL.md` |
| Agent | `agents/{slug}/` | `slug` (kebab-case) | `AGENT.md` |
| Collection | `collections/` | `{slug}.yaml` | YAML file |
| Stack | `stacks/` | `{slug}.yaml` | YAML file |

### Provenance YAML Schema

Mỗi skill/agent được import phải có `provenance.yaml`:

```yaml
# provenance.yaml
id: "systematic-debugging"
source: "superpowers"
source_path: "skills/systematic-debugging/SKILL.md"
imported_at: "2026-03-30T12:00:00Z"
version: "1.0"
type: "skill"
original_id: "superpowers:systematic-debugging"
```

---

## Phase 0: Dọn Dẹp (Cleanup) — 30 phút

### Mục tiêu
Xóa toàn bộ code cũ (v1 prototype) và tạo cấu trúc thư mục mới sạch sẽ. Giữ lại thư mục `docs/` chứa tài liệu thiết kế.

### Deliverable 0.1: Xóa các file cũ

**File cần xóa:**

| # | File | Lý do xóa |
|---|------|-----------|
| 1 | `agent-hub-index/build-registry.py` | Thay bằng `scripts/import-skill.py` + `scripts/build-catalog.py` |
| 2 | `agent-hub-index/scripts/search.py` | Chức năng search sẽ tích hợp vào Librarian agent |
| 3 | `agent-hub-index/registry.json` | Thay bằng `library/catalog.json` |
| 4 | `agent-hub-index/registry-index.json` | Thay bằng `library/catalog.json` (lightweight) |
| 5 | `agent-hub-index/registry.schema.json` | Schema mới sẽ embed trong `build-catalog.py` |
| 6 | `agent-hub-index/domain-keywords.json` | Keywords sẽ tích hợp vào `build-catalog.py` |

**Các bước thực hiện:**

```bash
cd $HOME/Agent_Hub/agent-hub-index

# Bước 1: Backup trước khi xóa (an toàn)
mkdir -p ~/.agent_hub_backups/backup-$(date +%Y%m%d)
cp build-registry.py scripts/search.py registry.json registry-index.json \
   registry.schema.json domain-keywords.json \
   ~/.agent_hub_backups/backup-$(date +%Y%m%d)/

# Bước 2: Xóa các file cũ
rm -f build-registry.py
rm -f scripts/search.py
rm -f registry.json
rm -f registry-index.json
rm -f registry.schema.json
rm -f domain-keywords.json

# Bước 3: Xóa thư mục scripts cũ nếu trống
rmdir scripts/ 2>/dev/null || true
```

**Giữ lại:**
- `docs/` — Toàn bộ tài liệu thiết kế (01-*.md đến 06-*.md)
- `commands/` — Sẽ được sử dụng lại ở Phase 3
- `mcp-server/` — Giữ nếu có, xem xét tích hợp sau

### Deliverable 0.2: Tạo cấu trúc thư mục mới

**Các bước thực hiện:**

```bash
cd $HOME/Agent_Hub/agent-hub-index

# Bước 1: Tạo cấu trúc library/
mkdir -p library/skills
mkdir -p library/agents
mkdir -p library/collections
mkdir -p library/stacks

# Bước 2: Tạo thư mục scripts mới
mkdir -p scripts

# Bước 3: Tạo thư mục hooks
mkdir -p hooks

# Bước 4: Tạo thư mục commands (nếu chưa có)
mkdir -p commands

# Bước 5: Tạo .gitkeep để giữ thư mục trống trong git
touch library/skills/.gitkeep
touch library/agents/.gitkeep
touch library/collections/.gitkeep
touch library/stacks/.gitkeep
touch hooks/.gitkeep
```

**Kiểm tra kết quả:**

```bash
# Verify: cấu trúc thư mục đúng
tree $HOME/Agent_Hub/agent-hub-index -L 3 --dirsfirst

# Expected output (đại khái):
# agent-hub-index/
# ├── commands/
# ├── docs/
# │   ├── 01-*.md
# │   └── ...
# ├── hooks/
# ├── library/
# │   ├── agents/
# │   ├── collections/
# │   ├── skills/
# │   └── stacks/
# └── scripts/

# Verify: các file cũ đã bị xóa
test ! -f build-registry.py && echo "OK: build-registry.py deleted"
test ! -f registry.json && echo "OK: registry.json deleted"
test ! -f registry-index.json && echo "OK: registry-index.json deleted"
test ! -f registry.schema.json && echo "OK: registry.schema.json deleted"
test ! -f domain-keywords.json && echo "OK: domain-keywords.json deleted"
test ! -f scripts/search.py && echo "OK: scripts/search.py deleted"

# Verify: docs vẫn còn
test -d docs && echo "OK: docs/ preserved"
```

### Exit Criteria cho Phase 0

- [ ] Không còn file nào trong danh sách xóa
- [ ] `docs/` vẫn còn nguyên vẹn
- [ ] Cấu trúc `library/{skills,agents,collections,stacks}` đã tồn tại
- [ ] Cấu trúc `scripts/`, `hooks/`, `commands/` đã tồn tại
- [ ] Backup đã được tạo tại `~/.agent_hub_backups/backup-*`

---

## Phase 1: Hạ Tầng Thư Viện (Library Infrastructure) — 2-4 giờ

### Mục tiêu
Xây dựng hệ thống import skills/agents từ các source projects vào library chuẩn hóa, và generate catalog.json tự động.

---

### Deliverable 1.1: Cấu trúc thư mục `library/`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/`

**Cấu trúc chi tiết sau khi import:**

```
library/
├── skills/
│   ├── brainstorming/
│   │   ├── SKILL.md              # Nội dung skill (copy từ source)
│   │   └── provenance.yaml       # Metadata về nguồn gốc
│   ├── systematic-debugging/
│   │   ├── SKILL.md
│   │   └── provenance.yaml
│   ├── test-driven-development/
│   │   ├── SKILL.md
│   │   └── provenance.yaml
│   └── ... (~35-40 skills)
├── agents/
│   ├── code-reviewer/
│   │   ├── AGENT.md
│   │   └── provenance.yaml
│   ├── gsd-planner/
│   │   ├── AGENT.md
│   │   └── provenance.yaml
│   └── ... (~10-15 agents)
├── collections/                   # Phase 2
├── stacks/                        # Phase 2
└── catalog.json                   # Auto-generated
```

**Input:** Không có (tạo cấu trúc trống)
**Output:** Thư mục sẵn sàng nhận import

**Đã hoàn thành ở Phase 0.** Không cần làm thêm.

---

### Deliverable 1.2: `scripts/import-skill.py`

**File path:** `$HOME/Agent_Hub/agent-hub-index/scripts/import-skill.py`

**Mục đích:** Import một skill hoặc agent từ source project vào `library/`. Tạo bản copy chuẩn hóa + provenance.yaml.

**Input:**
```
--source <source_name>    # superpowers | everything-claude-code | gstack | get-shit-done | learn-claude-code
--skill <skill_name>      # Tên skill/agent (slug)
--type <type>             # skill | agent (mặc định: tự detect)
--force                   # Ghi đè nếu đã tồn tại
--dry-run                 # Chỉ hiển thị, không copy
```

**Output:**
- `library/skills/{slug}/SKILL.md` hoặc `library/agents/{slug}/AGENT.md`
- `library/skills/{slug}/provenance.yaml` hoặc `library/agents/{slug}/provenance.yaml`
- Log ra stdout

**Các bước triển khai:**

1. **Định nghĩa SOURCE_MAP** — ánh xạ source name -> thư mục gốc + patterns:

```python
SOURCE_MAP = {
    "superpowers": {
        "root": Path("$HOME/Agent_Hub/superpowers"),
        "skill_patterns": ["skills/{name}/SKILL.md"],
        "agent_patterns": ["agents/{name}.md"],
    },
    "everything-claude-code": {
        "root": Path("$HOME/Agent_Hub/everything-claude-code"),
        "skill_patterns": [
            "skills/{name}/SKILL.md",
            "skills/*/{name}/SKILL.md",
        ],
        "agent_patterns": ["agents/{name}.md"],
    },
    "gstack": {
        "root": Path("$HOME/Agent_Hub/gstack"),
        "skill_patterns": ["{name}/SKILL.md"],
        "agent_patterns": [],
    },
    "get-shit-done": {
        "root": Path("$HOME/Agent_Hub/get-shit-done"),
        "skill_patterns": [],
        "agent_patterns": ["agents/{name}.md"],
    },
    "learn-claude-code": {
        "root": Path("$HOME/Agent_Hub/learn-claude-code"),
        "skill_patterns": ["skills/{name}/SKILL.md"],
        "agent_patterns": [],
    },
}
```

2. **Hàm `find_source_file(source, name, type_hint)`:**
   - Thử từng pattern trong `skill_patterns` và `agent_patterns`
   - Thay `{name}` bằng tên skill
   - Trả về `(absolute_path, detected_type)` hoặc raise error

3. **Hàm `import_entry(source_path, dest_dir, source_name, skill_name, entry_type)`:**
   - Tạo thư mục đích: `library/{type}s/{slug}/`
   - Copy file .md sang đích (đổi tên thành `SKILL.md` hoặc `AGENT.md`)
   - Generate `provenance.yaml` với:
     - `id`: slug
     - `source`: source_name
     - `source_path`: relative path trong source project
     - `imported_at`: ISO timestamp
     - `version`: đọc từ frontmatter nếu có, mặc định "1.0"
     - `type`: skill/agent
     - `original_id`: "{source}:{name}"

4. **Hàm `main()`:**
   - Parse arguments
   - Validate source name
   - Find source file
   - Check destination (--force logic)
   - Import
   - Print summary

**Test criteria:**

```bash
# Test 1: Import single skill
python3 $HOME/Agent_Hub/agent-hub-index/scripts/import-skill.py \
  --source superpowers --skill systematic-debugging

# Verify:
test -f $HOME/Agent_Hub/agent-hub-index/library/skills/systematic-debugging/SKILL.md \
  && echo "PASS: SKILL.md exists"
test -f $HOME/Agent_Hub/agent-hub-index/library/skills/systematic-debugging/provenance.yaml \
  && echo "PASS: provenance.yaml exists"

# Verify provenance content:
python3 -c "
import yaml
with open('$HOME/Agent_Hub/agent-hub-index/library/skills/systematic-debugging/provenance.yaml') as f:
    data = yaml.safe_load(f)
assert data['source'] == 'superpowers', f'Expected superpowers, got {data[\"source\"]}'
assert data['type'] == 'skill', f'Expected skill, got {data[\"type\"]}'
assert 'imported_at' in data, 'Missing imported_at'
print('PASS: provenance.yaml valid')
"

# Test 2: Import agent
python3 $HOME/Agent_Hub/agent-hub-index/scripts/import-skill.py \
  --source superpowers --skill code-reviewer --type agent
test -f $HOME/Agent_Hub/agent-hub-index/library/agents/code-reviewer/AGENT.md \
  && echo "PASS: AGENT.md exists"

# Test 3: Dry run
python3 $HOME/Agent_Hub/agent-hub-index/scripts/import-skill.py \
  --source gstack --skill investigate --dry-run
# Should print what would happen without copying

# Test 4: Duplicate prevention
python3 $HOME/Agent_Hub/agent-hub-index/scripts/import-skill.py \
  --source superpowers --skill systematic-debugging 2>&1 | grep -q "already exists" \
  && echo "PASS: duplicate detected"

# Test 5: Force overwrite
python3 $HOME/Agent_Hub/agent-hub-index/scripts/import-skill.py \
  --source superpowers --skill systematic-debugging --force \
  && echo "PASS: force overwrite"
```

**Dependencies:** Phase 0 hoàn thành (cấu trúc thư mục tồn tại)

---

### Deliverable 1.3: `scripts/build-catalog.py`

**File path:** `$HOME/Agent_Hub/agent-hub-index/scripts/build-catalog.py`

**Mục đích:** Scan toàn bộ `library/skills/` và `library/agents/`, đọc SKILL.md/AGENT.md + provenance.yaml, generate `library/catalog.json`.

**Input:** Không có arguments bắt buộc. Tùy chọn:
```
--library-dir <path>    # Mặc định: ../library (relative to script)
--output <path>         # Mặc định: ../library/catalog.json
--verbose               # In chi tiết
```

**Output:** `library/catalog.json` với schema:

```json
{
  "version": 2,
  "builtAt": "2026-03-30T12:00:00Z",
  "totalEntries": 50,
  "entries": [
    {
      "id": "systematic-debugging",
      "name": "Systematic Debugging",
      "type": "skill",
      "source": "superpowers",
      "description": "A structured approach to debugging...",
      "domains": ["debugging"],
      "technologies": [],
      "phases": ["debugging", "development"],
      "platforms": ["claude-code", "codex", "opencode", "cursor"],
      "cost": "medium",
      "stability": "stable",
      "path": "skills/systematic-debugging/SKILL.md",
      "importedAt": "2026-03-30T12:00:00Z",
      "keywords": ["debug", "root cause", "investigation", ...]
    }
  ],
  "collections": ["tdd-first", "debugging-deep-dive", ...],
  "stacks": ["ros2-robotics", "web-fullstack-typescript", ...]
}
```

**Các bước triển khai:**

1. **Scan thư mục:**
   - Duyệt `library/skills/*/SKILL.md`
   - Duyệt `library/agents/*/AGENT.md`
   - Đọc `provenance.yaml` đi kèm mỗi entry

2. **Parse mỗi entry:**
   - Đọc YAML frontmatter từ .md file (nếu có)
   - Đọc provenance.yaml
   - Extract: name, description (dòng đầu tiên non-empty sau heading)
   - Infer domains, technologies, phases từ nội dung (tái sử dụng logic từ build-registry.py cũ)

3. **Keyword extraction:**
   - Tích hợp DOMAIN_KEYWORDS, TECH_KEYWORDS, PHASE_KEYWORDS trực tiếp trong script (không dùng file JSON riêng)
   - Extract keywords từ nội dung body
   - Cap tại 50 keywords per entry

4. **Scan collections và stacks:**
   - Đọc `library/collections/*.yaml`
   - Đọc `library/stacks/*.yaml`
   - Thêm danh sách vào catalog

5. **Generate catalog.json:**
   - Sort entries theo id
   - Ghi ra file với indent=2

6. **Validation tích hợp:**
   - Kiểm tra mỗi entry có provenance.yaml
   - Kiểm tra không có id trùng lặp
   - Warning nếu entry thiếu description

**Test criteria:**

```bash
# Điều kiện tiên quyết: đã import ~50 entries (Deliverable 1.4)

# Test 1: Build catalog
python3 $HOME/Agent_Hub/agent-hub-index/scripts/build-catalog.py
test -f $HOME/Agent_Hub/agent-hub-index/library/catalog.json \
  && echo "PASS: catalog.json exists"

# Test 2: Validate JSON format
python3 -c "
import json
with open('$HOME/Agent_Hub/agent-hub-index/library/catalog.json') as f:
    data = json.load(f)
assert 'version' in data, 'Missing version'
assert 'entries' in data, 'Missing entries'
assert data['version'] == 2, f'Expected version 2, got {data[\"version\"]}'
print(f'PASS: {data[\"totalEntries\"]} entries loaded')
"

# Test 3: Verify entry count
python3 -c "
import json
with open('$HOME/Agent_Hub/agent-hub-index/library/catalog.json') as f:
    data = json.load(f)
count = len(data['entries'])
assert count >= 45, f'Expected >= 45 entries, got {count}'
print(f'PASS: {count} entries (target ~50)')
"

# Test 4: Verify required fields in every entry
python3 -c "
import json
REQUIRED = ['id', 'name', 'type', 'source', 'description', 'domains',
            'technologies', 'phases', 'platforms', 'cost', 'stability',
            'path', 'importedAt', 'keywords', 'use_with', 'conflicts_with', 'usage_pattern']
with open('$HOME/Agent_Hub/agent-hub-index/library/catalog.json') as f:
    data = json.load(f)
errors = []
for entry in data['entries']:
    for field in REQUIRED:
        if field not in entry:
            errors.append(f'{entry.get(\"id\", \"unknown\")}: missing {field}')
if errors:
    for e in errors:
        print(f'FAIL: {e}')
else:
    print(f'PASS: all {len(data[\"entries\"])} entries have required fields')
"

# Test 5: Verify no duplicate IDs
python3 -c "
import json
with open('$HOME/Agent_Hub/agent-hub-index/library/catalog.json') as f:
    data = json.load(f)
ids = [e['id'] for e in data['entries']]
dupes = [x for x in ids if ids.count(x) > 1]
assert not dupes, f'Duplicate IDs: {set(dupes)}'
print('PASS: no duplicate IDs')
"

# Test 6: Verify provenance for every entry
python3 -c "
import json, os
with open('$HOME/Agent_Hub/agent-hub-index/library/catalog.json') as f:
    data = json.load(f)
lib = '$HOME/Agent_Hub/agent-hub-index/library'
missing = []
for entry in data['entries']:
    prov_path = os.path.join(lib, os.path.dirname(entry['path']), 'provenance.yaml')
    if not os.path.exists(prov_path):
        missing.append(entry['id'])
if missing:
    print(f'FAIL: missing provenance for: {missing}')
else:
    print(f'PASS: all entries have provenance.yaml')
"
```

**Dependencies:** Deliverable 1.1, 1.2 (cần có library structure + imported entries)

---

### Deliverable 1.4: Import ~50 Curated Skills/Agents

**Mục đích:** Import bộ skill/agent tinh tuyển từ 5 source projects, đảm bảo chất lượng và đa dạng.

**Danh sách import cụ thể (50 entries):**

#### Từ `superpowers` (14 entries — tất cả skills + 1 agent):

| # | Tên | Loại | Lệnh import |
|---|-----|------|-------------|
| 1 | `brainstorming` | skill | `python3 scripts/import-skill.py --source superpowers --skill brainstorming` |
| 2 | `test-driven-development` | skill | `python3 scripts/import-skill.py --source superpowers --skill test-driven-development` |
| 3 | `requesting-code-review` | skill | `python3 scripts/import-skill.py --source superpowers --skill requesting-code-review` |
| 4 | `executing-plans` | skill | `python3 scripts/import-skill.py --source superpowers --skill executing-plans` |
| 5 | `subagent-driven-development` | skill | `python3 scripts/import-skill.py --source superpowers --skill subagent-driven-development` |
| 6 | `verification-before-completion` | skill | `python3 scripts/import-skill.py --source superpowers --skill verification-before-completion` |
| 7 | `finishing-a-development-branch` | skill | `python3 scripts/import-skill.py --source superpowers --skill finishing-a-development-branch` |
| 8 | `writing-skills` | skill | `python3 scripts/import-skill.py --source superpowers --skill writing-skills` |
| 9 | `writing-plans` | skill | `python3 scripts/import-skill.py --source superpowers --skill writing-plans` |
| 10 | `dispatching-parallel-agents` | skill | `python3 scripts/import-skill.py --source superpowers --skill dispatching-parallel-agents` |
| 11 | `using-git-worktrees` | skill | `python3 scripts/import-skill.py --source superpowers --skill using-git-worktrees` |
| 12 | `systematic-debugging` | skill | `python3 scripts/import-skill.py --source superpowers --skill systematic-debugging` |
| 13 | `using-superpowers` | skill | `python3 scripts/import-skill.py --source superpowers --skill using-superpowers` |
| 14 | `receiving-code-review` | skill | `python3 scripts/import-skill.py --source superpowers --skill receiving-code-review` |

#### Từ `everything-claude-code` (20 entries — skills tinh tuyển):

| # | Tên | Loại | Lệnh import |
|---|-----|------|-------------|
| 15 | `tdd-workflow` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill tdd-workflow` |
| 16 | `pytorch-patterns` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill pytorch-patterns` |
| 17 | `api-design` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill api-design` |
| 18 | `docker-patterns` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill docker-patterns` |
| 19 | `deployment-patterns` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill deployment-patterns` |
| 20 | `e2e-testing` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill e2e-testing` |
| 21 | `python-testing` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill python-testing` |
| 22 | `golang-patterns` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill golang-patterns` |
| 23 | `golang-testing` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill golang-testing` |
| 24 | `rust-patterns` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill rust-patterns` |
| 25 | `rust-testing` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill rust-testing` |
| 26 | `postgres-patterns` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill postgres-patterns` |
| 27 | `django-patterns` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill django-patterns` |
| 28 | `security-scan` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill security-scan` |
| 29 | `architecture-decision-records` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill architecture-decision-records` |
| 30 | `python-patterns` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill python-patterns` |
| 31 | `frontend-patterns` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill frontend-patterns` |
| 32 | `database-migrations` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill database-migrations` |
| 33 | `codebase-onboarding` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill codebase-onboarding` |
| 34 | `deep-research` | skill | `python3 scripts/import-skill.py --source everything-claude-code --skill deep-research` |

#### Từ `gstack` (6 entries — skills tinh tuyển):

| # | Tên | Loại | Lệnh import |
|---|-----|------|-------------|
| 35 | `investigate` | skill | `python3 scripts/import-skill.py --source gstack --skill investigate` |
| 36 | `qa` | skill | `python3 scripts/import-skill.py --source gstack --skill qa` |
| 37 | `review` | skill | `python3 scripts/import-skill.py --source gstack --skill review` |
| 38 | `ship` | skill | `python3 scripts/import-skill.py --source gstack --skill ship` |
| 39 | `canary` | skill | `python3 scripts/import-skill.py --source gstack --skill canary` |
| 40 | `guard` | skill | `python3 scripts/import-skill.py --source gstack --skill guard` |

#### Từ `get-shit-done` (7 entries — agents tinh tuyển):

| # | Tên | Loại | Lệnh import |
|---|-----|------|-------------|
| 41 | `gsd-planner` | agent | `python3 scripts/import-skill.py --source get-shit-done --skill gsd-planner --type agent` |
| 42 | `gsd-executor` | agent | `python3 scripts/import-skill.py --source get-shit-done --skill gsd-executor --type agent` |
| 43 | `gsd-debugger` | agent | `python3 scripts/import-skill.py --source get-shit-done --skill gsd-debugger --type agent` |
| 44 | `gsd-verifier` | agent | `python3 scripts/import-skill.py --source get-shit-done --skill gsd-verifier --type agent` |
| 45 | `gsd-roadmapper` | agent | `python3 scripts/import-skill.py --source get-shit-done --skill gsd-roadmapper --type agent` |
| 46 | `gsd-codebase-mapper` | agent | `python3 scripts/import-skill.py --source get-shit-done --skill gsd-codebase-mapper --type agent` |
| 47 | `gsd-plan-checker` | agent | `python3 scripts/import-skill.py --source get-shit-done --skill gsd-plan-checker --type agent` |

#### Từ `learn-claude-code` (3 entries):

| # | Tên | Loại | Lệnh import |
|---|-----|------|-------------|
| 48 | `agent-builder` | skill | `python3 scripts/import-skill.py --source learn-claude-code --skill agent-builder` |
| 49 | `code-review` | skill | `python3 scripts/import-skill.py --source learn-claude-code --skill code-review` |
| 50 | `mcp-builder` | skill | `python3 scripts/import-skill.py --source learn-claude-code --skill mcp-builder` |

**Script batch import:**

```bash
#!/bin/bash
# File: scripts/batch-import.sh (tạm thời, dùng 1 lần)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMPORT="python3 ${SCRIPT_DIR}/import-skill.py"

echo "=== Importing from superpowers ==="
for skill in brainstorming test-driven-development requesting-code-review \
  executing-plans subagent-driven-development verification-before-completion \
  finishing-a-development-branch writing-skills writing-plans \
  dispatching-parallel-agents using-git-worktrees systematic-debugging \
  using-superpowers receiving-code-review; do
  $IMPORT --source superpowers --skill "$skill" --force
done

echo "=== Importing from everything-claude-code ==="
for skill in tdd-workflow pytorch-patterns api-design docker-patterns \
  deployment-patterns e2e-testing python-testing golang-patterns \
  golang-testing rust-patterns rust-testing postgres-patterns \
  django-patterns security-scan architecture-decision-records \
  python-patterns frontend-patterns database-migrations \
  codebase-onboarding deep-research; do
  $IMPORT --source everything-claude-code --skill "$skill" --force
done

echo "=== Importing from gstack ==="
for skill in investigate qa review ship canary guard; do
  $IMPORT --source gstack --skill "$skill" --force
done

echo "=== Importing from get-shit-done ==="
for agent in gsd-planner gsd-executor gsd-debugger gsd-verifier \
  gsd-roadmapper gsd-codebase-mapper gsd-plan-checker; do
  $IMPORT --source get-shit-done --skill "$agent" --type agent --force
done

echo "=== Importing from learn-claude-code ==="
for skill in agent-builder code-review mcp-builder; do
  $IMPORT --source learn-claude-code --skill "$skill" --force
done

echo ""
echo "=== Import complete ==="
echo "Skills: $(ls -d ${SCRIPT_DIR}/../library/skills/*/ 2>/dev/null | wc -l)"
echo "Agents: $(ls -d ${SCRIPT_DIR}/../library/agents/*/ 2>/dev/null | wc -l)"
```

**Các bước thực hiện:**

1. Tạo `scripts/batch-import.sh` với nội dung trên
2. `chmod +x scripts/batch-import.sh`
3. Chạy `./scripts/batch-import.sh`
4. Kiểm tra output: mong đợi ~43 skills + ~7 agents

**Test criteria:**

```bash
# Đếm entries
SKILL_COUNT=$(ls -d $HOME/Agent_Hub/agent-hub-index/library/skills/*/ 2>/dev/null | wc -l)
AGENT_COUNT=$(ls -d $HOME/Agent_Hub/agent-hub-index/library/agents/*/ 2>/dev/null | wc -l)
TOTAL=$((SKILL_COUNT + AGENT_COUNT))

echo "Skills: $SKILL_COUNT"  # Expected: ~43
echo "Agents: $AGENT_COUNT"  # Expected: ~7
echo "Total:  $TOTAL"        # Expected: ~50

# Verify mỗi entry có provenance.yaml
MISSING=0
for dir in $HOME/Agent_Hub/agent-hub-index/library/skills/*/; do
  test -f "$dir/provenance.yaml" || { echo "MISSING: $dir/provenance.yaml"; MISSING=$((MISSING+1)); }
done
for dir in $HOME/Agent_Hub/agent-hub-index/library/agents/*/; do
  test -f "$dir/provenance.yaml" || { echo "MISSING: $dir/provenance.yaml"; MISSING=$((MISSING+1)); }
done
echo "Missing provenance: $MISSING"  # Expected: 0
```

**Dependencies:** Deliverable 1.2 (import-skill.py phải hoạt động)

---

### Deliverable 1.5: `library/catalog.json` Generated

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/catalog.json`

**Đây là output của Deliverable 1.3.** Chạy:

```bash
python3 $HOME/Agent_Hub/agent-hub-index/scripts/build-catalog.py
```

**Test criteria:** Xem Deliverable 1.3 test criteria.

**Dependencies:** Deliverable 1.3 + 1.4

---

### Exit Criteria cho Phase 1

- [ ] `python3 scripts/import-skill.py --source superpowers --skill systematic-debugging` chạy thành công (hoặc báo "already exists")
- [ ] `python3 scripts/build-catalog.py` generate `library/catalog.json` hợp lệ
- [ ] `catalog.json` có >= 45 entries (target ~50) với đầy đủ required fields
- [ ] Mỗi entry trong library có `provenance.yaml` đi kèm
- [ ] Không có duplicate IDs trong catalog
- [ ] Mỗi entry có ít nhất: id, name, type, source, description, path

---

## Phase 2: Collections & Stacks — 2-3 giờ

### Mục tiêu
Tạo 4 seed collections (workflow-based bundles) và 4 seed stacks (tech-based bundles), cùng script validate để đảm bảo tính nhất quán.

---

### Deliverable 2.1: Seed Collections (4 files YAML)

Collections nhóm skills/agents theo **workflow methodology** — không phụ thuộc tech stack cụ thể.

---

#### Collection 2.1.1: `tdd-first.yaml`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/collections/tdd-first.yaml`

**Triết lý:** Test-Driven Development từ đầu đến cuối. Viết test trước, implement sau, verify liên tục.

**Nội dung đầy đủ:**

```yaml
# tdd-first.yaml — TDD-First Development Collection
name: "TDD-First Development"
id: "tdd-first"
description: >
  Bộ skills cho quy trình phát triển Test-Driven Development.
  Bắt đầu bằng brainstorming để hiểu yêu cầu, viết test trước khi code,
  review liên tục, và verify trước khi ship.
tags:
  - tdd
  - testing
  - quality
  - workflow
applicable_phases:
  - planning
  - development
  - testing
  - review

entries:
  - seq: 1
    id: "brainstorming"
    role: "Hiểu yêu cầu và thiết kế test cases trước khi code"
    when: "Bắt đầu feature mới hoặc thay đổi lớn"
    required: true

  - seq: 2
    id: "writing-plans"
    role: "Viết kế hoạch implementation với test-first approach"
    when: "Sau brainstorming, trước khi bắt đầu code"
    required: true

  - seq: 3
    id: "test-driven-development"
    role: "Core TDD workflow: Red → Green → Refactor"
    when: "Trong suốt quá trình development"
    required: true

  - seq: 4
    id: "tdd-workflow"
    role: "Chi tiết TDD patterns và best practices"
    when: "Bổ sung cho TDD skill chính"
    required: false

  - seq: 5
    id: "executing-plans"
    role: "Thực thi kế hoạch đã viết theo TDD"
    when: "Khi bắt đầu implement từng task"
    required: true

  - seq: 6
    id: "requesting-code-review"
    role: "Yêu cầu review khi đã pass tất cả tests"
    when: "Sau khi hoàn thành implementation"
    required: true

  - seq: 7
    id: "verification-before-completion"
    role: "Kiểm tra cuối cùng trước khi merge"
    when: "Trước khi đánh dấu task là done"
    required: true

  - seq: 8
    id: "finishing-a-development-branch"
    role: "Clean up branch, squash commits, prepare for merge"
    when: "Khi branch đã pass review"
    required: false
```

**Giải thích sequencing:**
1. `brainstorming` (seq 1) — Luôn bắt đầu bằng hiểu yêu cầu
2. `writing-plans` (seq 2) — Lập kế hoạch test cases + implementation
3. `test-driven-development` (seq 3) — Core workflow TDD
4. `tdd-workflow` (seq 4) — Chi tiết patterns, bổ sung cho seq 3
5. `executing-plans` (seq 5) — Thực thi kế hoạch
6. `requesting-code-review` (seq 6) — Review khi tests pass
7. `verification-before-completion` (seq 7) — Verify cuối cùng
8. `finishing-a-development-branch` (seq 8) — Clean up

---

#### Collection 2.1.2: `debugging-deep-dive.yaml`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/collections/debugging-deep-dive.yaml`

**Triết lý:** Debugging có hệ thống, từ phát hiện đến root cause analysis đến fix và verify.

**Nội dung đầy đủ:**

```yaml
# debugging-deep-dive.yaml — Deep Debugging Collection
name: "Debugging Deep Dive"
id: "debugging-deep-dive"
description: >
  Bộ skills cho quy trình debugging có hệ thống.
  Từ investigation ban đầu, qua root cause analysis,
  đến fix và verification. Phù hợp cho bugs phức tạp
  cần phân tích sâu.
tags:
  - debugging
  - investigation
  - root-cause
  - troubleshooting
applicable_phases:
  - debugging
  - testing
  - review

entries:
  - seq: 1
    id: "systematic-debugging"
    role: "Framework debugging có hệ thống: reproduce → isolate → fix → verify"
    when: "Khi gặp bug cần debug"
    required: true

  - seq: 2
    id: "investigate"
    role: "Investigation sâu: đọc logs, trace execution, tìm pattern"
    when: "Khi cần investigate root cause"
    required: true

  - seq: 3
    id: "gsd-debugger"
    role: "Agent debugging tự động: tạo hypotheses và test chúng"
    when: "Khi bug phức tạp cần agent hỗ trợ"
    required: false

  - seq: 4
    id: "gsd-codebase-mapper"
    role: "Map codebase để hiểu context xung quanh bug"
    when: "Khi bug liên quan đến nhiều files/modules"
    required: false

  - seq: 5
    id: "verification-before-completion"
    role: "Verify fix không gây regression"
    when: "Sau khi đã fix bug"
    required: true

  - seq: 6
    id: "requesting-code-review"
    role: "Review fix để đảm bảo chất lượng"
    when: "Trước khi merge fix"
    required: false
```

**Giải thích sequencing:**
1. `systematic-debugging` (seq 1) — Framework chính, luôn dùng
2. `investigate` (seq 2) — Deep dive vào code/logs
3. `gsd-debugger` (seq 3) — Agent hỗ trợ tự động (tùy chọn)
4. `gsd-codebase-mapper` (seq 4) — Hiểu context codebase
5. `verification-before-completion` (seq 5) — Verify fix
6. `requesting-code-review` (seq 6) — Review trước merge

---

#### Collection 2.1.3: `plan-driven-development.yaml`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/collections/plan-driven-development.yaml`

**Triết lý:** Lập kế hoạch cẩn thận trước khi code. Brainstorm → Plan → Execute → Review. Phù hợp cho features lớn.

**Nội dung đầy đủ:**

```yaml
# plan-driven-development.yaml — Plan-Driven Development Collection
name: "Plan-Driven Development"
id: "plan-driven-development"
description: >
  Bộ skills cho phát triển dựa trên kế hoạch.
  Phù hợp cho features lớn, refactoring quy mô lớn,
  hoặc khi cần sự phối hợp giữa nhiều components.
  Brainstorm kỹ, lập kế hoạch chi tiết, thực thi có hệ thống.
tags:
  - planning
  - architecture
  - development
  - workflow
applicable_phases:
  - planning
  - architecture
  - development
  - review

entries:
  - seq: 1
    id: "brainstorming"
    role: "Explore yêu cầu, constraints, và design options"
    when: "Bắt đầu bất kỳ feature lớn nào"
    required: true

  - seq: 2
    id: "architecture-decision-records"
    role: "Ghi lại các quyết định kiến trúc quan trọng"
    when: "Khi có quyết định thiết kế ảnh hưởng lớn"
    required: false

  - seq: 3
    id: "writing-plans"
    role: "Viết kế hoạch triển khai chi tiết"
    when: "Sau brainstorming, trước khi code"
    required: true

  - seq: 4
    id: "gsd-planner"
    role: "Agent lập kế hoạch tự động: chia nhỏ tasks"
    when: "Khi cần agent hỗ trợ planning"
    required: false

  - seq: 5
    id: "executing-plans"
    role: "Thực thi từng task trong kế hoạch"
    when: "Trong quá trình development"
    required: true

  - seq: 6
    id: "subagent-driven-development"
    role: "Dispatch parallel agents cho tasks độc lập"
    when: "Khi có nhiều tasks có thể song song"
    required: false

  - seq: 7
    id: "requesting-code-review"
    role: "Review toàn bộ implementation"
    when: "Sau khi hoàn thành tất cả tasks"
    required: true

  - seq: 8
    id: "verification-before-completion"
    role: "Verify everything works end-to-end"
    when: "Trước khi ship"
    required: true
```

**Giải thích sequencing:**
1. `brainstorming` (seq 1) — Explore requirements
2. `architecture-decision-records` (seq 2) — Document decisions
3. `writing-plans` (seq 3) — Kế hoạch chi tiết
4. `gsd-planner` (seq 4) — Agent hỗ trợ planning
5. `executing-plans` (seq 5) — Thực thi
6. `subagent-driven-development` (seq 6) — Parallel execution
7. `requesting-code-review` (seq 7) — Review
8. `verification-before-completion` (seq 8) — Final verify

---

#### Collection 2.1.4: `devops-ship-cycle.yaml`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/collections/devops-ship-cycle.yaml`

**Triết lý:** Từ code xong đến ship production. Review, test, deploy, monitor.

**Nội dung đầy đủ:**

```yaml
# devops-ship-cycle.yaml — DevOps Ship Cycle Collection
name: "DevOps Ship Cycle"
id: "devops-ship-cycle"
description: >
  Bộ skills cho quy trình ship code ra production.
  Từ review cuối cùng, qua QA, deploy, canary testing,
  đến monitoring. Đảm bảo code được ship an toàn và đáng tin cậy.
tags:
  - devops
  - deployment
  - shipping
  - quality
  - monitoring
applicable_phases:
  - review
  - testing
  - deployment
  - monitoring

entries:
  - seq: 1
    id: "requesting-code-review"
    role: "Review cuối cùng trước khi ship"
    when: "Code đã xong, cần review lần cuối"
    required: true

  - seq: 2
    id: "security-scan"
    role: "Scan security vulnerabilities trước khi deploy"
    when: "Trước mỗi lần deploy"
    required: true

  - seq: 3
    id: "qa"
    role: "QA testing: functional, regression, edge cases"
    when: "Sau review, trước deploy"
    required: true

  - seq: 4
    id: "docker-patterns"
    role: "Containerization best practices"
    when: "Khi build/update Docker images"
    required: false

  - seq: 5
    id: "deployment-patterns"
    role: "Deployment strategies: blue-green, rolling, canary"
    when: "Khi chọn deployment strategy"
    required: false

  - seq: 6
    id: "ship"
    role: "Ship code ra production"
    when: "Khi đã pass QA"
    required: true

  - seq: 7
    id: "canary"
    role: "Canary deployment: monitor subset users trước rollout"
    when: "Sau deploy, trước full rollout"
    required: false

  - seq: 8
    id: "guard"
    role: "Production guard: monitor health, rollback nếu cần"
    when: "Sau deploy, monitoring liên tục"
    required: false
```

**Giải thích sequencing:**
1. `requesting-code-review` (seq 1) — Review trước ship
2. `security-scan` (seq 2) — Security check
3. `qa` (seq 3) — QA testing
4. `docker-patterns` (seq 4) — Container prep (tùy chọn)
5. `deployment-patterns` (seq 5) — Strategy selection (tùy chọn)
6. `ship` (seq 6) — Deploy to production
7. `canary` (seq 7) — Canary testing
8. `guard` (seq 8) — Production monitoring

---

### Deliverable 2.2: Seed Stacks (4 files YAML)

Stacks nhóm skills/agents theo **tech stack** — phù hợp cho dự án cụ thể.

---

#### Stack 2.2.1: `ros2-robotics.yaml`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/stacks/ros2-robotics.yaml`

**Mục đích:** Stack cho dự án ROS2 robotics (sensor processing, navigation, SLAM).

**Nội dung đầy đủ:**

```yaml
# ros2-robotics.yaml — ROS2 Robotics Stack
name: "ROS2 Robotics"
id: "ros2-robotics"
description: >
  Stack đầy đủ cho phát triển robot dùng ROS2.
  Bao gồm skills cho debugging sensor data, planning navigation,
  testing ROS2 nodes, và deployment trên robot hardware.
tags:
  - ros2
  - robotics
  - cpp
  - python
  - sensor
  - navigation
domains:
  - robotics
  - debugging
  - testing
technologies:
  - ros2
  - cpp
  - python
  - docker

core_skills:
  - id: "systematic-debugging"
    role: "Debug ROS2 nodes, sensor pipelines, timing issues"
    priority: critical

  - id: "investigate"
    role: "Investigate rosbag data, tf trees, node connections"
    priority: critical

  - id: "brainstorming"
    role: "Design ROS2 node architecture, message types, service interfaces"
    priority: high

  - id: "writing-plans"
    role: "Plan multi-node systems, launch files, parameter configs"
    priority: high

  - id: "test-driven-development"
    role: "TDD cho ROS2 nodes: unit tests với gtest/pytest"
    priority: high

  - id: "docker-patterns"
    role: "Docker cho ROS2: multi-stage builds, rosdep, colcon workspace"
    priority: medium

workflow_skills:
  - id: "executing-plans"
    role: "Execute plan theo từng node/package"
    phase: development

  - id: "verification-before-completion"
    role: "Verify integration giữa các nodes"
    phase: testing

  - id: "gsd-codebase-mapper"
    role: "Map ROS2 workspace: packages, dependencies, launch graph"
    phase: planning

  - id: "requesting-code-review"
    role: "Review trước merge vào main branch"
    phase: review

  - id: "finishing-a-development-branch"
    role: "Clean up feature branch"
    phase: deployment
```

---

#### Stack 2.2.2: `web-fullstack-typescript.yaml`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/stacks/web-fullstack-typescript.yaml`

**Mục đích:** Stack cho dự án web fullstack TypeScript (React/Next.js + Node.js + Postgres).

**Nội dung đầy đủ:**

```yaml
# web-fullstack-typescript.yaml — Web Fullstack TypeScript Stack
name: "Web Fullstack TypeScript"
id: "web-fullstack-typescript"
description: >
  Stack cho phát triển web fullstack với TypeScript.
  Frontend React/Next.js, backend Node.js, database Postgres.
  Bao gồm skills cho API design, testing, deployment, và security.
tags:
  - typescript
  - react
  - nextjs
  - nodejs
  - postgres
  - fullstack
domains:
  - web-frontend
  - web-backend
  - data
  - testing
  - devops
technologies:
  - typescript
  - react
  - postgres
  - docker

core_skills:
  - id: "frontend-patterns"
    role: "React/Next.js patterns: components, hooks, state management"
    priority: critical

  - id: "api-design"
    role: "REST/GraphQL API design: endpoints, validation, error handling"
    priority: critical

  - id: "postgres-patterns"
    role: "Postgres: schema design, queries, indexing, migrations"
    priority: critical

  - id: "tdd-workflow"
    role: "TDD cho TypeScript: Jest, Vitest, React Testing Library"
    priority: high

  - id: "e2e-testing"
    role: "E2E testing: Playwright/Cypress cho fullstack flows"
    priority: high

  - id: "security-scan"
    role: "Security: XSS, CSRF, SQL injection, auth flows"
    priority: high

  - id: "database-migrations"
    role: "Database migrations: Prisma, Drizzle, raw SQL"
    priority: medium

workflow_skills:
  - id: "brainstorming"
    role: "Design UI components, API contracts, database schema"
    phase: planning

  - id: "writing-plans"
    role: "Plan feature implementation across frontend + backend"
    phase: planning

  - id: "executing-plans"
    role: "Execute feature tasks"
    phase: development

  - id: "docker-patterns"
    role: "Dockerize frontend + backend + database"
    phase: deployment

  - id: "deployment-patterns"
    role: "Deploy: Vercel, Docker, CI/CD pipelines"
    phase: deployment

  - id: "codebase-onboarding"
    role: "Onboard developer mới vào fullstack codebase"
    phase: documentation

  - id: "requesting-code-review"
    role: "Review PRs"
    phase: review
```

---

#### Stack 2.2.3: `ml-research-pytorch.yaml`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/stacks/ml-research-pytorch.yaml`

**Mục đích:** Stack cho nghiên cứu ML/AI với PyTorch.

**Nội dung đầy đủ:**

```yaml
# ml-research-pytorch.yaml — ML Research PyTorch Stack
name: "ML Research PyTorch"
id: "ml-research-pytorch"
description: >
  Stack cho nghiên cứu Machine Learning với PyTorch.
  Từ experiment design, model implementation, training pipeline,
  đến evaluation và paper writing. Tối ưu cho research workflow.
tags:
  - pytorch
  - machine-learning
  - research
  - python
  - experiment
  - training
domains:
  - ai-ml
  - research
  - data
  - testing
technologies:
  - pytorch
  - python
  - docker

core_skills:
  - id: "pytorch-patterns"
    role: "PyTorch patterns: models, dataloaders, training loops, distributed"
    priority: critical

  - id: "python-patterns"
    role: "Python best practices: typing, packaging, virtual envs"
    priority: critical

  - id: "python-testing"
    role: "Testing ML code: pytest, fixtures, reproducibility"
    priority: high

  - id: "deep-research"
    role: "Research workflow: literature review, experiment design, analysis"
    priority: high

  - id: "systematic-debugging"
    role: "Debug training issues: loss NaN, gradient explosion, data bugs"
    priority: high

  - id: "docker-patterns"
    role: "Docker cho ML: CUDA, multi-stage, reproducible environments"
    priority: medium

workflow_skills:
  - id: "brainstorming"
    role: "Brainstorm experiment hypotheses, model architectures"
    phase: planning

  - id: "writing-plans"
    role: "Plan experiment pipeline: data → train → eval → report"
    phase: planning

  - id: "executing-plans"
    role: "Execute experiments theo plan"
    phase: development

  - id: "verification-before-completion"
    role: "Verify results: reproducibility, statistical significance"
    phase: testing

  - id: "codebase-onboarding"
    role: "Onboard collaborators vào research codebase"
    phase: documentation
```

---

#### Stack 2.2.4: `api-service-go.yaml`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/stacks/api-service-go.yaml`

**Mục đích:** Stack cho API service viết bằng Go.

**Nội dung đầy đủ:**

```yaml
# api-service-go.yaml — API Service Go Stack
name: "API Service Go"
id: "api-service-go"
description: >
  Stack cho phát triển API service bằng Go.
  Bao gồm skills cho Go patterns, testing, API design,
  database, Docker deployment, và security.
  Phù hợp cho microservices và production APIs.
tags:
  - go
  - api
  - microservice
  - backend
  - docker
  - postgres
domains:
  - web-backend
  - data
  - testing
  - devops
  - security
technologies:
  - go
  - postgres
  - docker

core_skills:
  - id: "golang-patterns"
    role: "Go patterns: interfaces, error handling, concurrency, project structure"
    priority: critical

  - id: "golang-testing"
    role: "Go testing: table tests, mocks, integration tests, benchmarks"
    priority: critical

  - id: "api-design"
    role: "API design: REST endpoints, middleware, validation, versioning"
    priority: critical

  - id: "postgres-patterns"
    role: "Postgres: schema, queries, connection pooling, migrations"
    priority: high

  - id: "security-scan"
    role: "Security: input validation, auth, secrets management"
    priority: high

  - id: "docker-patterns"
    role: "Docker: multi-stage builds, minimal images, health checks"
    priority: high

workflow_skills:
  - id: "brainstorming"
    role: "Design API contracts, service boundaries"
    phase: planning

  - id: "writing-plans"
    role: "Plan service implementation"
    phase: planning

  - id: "architecture-decision-records"
    role: "Document architecture decisions (database choice, auth strategy)"
    phase: architecture

  - id: "executing-plans"
    role: "Implement endpoints, handlers, middleware"
    phase: development

  - id: "deployment-patterns"
    role: "Deploy: Docker, Kubernetes, CI/CD"
    phase: deployment

  - id: "ship"
    role: "Ship to production"
    phase: deployment

  - id: "canary"
    role: "Canary deployment"
    phase: monitoring

  - id: "guard"
    role: "Production monitoring"
    phase: monitoring
```

---

### Deliverable 2.3: `scripts/validate.py`

**File path:** `$HOME/Agent_Hub/agent-hub-index/scripts/validate.py`

**Mục đích:** Validate tất cả YAML files trong collections/ và stacks/, kiểm tra rằng mọi skill/agent ID được tham chiếu đều tồn tại trong library.

**Input:**
```
--library-dir <path>    # Mặc định: ../library
--verbose               # In chi tiết
--fix                   # Tự động fix những gì có thể
```

**Output:** Exit code 0 nếu không có lỗi. In danh sách lỗi nếu có.

**Các bước triển khai:**

1. **Scan library để lấy danh sách IDs hợp lệ:**
   - Duyệt `library/skills/*/` → mỗi thư mục = 1 skill ID
   - Duyệt `library/agents/*/` → mỗi thư mục = 1 agent ID
   - Kết quả: `valid_ids: set[str]`

2. **Validate collections:**
   - Đọc mỗi file `library/collections/*.yaml`
   - Kiểm tra YAML hợp lệ
   - Kiểm tra có required fields: `name`, `id`, `description`, `entries`
   - Kiểm tra mỗi entry có: `seq`, `id`, `role`
   - Kiểm tra `seq` là unique và liên tục (1, 2, 3, ...)
   - Kiểm tra mỗi `entry.id` tồn tại trong `valid_ids`
   - Kiểm tra số entries: >= 4 và <= 12

3. **Validate stacks:**
   - Đọc mỗi file `library/stacks/*.yaml`
   - Kiểm tra YAML hợp lệ
   - Kiểm tra có required fields: `name`, `id`, `description`, `core_skills`, `workflow_skills`
   - Kiểm tra mỗi skill trong `core_skills` có: `id`, `role`, `priority`
   - Kiểm tra mỗi skill trong `workflow_skills` có: `id`, `role`, `phase`
   - Kiểm tra `priority` thuộc `{critical, high, medium, low}`
   - Kiểm tra mỗi skill ID tồn tại trong `valid_ids`
   - Kiểm tra `core_skills` có ít nhất 3 entries
   - Kiểm tra `workflow_skills` có ít nhất 2 entries

4. **Validate catalog.json (nếu tồn tại):**
   - Kiểm tra mỗi entry trong catalog có thư mục tương ứng trong library
   - Kiểm tra không có thư mục trong library thiếu entry trong catalog (orphans)

5. **Report:**
   - In tổng kết: X errors, Y warnings
   - Exit code 0 nếu 0 errors
   - Exit code 1 nếu có errors

**Test criteria:**

```bash
# Test 1: Validate passes (no errors)
python3 $HOME/Agent_Hub/agent-hub-index/scripts/validate.py
echo "Exit code: $?"  # Expected: 0

# Test 2: Verbose output
python3 $HOME/Agent_Hub/agent-hub-index/scripts/validate.py --verbose
# Expected: danh sách tất cả files được check, từng ID được validate

# Test 3: Tạo file lỗi tạm để test error detection
cat > /tmp/test-bad-collection.yaml << 'EOF'
name: "Bad Collection"
id: "bad"
description: "Test"
entries:
  - seq: 1
    id: "nonexistent-skill-xyz"
    role: "Test"
EOF
cp /tmp/test-bad-collection.yaml \
  $HOME/Agent_Hub/agent-hub-index/library/collections/bad-test.yaml

python3 $HOME/Agent_Hub/agent-hub-index/scripts/validate.py 2>&1 \
  | grep -q "nonexistent-skill-xyz" && echo "PASS: detected invalid reference"

# Cleanup
rm $HOME/Agent_Hub/agent-hub-index/library/collections/bad-test.yaml

# Test 4: Verify collection entry counts
python3 -c "
import yaml, glob
for f in sorted(glob.glob('$HOME/Agent_Hub/agent-hub-index/library/collections/*.yaml')):
    with open(f) as fh:
        data = yaml.safe_load(fh)
    count = len(data.get('entries', []))
    status = 'PASS' if 4 <= count <= 12 else 'FAIL'
    print(f'{status}: {data[\"id\"]} has {count} entries')
"

# Test 5: Verify stack sections
python3 -c "
import yaml, glob
for f in sorted(glob.glob('$HOME/Agent_Hub/agent-hub-index/library/stacks/*.yaml')):
    with open(f) as fh:
        data = yaml.safe_load(fh)
    core = len(data.get('core_skills', []))
    wf = len(data.get('workflow_skills', []))
    ok = core >= 3 and wf >= 2
    status = 'PASS' if ok else 'FAIL'
    print(f'{status}: {data[\"id\"]} — core: {core}, workflow: {wf}')
"
```

**Dependencies:** Deliverable 1.4 (library phải có entries), 2.1, 2.2 (collections + stacks phải tồn tại)

---

### Exit Criteria cho Phase 2

- [ ] `python3 scripts/validate.py` exit code 0 (0 errors)
- [ ] 4 collection files tồn tại trong `library/collections/`
- [ ] 4 stack files tồn tại trong `library/stacks/`
- [ ] Mỗi collection có 4-8 entries với sequence numbers liên tục
- [ ] Mỗi stack có `core_skills` (>= 3) + `workflow_skills` (>= 2) sections
- [ ] Tất cả skill/agent IDs trong collections/stacks đều tồn tại trong `library/`
- [ ] `python3 scripts/build-catalog.py` sau khi thêm collections/stacks vẫn pass

---

## Phase 3: The Librarian — 3-5 giờ

### Mục tiêu
Xây dựng AI Librarian agent — "thủ thư" cho thư viện skills. Librarian có thể recommend skills, phát hiện project context, và publish skills vào project.

---

### Deliverable 3.1: `library/agents/librarian.md`

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/agents/librarian.md`

**Mục đích:** Định nghĩa đầy đủ Librarian agent. Đây là file .md chứa system prompt + instructions cho AI agent.

**Nội dung cần bao gồm:**

1. **Frontmatter YAML:**
```yaml
---
name: "Librarian"
description: "AI Librarian cho Agent Hub — recommend, publish, và quản lý skills/agents library"
model: "claude-sonnet-4-20250514"
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---
```

2. **Identity section:**
   - Vai trò: Thủ thư chuyên nghiệp cho Agent Hub skills library
   - Nhiệm vụ chính: (a) Recommend skills phù hợp, (b) Publish skills vào project, (c) Quản lý library

3. **Catalog knowledge:**
   - Đọc `library/catalog.json` khi khởi động
   - Hiểu cấu trúc: entries, collections, stacks
   - Biết đường dẫn gốc: `$HOME/Agent_Hub/agent-hub-index/library/`

4. **Recommendation engine instructions:**
   - Phân tích project context: đọc package.json, Cargo.toml, go.mod, pyproject.toml, CMakeLists.txt, etc.
   - Match technologies → stacks → core_skills
   - Match workflow phase → collections → relevant skills
   - Trả về danh sách ranked với explanation

5. **Publish workflow instructions:**
   - Target: Copy skills vào `.claude/skills/` hoặc `.opencode/skills/` của project
   - Tạo manifest file để track skills đã publish
   - Yêu cầu user confirm trước khi publish
   - Command: `python3 scripts/publish-to-project.py --project <path> --skills <id1,id2,...>`

6. **Proactive mode instructions:**
   - Khi detect new project (không có skills installed):
     - Analyze project files
     - Suggest matching stack
     - Offer to publish

**Các bước triển khai:**

1. Tạo file `$HOME/Agent_Hub/agent-hub-index/library/agents/librarian.md`
2. Viết frontmatter
3. Viết identity + role description
4. Viết recommendation algorithm (bằng natural language instructions)
5. Viết publish workflow
6. Viết proactive mode instructions
7. Viết response format examples

**Test criteria:**

```bash
# Test 1: File tồn tại và có frontmatter
test -f $HOME/Agent_Hub/agent-hub-index/library/agents/librarian.md \
  && echo "PASS: librarian.md exists"

# Test 2: Frontmatter hợp lệ
python3 -c "
import yaml, re
with open('$HOME/Agent_Hub/agent-hub-index/library/agents/librarian.md') as f:
    content = f.read()
m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
assert m, 'No frontmatter found'
fm = yaml.safe_load(m.group(1))
assert fm.get('name') == 'Librarian', f'Expected Librarian, got {fm.get(\"name\")}'
print('PASS: frontmatter valid')
"

# Test 3: Nội dung đầy đủ (kiểm tra keywords)
python3 -c "
with open('$HOME/Agent_Hub/agent-hub-index/library/agents/librarian.md') as f:
    content = f.read()
required_keywords = ['catalog.json', 'recommend', 'publish', 'proactive', 'collection', 'stack']
missing = [kw for kw in required_keywords if kw not in content.lower()]
assert not missing, f'Missing keywords: {missing}'
print('PASS: all required sections present')
"
```

**Dependencies:** Phase 1 (catalog.json), Phase 2 (collections + stacks)

---

### Deliverable 3.2: `commands/librarian.md`

**File path:** `$HOME/Agent_Hub/agent-hub-index/commands/librarian.md`

**Mục đích:** Slash command `/librarian` cho Claude Code. Khi user gõ `/librarian`, load Librarian agent.

**Nội dung cần bao gồm:**

1. **Frontmatter:**
```yaml
---
name: librarian
description: "Mở AI Librarian — recommend và publish skills cho project"
argument-hint: "[recommend | publish | browse | search <query>]"
---
```

2. **Command body:**
   - Load catalog.json
   - Detect project context (cwd)
   - Theo subcommand:
     - `recommend` — Phân tích project và recommend skills
     - `publish <skills>` — Publish skills vào project
     - `browse` — Browse library interactively
     - `search <query>` — Tìm kiếm trong catalog
     - Không có argument — Hiển thị menu

**Các bước triển khai:**

1. Tạo file `commands/librarian.md`
2. Viết frontmatter với argument-hint
3. Viết logic dispatch dựa trên argument
4. Viết mỗi sub-workflow chi tiết
5. Include đường dẫn tuyệt đối đến catalog.json và scripts

**Test criteria:**

```bash
# Test 1: File tồn tại
test -f $HOME/Agent_Hub/agent-hub-index/commands/librarian.md \
  && echo "PASS: commands/librarian.md exists"

# Test 2: Frontmatter hợp lệ
python3 -c "
import yaml, re
with open('$HOME/Agent_Hub/agent-hub-index/commands/librarian.md') as f:
    content = f.read()
m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
assert m, 'No frontmatter found'
fm = yaml.safe_load(m.group(1))
assert fm.get('name') == 'librarian', f'Expected librarian, got {fm.get(\"name\")}'
print('PASS: command frontmatter valid')
"

# Test 3: Kiểm tra /librarian command khả dụng
# (Cần test thủ công trong Claude Code session)
# Gõ: /librarian recommend
# Expected: Librarian phân tích project và recommend skills
```

**Dependencies:** Deliverable 3.1 (librarian.md phải tồn tại)

---

### Deliverable 3.3: `hooks/hooks.json`

**File path:** `$HOME/Agent_Hub/agent-hub-index/hooks/hooks.json`

**Mục đích:** Cấu hình hook để Librarian chạy proactive detection khi bắt đầu session mới.

**Nội dung đầy đủ:**

```json
{
  "hooks": [
    {
      "name": "agent-hub-session-start",
      "event": "session-start",
      "description": "Detect project context and suggest relevant skills from Agent Hub library",
      "command": "$HOME/Agent_Hub/agent-hub-index/hooks/session-start",
      "timeout_ms": 5000,
      "enabled": true
    }
  ]
}
```

**Các bước triển khai:**

1. Tạo file `hooks/hooks.json` với nội dung trên
2. Đảm bảo path đến `session-start` script chính xác
3. Set timeout hợp lý (5 giây)

**Test criteria:**

```bash
# Test 1: File tồn tại và JSON hợp lệ
python3 -c "
import json
with open('$HOME/Agent_Hub/agent-hub-index/hooks/hooks.json') as f:
    data = json.load(f)
assert 'hooks' in data, 'Missing hooks key'
assert len(data['hooks']) > 0, 'No hooks defined'
hook = data['hooks'][0]
assert hook['event'] == 'session-start', f'Expected session-start, got {hook[\"event\"]}'
print('PASS: hooks.json valid')
"

# Test 2: Referenced script exists
SCRIPT=$(python3 -c "
import json
with open('$HOME/Agent_Hub/agent-hub-index/hooks/hooks.json') as f:
    data = json.load(f)
print(data['hooks'][0]['command'])
")
test -f "$SCRIPT" && echo "PASS: session-start script exists"
```

**Dependencies:** Deliverable 3.4 (session-start script phải tồn tại)

---

### Deliverable 3.4: `hooks/session-start`

**File path:** `$HOME/Agent_Hub/agent-hub-index/hooks/session-start`

**Mục đích:** Script chạy khi bắt đầu session. Phát hiện project context và suggest skills nếu chưa có.

**Input:** Không có arguments. Đọc environment variable `$PWD` (working directory).

**Output:** JSON stdout với thông tin context (Claude Code đọc output này).

**Logic chính:**

1. Kiểm tra working directory có phải project (có package.json, Cargo.toml, go.mod, etc.)
2. Kiểm tra đã có `.claude/skills/` với skills từ Agent Hub chưa
3. Nếu là project mới (chưa có skills):
   - Detect tech stack từ project files
   - Tìm matching stack trong `library/stacks/`
   - Output suggestion JSON

**Nội dung script (bash):**

```bash
#!/bin/bash
# hooks/session-start — Proactive Agent Hub detection
# Called by Claude Code on session start via hooks.json

set -euo pipefail

LIBRARY_DIR="$HOME/Agent_Hub/agent-hub-index/library"
CATALOG="$LIBRARY_DIR/catalog.json"
PROJECT_DIR="${PWD:-$(pwd)}"
MANIFEST="$PROJECT_DIR/.agent-hub-manifest.json"

# Nếu đã có manifest → project đã setup → skip
if [ -f "$MANIFEST" ]; then
  exit 0
fi

# Detect project type
detect_stack() {
  local dir="$1"

  # ROS2
  if [ -f "$dir/package.xml" ] || ls "$dir"/*/package.xml >/dev/null 2>&1; then
    echo "ros2-robotics"
    return
  fi

  # TypeScript fullstack
  if [ -f "$dir/package.json" ] && [ -f "$dir/tsconfig.json" ]; then
    if grep -q '"next"' "$dir/package.json" 2>/dev/null || \
       grep -q '"react"' "$dir/package.json" 2>/dev/null; then
      echo "web-fullstack-typescript"
      return
    fi
  fi

  # Go
  if [ -f "$dir/go.mod" ]; then
    echo "api-service-go"
    return
  fi

  # Python ML
  if [ -f "$dir/pyproject.toml" ] || [ -f "$dir/setup.py" ]; then
    if grep -q "torch\|pytorch\|tensorflow\|transformers" \
       "$dir/requirements.txt" "$dir/pyproject.toml" 2>/dev/null; then
      echo "ml-research-pytorch"
      return
    fi
  fi

  echo ""
}

STACK=$(detect_stack "$PROJECT_DIR")

if [ -n "$STACK" ] && [ -f "$CATALOG" ]; then
  # Output suggestion cho Claude Code
  cat << EOF
[Agent Hub] Detected project at: $PROJECT_DIR
Suggested stack: $STACK
To setup skills for this project, run: /librarian recommend
Or: python3 $HOME/Agent_Hub/agent-hub-index/scripts/publish-to-project.py --project "$PROJECT_DIR" --stack "$STACK"
EOF
fi
```

**Các bước triển khai:**

1. Tạo file `hooks/session-start` với nội dung trên
2. `chmod +x hooks/session-start`
3. Test với các loại project khác nhau

**Test criteria:**

```bash
# Test 1: Script executable
test -x $HOME/Agent_Hub/agent-hub-index/hooks/session-start \
  && echo "PASS: script is executable"

# Test 2: Chạy trong project ROS2
mkdir -p /tmp/test-ros2-project
touch /tmp/test-ros2-project/package.xml
cd /tmp/test-ros2-project && $HOME/Agent_Hub/agent-hub-index/hooks/session-start \
  | grep -q "ros2-robotics" && echo "PASS: detected ROS2 project"
rm -rf /tmp/test-ros2-project

# Test 3: Chạy trong project TypeScript
mkdir -p /tmp/test-ts-project
echo '{"dependencies":{"next":"14.0.0","react":"18.0.0"}}' > /tmp/test-ts-project/package.json
echo '{}' > /tmp/test-ts-project/tsconfig.json
cd /tmp/test-ts-project && $HOME/Agent_Hub/agent-hub-index/hooks/session-start \
  | grep -q "web-fullstack-typescript" && echo "PASS: detected TS project"
rm -rf /tmp/test-ts-project

# Test 4: Chạy trong project Go
mkdir -p /tmp/test-go-project
echo 'module example.com/test' > /tmp/test-go-project/go.mod
cd /tmp/test-go-project && $HOME/Agent_Hub/agent-hub-index/hooks/session-start \
  | grep -q "api-service-go" && echo "PASS: detected Go project"
rm -rf /tmp/test-go-project

# Test 5: Chạy khi đã có manifest (should exit silently)
mkdir -p /tmp/test-manifest-project
echo '{}' > /tmp/test-manifest-project/.agent-hub-manifest.json
cd /tmp/test-manifest-project && OUTPUT=$($HOME/Agent_Hub/agent-hub-index/hooks/session-start)
[ -z "$OUTPUT" ] && echo "PASS: skipped project with existing manifest"
rm -rf /tmp/test-manifest-project
```

**Dependencies:** Deliverable 2.2 (stacks phải tồn tại để suggest)

---

### Deliverable 3.5: `scripts/publish-to-project.py`

**File path:** `$HOME/Agent_Hub/agent-hub-index/scripts/publish-to-project.py`

**Mục đích:** Publish (copy) skills/agents từ library vào project cụ thể. Tạo manifest để track.

**Input:**
```
--project <path>          # Path đến project (mặc định: cwd)
--skills <id1,id2,...>    # Danh sách skill IDs để publish
--stack <stack_id>        # Publish tất cả skills trong stack
--collection <coll_id>    # Publish tất cả skills trong collection
--platform <platform>     # claude-code | opencode (mặc định: claude-code)
--dry-run                 # Chỉ hiển thị, không copy
--force                   # Ghi đè nếu đã tồn tại
```

**Output:**
- Copy skill files vào `<project>/.claude/skills/<skill-name>/SKILL.md` (hoặc `.opencode/skills/`)
- Tạo/cập nhật `<project>/.agent-hub-manifest.json`
- Log ra stdout

**Manifest format:**

```json
{
  "version": 1,
  "publishedAt": "2026-03-30T12:00:00Z",
  "updatedAt": "2026-03-30T12:00:00Z",
  "source": "agent-hub",
  "libraryPath": "$HOME/Agent_Hub/agent-hub-index/library",
  "platform": "claude-code",
  "skills": [
    {
      "id": "systematic-debugging",
      "type": "skill",
      "publishedAt": "2026-03-30T12:00:00Z",
      "source": "superpowers",
      "installedPath": ".claude/skills/systematic-debugging/SKILL.md"
    }
  ],
  "stacks": ["ros2-robotics"],
  "collections": []
}
```

**Các bước triển khai:**

1. **Parse arguments:**
   - Validate project path tồn tại
   - Resolve skill list: từ `--skills`, `--stack`, hoặc `--collection`

2. **Resolve skills từ stack/collection:**
   - Đọc `library/stacks/<id>.yaml` → lấy tất cả skill IDs (core + workflow)
   - Đọc `library/collections/<id>.yaml` → lấy tất cả entry IDs

3. **Hàm `publish_skill(skill_id, project_path, platform)`:**
   - Tìm skill trong `library/skills/<id>/` hoặc `library/agents/<id>/`
   - Determine target dir: `.claude/skills/<id>/` hoặc `.opencode/skills/<id>/`
   - `mkdir -p` target dir
   - Copy SKILL.md (hoặc AGENT.md) vào target
   - Return metadata

4. **Hàm `update_manifest(project_path, published_skills, stack, collection)`:**
   - Đọc manifest hiện tại nếu có
   - Merge skills mới (không duplicate)
   - Ghi manifest

5. **Dry run mode:**
   - Hiển thị danh sách actions sẽ thực hiện
   - Không copy file nào

6. **Main:**
   - Parse args → resolve skills → confirm (nếu không `--force`) → publish → update manifest → report

**Test criteria:**

```bash
# Test 1: Publish từ stack
mkdir -p /tmp/test-publish-project
python3 $HOME/Agent_Hub/agent-hub-index/scripts/publish-to-project.py \
  --project /tmp/test-publish-project \
  --stack ros2-robotics \
  --force

# Verify: skills được copy
test -d /tmp/test-publish-project/.claude/skills/systematic-debugging \
  && echo "PASS: skill directory created"
test -f /tmp/test-publish-project/.claude/skills/systematic-debugging/SKILL.md \
  && echo "PASS: SKILL.md copied"

# Verify: manifest created
test -f /tmp/test-publish-project/.agent-hub-manifest.json \
  && echo "PASS: manifest created"

python3 -c "
import json
with open('/tmp/test-publish-project/.agent-hub-manifest.json') as f:
    data = json.load(f)
assert len(data['skills']) > 5, f'Expected >5 skills, got {len(data[\"skills\"])}'
assert 'ros2-robotics' in data.get('stacks', []), 'Stack not in manifest'
print(f'PASS: manifest has {len(data[\"skills\"])} skills')
"

rm -rf /tmp/test-publish-project

# Test 2: Publish specific skills
mkdir -p /tmp/test-publish-specific
python3 $HOME/Agent_Hub/agent-hub-index/scripts/publish-to-project.py \
  --project /tmp/test-publish-specific \
  --skills systematic-debugging,brainstorming \
  --force

SKILL_COUNT=$(ls -d /tmp/test-publish-specific/.claude/skills/*/ 2>/dev/null | wc -l)
[ "$SKILL_COUNT" -eq 2 ] && echo "PASS: exactly 2 skills published"

rm -rf /tmp/test-publish-specific

# Test 3: Dry run
mkdir -p /tmp/test-dry-run
python3 $HOME/Agent_Hub/agent-hub-index/scripts/publish-to-project.py \
  --project /tmp/test-dry-run \
  --stack web-fullstack-typescript \
  --dry-run

test ! -d /tmp/test-dry-run/.claude && echo "PASS: dry run did not create files"
rm -rf /tmp/test-dry-run

# Test 4: Publish cho opencode
mkdir -p /tmp/test-opencode
python3 $HOME/Agent_Hub/agent-hub-index/scripts/publish-to-project.py \
  --project /tmp/test-opencode \
  --skills brainstorming \
  --platform opencode \
  --force

test -f /tmp/test-opencode/.opencode/skills/brainstorming/SKILL.md \
  && echo "PASS: published to .opencode"
rm -rf /tmp/test-opencode
```

**Dependencies:** Phase 1 (library entries), Phase 2 (stacks/collections)

---

### Exit Criteria cho Phase 3

- [ ] `/librarian` command load được và respond (test trong Claude Code session)
- [ ] Proactive mode detect new project và suggest stack phù hợp
- [ ] `publish-to-project.py --project <path> --stack ros2-robotics` copy skills + tạo manifest
- [ ] Librarian recommend skills dựa trên project context
- [ ] Librarian publish skills với user approval (qua `--force` hoặc interactive confirm)
- [ ] Hook `session-start` chạy trong < 5 giây

---

## Phase 4: Integration Test & Polish — 1-2 giờ

### Mục tiêu
Test end-to-end toàn bộ system, tạo rebuild script, và viết README.

---

### Deliverable 4.1-4.3: End-to-End Tests (3 scenarios)

#### Test Scenario 1: New Project → Proactive Suggest → Publish → Verify

**Preconditions:**
- Agent Hub library đã build xong (Phase 1-3)
- Catalog.json hợp lệ

**Actions:**
```bash
# Bước 1: Tạo project Go mới
mkdir -p /tmp/e2e-test-go
echo 'module example.com/myservice' > /tmp/e2e-test-go/go.mod
echo 'package main' > /tmp/e2e-test-go/main.go

# Bước 2: Simulate session-start hook
cd /tmp/e2e-test-go
OUTPUT=$($HOME/Agent_Hub/agent-hub-index/hooks/session-start)
echo "$OUTPUT"

# Bước 3: Publish stack
python3 $HOME/Agent_Hub/agent-hub-index/scripts/publish-to-project.py \
  --project /tmp/e2e-test-go \
  --stack api-service-go \
  --force

# Bước 4: Verify
```

**Expected results:**
- Hook output chứa "api-service-go"
- `.claude/skills/golang-patterns/SKILL.md` tồn tại
- `.claude/skills/golang-testing/SKILL.md` tồn tại
- `.claude/skills/api-design/SKILL.md` tồn tại
- `.agent-hub-manifest.json` tồn tại với >= 8 skills

**Verification commands:**
```bash
grep -q "api-service-go" <<< "$OUTPUT" && echo "PASS: correct stack detected"
test -f /tmp/e2e-test-go/.claude/skills/golang-patterns/SKILL.md && echo "PASS: golang-patterns"
test -f /tmp/e2e-test-go/.claude/skills/golang-testing/SKILL.md && echo "PASS: golang-testing"
test -f /tmp/e2e-test-go/.claude/skills/api-design/SKILL.md && echo "PASS: api-design"
python3 -c "
import json
with open('/tmp/e2e-test-go/.agent-hub-manifest.json') as f:
    m = json.load(f)
print(f'Skills: {len(m[\"skills\"])}')
assert len(m['skills']) >= 8
print('PASS: manifest complete')
"
rm -rf /tmp/e2e-test-go
```

---

#### Test Scenario 2: /librarian → Recommend → Publish Subset

**Preconditions:**
- Agent Hub library đã build xong
- Đang ở trong một project TypeScript

**Actions:**
```bash
# Bước 1: Tạo project TypeScript
mkdir -p /tmp/e2e-test-ts
echo '{"dependencies":{"next":"14.0","react":"18.0","prisma":"5.0"}}' > /tmp/e2e-test-ts/package.json
echo '{"compilerOptions":{"target":"es2022"}}' > /tmp/e2e-test-ts/tsconfig.json

# Bước 2: (Trong Claude Code session) Gõ /librarian recommend
# Hoặc simulate bằng script:
cd /tmp/e2e-test-ts
$HOME/Agent_Hub/agent-hub-index/hooks/session-start

# Bước 3: Publish chỉ frontend + testing skills
python3 $HOME/Agent_Hub/agent-hub-index/scripts/publish-to-project.py \
  --project /tmp/e2e-test-ts \
  --skills frontend-patterns,tdd-workflow,e2e-testing,postgres-patterns \
  --force

# Bước 4: Verify
```

**Expected results:**
- Chỉ 4 skills được publish (không phải toàn bộ stack)
- Manifest liệt kê chính xác 4 skills

**Verification commands:**
```bash
SKILL_COUNT=$(ls -d /tmp/e2e-test-ts/.claude/skills/*/ 2>/dev/null | wc -l)
[ "$SKILL_COUNT" -eq 4 ] && echo "PASS: exactly 4 skills published"
python3 -c "
import json
with open('/tmp/e2e-test-ts/.agent-hub-manifest.json') as f:
    m = json.load(f)
ids = [s['id'] for s in m['skills']]
expected = {'frontend-patterns', 'tdd-workflow', 'e2e-testing', 'postgres-patterns'}
assert set(ids) == expected, f'Expected {expected}, got {set(ids)}'
print('PASS: correct skills in manifest')
"
rm -rf /tmp/e2e-test-ts
```

---

#### Test Scenario 3: Contribute New Skill → Import → Catalog Update

**Preconditions:**
- Library đã có ~50 entries
- catalog.json đã build

**Actions:**
```bash
# Bước 1: Tạo skill mới trong superpowers (simulate)
mkdir -p /tmp/e2e-test-contribute
cat > /tmp/e2e-test-contribute/SKILL.md << 'EOF'
---
name: "ros2-launch-debugger"
description: "Debug ROS2 launch files and node configurations"
---

# ROS2 Launch Debugger

A skill for debugging ROS2 launch files, node parameters, and remappings.

## When to use
- Launch file fails to start nodes
- Parameters not loaded correctly
- Topic remappings broken
EOF

# Bước 2: Import (cần support --path tùy chỉnh hoặc copy vào source trước)
# Option A: Copy vào superpowers rồi import
# Option B: Import trực tiếp từ path (cần extension)
# Sử dụng import-skill.py với --source-path override (nếu có)

# Giả sử skill đã ở đúng vị trí trong source:
python3 $HOME/Agent_Hub/agent-hub-index/scripts/import-skill.py \
  --source superpowers --skill ros2-launch-debugger --force 2>/dev/null || \
  echo "NOTE: skill not in superpowers source - this tests the error path"

# Bước 3: Rebuild catalog
python3 $HOME/Agent_Hub/agent-hub-index/scripts/build-catalog.py

# Bước 4: Verify catalog updated
python3 -c "
import json
with open('$HOME/Agent_Hub/agent-hub-index/library/catalog.json') as f:
    data = json.load(f)
print(f'Total entries: {data[\"totalEntries\"]}')
"
```

**Expected results:**
- Import thành công (hoặc báo lỗi nếu skill không tồn tại trong source)
- Catalog rebuild thành công
- Entry count tăng nếu import thành công

**Verification commands:**
```bash
# Verify catalog.json is valid JSON
python3 -c "
import json
with open('$HOME/Agent_Hub/agent-hub-index/library/catalog.json') as f:
    json.load(f)
print('PASS: catalog.json is valid')
"
```

---

### Deliverable 4.4: `scripts/rebuild.sh`

**File path:** `$HOME/Agent_Hub/agent-hub-index/scripts/rebuild.sh`

**Mục đích:** Script chạy toàn bộ pipeline: batch import → build catalog → validate.

**Nội dung đầy đủ:**

```bash
#!/bin/bash
# rebuild.sh — Full Agent Hub pipeline
# Usage: ./scripts/rebuild.sh [--skip-import] [--verbose]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LIBRARY_DIR="$PROJECT_DIR/library"

# Parse args
SKIP_IMPORT=false
VERBOSE=""
for arg in "$@"; do
  case "$arg" in
    --skip-import) SKIP_IMPORT=true ;;
    --verbose) VERBOSE="--verbose" ;;
  esac
done

echo "============================================"
echo "  Agent Hub — Full Rebuild"
echo "============================================"
echo "Project: $PROJECT_DIR"
echo "Library: $LIBRARY_DIR"
echo ""

# Step 1: Import (unless skipped)
if [ "$SKIP_IMPORT" = false ]; then
  echo ">>> Step 1/3: Importing skills..."
  if [ -f "$SCRIPT_DIR/batch-import.sh" ]; then
    bash "$SCRIPT_DIR/batch-import.sh"
  else
    echo "  [SKIP] batch-import.sh not found"
  fi
  echo ""
else
  echo ">>> Step 1/3: Import SKIPPED"
  echo ""
fi

# Step 2: Build catalog
echo ">>> Step 2/3: Building catalog..."
python3 "$SCRIPT_DIR/build-catalog.py" $VERBOSE
echo ""

# Step 3: Validate
echo ">>> Step 3/3: Validating..."
python3 "$SCRIPT_DIR/validate.py" $VERBOSE
VALIDATE_EXIT=$?
echo ""

# Summary
echo "============================================"
echo "  Rebuild Complete"
echo "============================================"
SKILL_COUNT=$(ls -d "$LIBRARY_DIR/skills/"*/ 2>/dev/null | wc -l)
AGENT_COUNT=$(ls -d "$LIBRARY_DIR/agents/"*/ 2>/dev/null | wc -l)
COLL_COUNT=$(ls "$LIBRARY_DIR/collections/"*.yaml 2>/dev/null | wc -l)
STACK_COUNT=$(ls "$LIBRARY_DIR/stacks/"*.yaml 2>/dev/null | wc -l)

echo "  Skills:      $SKILL_COUNT"
echo "  Agents:      $AGENT_COUNT"
echo "  Collections: $COLL_COUNT"
echo "  Stacks:      $STACK_COUNT"
echo "  Catalog:     $(test -f "$LIBRARY_DIR/catalog.json" && echo "OK" || echo "MISSING")"
echo "  Validation:  $([ $VALIDATE_EXIT -eq 0 ] && echo "PASS" || echo "FAIL")"
echo "============================================"

exit $VALIDATE_EXIT
```

**Các bước triển khai:**

1. Tạo file `scripts/rebuild.sh`
2. `chmod +x scripts/rebuild.sh`
3. Test chạy

**Test criteria:**

```bash
# Test 1: Full rebuild
$HOME/Agent_Hub/agent-hub-index/scripts/rebuild.sh --skip-import
echo "Exit code: $?"  # Expected: 0

# Test 2: Verbose mode
$HOME/Agent_Hub/agent-hub-index/scripts/rebuild.sh --skip-import --verbose

# Test 3: Verify output có summary
$HOME/Agent_Hub/agent-hub-index/scripts/rebuild.sh --skip-import 2>&1 \
  | grep -q "Rebuild Complete" && echo "PASS: summary present"
```

**Dependencies:** Phase 1 (import-skill.py, build-catalog.py), Phase 2 (validate.py)

---

### Deliverable 4.5: README.md

**File path:** `$HOME/Agent_Hub/agent-hub-index/README.md`

**Nội dung cần bao gồm:**

1. **Tiêu đề + mô tả ngắn** (1-2 câu)
2. **Quick Start:**
   - `./scripts/rebuild.sh` — build toàn bộ
   - `/librarian recommend` — nhận gợi ý skills
3. **Cấu trúc thư mục** (tóm tắt)
4. **Scripts reference:**
   - `import-skill.py` — import skill
   - `build-catalog.py` — build catalog
   - `validate.py` — validate references
   - `publish-to-project.py` — publish to project
   - `rebuild.sh` — full pipeline
5. **Cách sử dụng Librarian:**
   - Slash command
   - Proactive mode
   - Manual publish
6. **Cách contribute skill mới**
7. **Source projects** — danh sách 5 sources

**Test criteria:**

```bash
test -f $HOME/Agent_Hub/agent-hub-index/README.md && echo "PASS: README exists"
# Verify có Quick Start section
grep -q "Quick Start\|Quickstart\|Getting Started" \
  $HOME/Agent_Hub/agent-hub-index/README.md && echo "PASS: has quick start"
```

---

### 10 Test Scenarios Chi Tiết

| # | Scenario | Preconditions | Actions | Expected Results | Verification |
|---|----------|---------------|---------|------------------|-------------|
| 1 | Import single skill | Phase 0 done | `import-skill.py --source superpowers --skill brainstorming` | SKILL.md + provenance.yaml created | `test -f library/skills/brainstorming/SKILL.md` |
| 2 | Import agent | Phase 0 done | `import-skill.py --source get-shit-done --skill gsd-planner --type agent` | AGENT.md + provenance.yaml created | `test -f library/agents/gsd-planner/AGENT.md` |
| 3 | Build catalog | ~50 entries imported | `build-catalog.py` | catalog.json with ~50 entries | `python3 -c "import json; d=json.load(open('library/catalog.json')); print(len(d['entries']))"` |
| 4 | Validate clean | Phase 2 done | `validate.py` | Exit 0 | `validate.py; echo $?` |
| 5 | Validate catches error | Bad YAML injected | `validate.py` | Exit 1, error message | `validate.py; [ $? -ne 0 ] && echo PASS` |
| 6 | Detect ROS2 project | package.xml exists | `hooks/session-start` | Output contains "ros2-robotics" | `grep ros2-robotics` |
| 7 | Detect Go project | go.mod exists | `hooks/session-start` | Output contains "api-service-go" | `grep api-service-go` |
| 8 | Publish stack | Library built | `publish-to-project.py --stack api-service-go --project /tmp/x` | Skills copied + manifest | `test -f /tmp/x/.agent-hub-manifest.json` |
| 9 | Publish specific skills | Library built | `publish-to-project.py --skills a,b --project /tmp/x` | Only 2 skills copied | `ls .claude/skills/ \| wc -l` |
| 10 | Full rebuild | Phase 0 done | `rebuild.sh` | All steps pass, exit 0 | `rebuild.sh; echo $?` |

---

### Exit Criteria cho Phase 4

- [ ] Tất cả 10 test scenarios pass
- [ ] `rebuild.sh` chạy end-to-end exit code 0
- [ ] `README.md` tồn tại với Quick Start section
- [ ] Không có orphan files (mọi skill/agent có provenance)
- [ ] catalog.json, collections, stacks đều validate pass

---

## Phase 5: Multi-platform (Tùy chọn) — 1-2 giờ

### Mục tiêu
Mở rộng hỗ trợ cho các AI coding assistants khác ngoài Claude Code.

### Deliverable 5.1: OpenCode Skill File

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/agents/librarian-opencode.md`

**Nội dung:**
- Adaption của librarian.md cho OpenCode format
- Thay đổi:
  - Tool names theo OpenCode conventions
  - Path format cho `.opencode/skills/` thay vì `.claude/skills/`
  - Remove Claude Code-specific features (hooks)

**Test:**
```bash
test -f $HOME/Agent_Hub/agent-hub-index/library/agents/librarian-opencode.md \
  && echo "PASS"
```

### Deliverable 5.2: Codex Skill File

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/agents/librarian-codex.md`

**Nội dung:**
- Adaption cho Codex (OpenAI) format
- Simplified version (Codex có ít tool access hơn)
- Focus vào recommendation only (publish thủ công)

**Test:**
```bash
test -f $HOME/Agent_Hub/agent-hub-index/library/agents/librarian-codex.md \
  && echo "PASS"
```

### Deliverable 5.3: Copilot Instructions Fragment

**File path:** `$HOME/Agent_Hub/agent-hub-index/library/agents/librarian-copilot.md`

**Nội dung:**
- Fragment cho `.github/copilot-instructions.md`
- Chỉ recommendation (Copilot không có skill system)
- Embed danh sách skills trực tiếp thay vì đọc catalog

**Test:**
```bash
test -f $HOME/Agent_Hub/agent-hub-index/library/agents/librarian-copilot.md \
  && echo "PASS"
```

### Cập nhật `publish-to-project.py`

Thêm logic cho mỗi platform:

| Platform | Target Directory | Skill Format |
|----------|-----------------|-------------|
| claude-code | `.claude/skills/<name>/SKILL.md` | Markdown với YAML frontmatter |
| opencode | `.opencode/skills/<name>/SKILL.md` | Markdown với YAML frontmatter |
| codex | `codex-instructions/<name>.md` | Markdown |
| copilot | `.github/copilot-instructions.md` | Append to single file |

---

## Timeline Summary

```
╔════════════════════════════════════════════════════════════════════════╗
║                    AGENT HUB — IMPLEMENTATION TIMELINE               ║
╠═══════════╦══════╦══════╦══════╦══════╦══════╦══════╦══════╦═════════╣
║   Phase   ║ 0.5h ║  1h  ║  2h  ║  3h  ║  4h  ║  5h  ║  6h  ║ 7-16h  ║
╠═══════════╬══════╬══════╬══════╬══════╬══════╬══════╬══════╬═════════╣
║ Phase 0   ║██████║      ║      ║      ║      ║      ║      ║         ║
║ Cleanup   ║ 30m  ║      ║      ║      ║      ║      ║      ║         ║
╠═══════════╬══════╬══════╬══════╬══════╬══════╬══════╬══════╬═════════╣
║ Phase 1   ║      ║██████║██████║██████║██████║      ║      ║         ║
║ Library   ║      ║ import-skill.py  ║ build-catalog  ║      ║         ║
║ Infra     ║      ║      ║ batch import 50  ║      ║      ║         ║
╠═══════════╬══════╬══════╬══════╬══════╬══════╬══════╬══════╬═════════╣
║ Phase 2   ║      ║      ║      ║      ║██████║██████║██████║         ║
║ Coll &    ║      ║      ║      ║      ║ 4 collections ║      ║         ║
║ Stacks    ║      ║      ║      ║      ║ 4 stacks      ║      ║         ║
║           ║      ║      ║      ║      ║ validate.py   ║      ║         ║
╠═══════════╬══════╬══════╬══════╬══════╬══════╬══════╬══════╬═════════╣
║ Phase 3   ║      ║      ║      ║      ║      ║      ║██████║█████████║
║ Librarian ║      ║      ║      ║      ║      ║      ║ agent║ command ║
║           ║      ║      ║      ║      ║      ║      ║ hook ║ publish ║
╠═══════════╬══════╬══════╬══════╬══════╬══════╬══════╬══════╬═════════╣
║ Phase 4   ║      ║      ║      ║      ║      ║      ║      ║█████████║
║ Test &    ║      ║      ║      ║      ║      ║      ║      ║ E2E     ║
║ Polish    ║      ║      ║      ║      ║      ║      ║      ║ rebuild ║
╠═══════════╬══════╬══════╬══════╬══════╬══════╬══════╬══════╬═════════╣
║ Phase 5   ║      ║      ║      ║      ║      ║      ║      ║(tùy chọn)║
║ Multi-plat║      ║      ║      ║      ║      ║      ║      ║ 1-2h    ║
╚═══════════╩══════╩══════╩══════╩══════╩══════╩══════╩══════╩═════════╝

TỔNG: ~9-16 giờ (không kể Phase 5)

Chi tiết:
  Phase 0: ████                              30 phút
  Phase 1: ████████████████                  2-4 giờ
  Phase 2: ████████████                      2-3 giờ
  Phase 3: ████████████████████              3-5 giờ
  Phase 4: ████████                          1-2 giờ
  Phase 5: ████████ (optional)               1-2 giờ
```

---

## Risk Assessment

### Phase 0: Cleanup

| Rủi ro | Khả năng | Tác động | Giảm thiểu |
|--------|----------|----------|-----------|
| Xóa nhầm file cần thiết | Thấp | Cao | Backup trước khi xóa. Kiểm tra danh sách xóa 2 lần |
| mcp-server/ dependency | Trung bình | Trung bình | Giữ mcp-server/, không xóa. Tích hợp sau nếu cần |

**Nếu bị kẹt:** Restore từ backup tại `/tmp/agent-hub-backup-*`. Hoặc dùng `git checkout` nếu đã commit.

---

### Phase 1: Library Infrastructure

| Rủi ro | Khả năng | Tác động | Giảm thiểu |
|--------|----------|----------|-----------|
| Source paths thay đổi | Trung bình | Cao | Hardcode paths trong SOURCE_MAP, dễ update. Test từng source trước khi batch |
| Skill names không match slug | Cao | Trung bình | Normalize name → slug (lowercase, replace spaces with -). Handle edge cases |
| YAML frontmatter thiếu/lỗi | Cao | Thấp | Fallback sang filename-based naming. Log warnings |
| Quá nhiều entries → catalog lớn | Thấp | Thấp | Curate 50 entries, không import tất cả 407 |
| Python dependency (pyyaml) | Thấp | Trung bình | `pip install pyyaml` nếu chưa có. Hoặc dùng regex fallback |

**Nếu bị kẹt:**
- Source path không tìm thấy → Chạy `find $HOME/Agent_Hub/<source> -name "SKILL.md"` để locate
- YAML parse error → Dùng regex fallback cho frontmatter
- Import 1 source fails → Skip, import các sources khác trước

---

### Phase 2: Collections & Stacks

| Rủi ro | Khả năng | Tác động | Giảm thiểu |
|--------|----------|----------|-----------|
| Skill ID không tồn tại trong library | Cao | Cao | Chạy validate.py ngay sau khi tạo YAML. Fix references |
| YAML syntax error | Trung bình | Thấp | Dùng YAML linter. Test parse mỗi file |
| Sequencing logic sai | Thấp | Thấp | Review manually. Không ảnh hưởng technical correctness |

**Nếu bị kẹt:**
- validate.py báo lỗi reference → Kiểm tra `ls library/skills/` vs ID trong YAML
- YAML error → Dùng online YAML validator
- Không chắc skill nào phù hợp → Tham khảo registry.json cũ (đã backup)

---

### Phase 3: The Librarian

| Rủi ro | Khả năng | Tác động | Giảm thiểu |
|--------|----------|----------|-----------|
| Slash command không load | Trung bình | Cao | Test trong Claude Code. Kiểm tra path, frontmatter format |
| Hook timeout | Trung bình | Trung bình | Set timeout 5s. Optimize session-start script |
| Publish overwrite user files | Thấp | Cao | Luôn check tồn tại + confirm. Default no-overwrite |
| Proactive detect sai stack | Trung bình | Thấp | Detect dựa trên multiple signals, không chỉ 1 file |
| catalog.json quá lớn cho context | Thấp | Trung bình | Giữ catalog nhỏ (~50 entries). Lazy load khi cần |

**Nếu bị kẹt:**
- Slash command không load → Kiểm tra `commands/` path trong Claude Code settings
- Hook không chạy → Test script manually, kiểm tra `hooks.json` format
- Publish fail → Test `publish-to-project.py` standalone trước khi tích hợp

---

### Phase 4: Integration Test & Polish

| Rủi ro | Khả năng | Tác động | Giảm thiểu |
|--------|----------|----------|-----------|
| E2E test fail vì environment | Trung bình | Thấp | Dùng `/tmp/` cho test projects. Cleanup sau mỗi test |
| rebuild.sh fail trên một step | Trung bình | Thấp | `set -euo pipefail` + error messages rõ ràng |

**Nếu bị kẹt:**
- E2E fail → Run từng step manually để isolate
- rebuild.sh fail → Chạy từng script riêng lẻ

---

### Phase 5: Multi-platform

| Rủi ro | Khả năng | Tác động | Giảm thiểu |
|--------|----------|----------|-----------|
| Không biết format chính xác của platform khác | Cao | Trung bình | Research documentation. Tạo minimal version trước |
| Platform API thay đổi | Trung bình | Thấp | Giữ simple, dễ update |

**Nếu bị kẹt:**
- Phase 5 là optional. Skip nếu không đủ thời gian
- Focus Claude Code trước, mở rộng sau

---

## Dependencies Graph

```
                            ┌─────────────┐
                            │   Phase 0   │
                            │   Cleanup   │
                            │   (30 min)  │
                            └──────┬──────┘
                                   │
                                   ▼
                  ┌────────────────────────────────────┐
                  │            Phase 1                  │
                  │    Library Infrastructure           │
                  │           (2-4h)                    │
                  │                                    │
                  │  ┌─────────┐    ┌──────────────┐   │
                  │  │ D1.2    │    │    D1.3      │   │
                  │  │ import- │    │  build-      │   │
                  │  │ skill.py│    │  catalog.py  │   │
                  │  └────┬────┘    └──────┬───────┘   │
                  │       │               │            │
                  │       ▼               │            │
                  │  ┌─────────┐          │            │
                  │  │  D1.4   │          │            │
                  │  │ Import  │──────────┘            │
                  │  │ ~50     │                       │
                  │  │ entries │          ┌─────────┐  │
                  │  └────┬────┘    ┌────▶│  D1.5   │  │
                  │       │         │     │catalog. │  │
                  │       └─────────┘     │  json   │  │
                  │                       └────┬────┘  │
                  └────────────────────────────┼───────┘
                                               │
                              ┌─────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │            Phase 2                 │
              │      Collections & Stacks          │
              │            (2-3h)                   │
              │                                    │
              │  ┌──────────┐   ┌──────────────┐  │
              │  │   D2.1   │   │    D2.2      │  │
              │  │ 4 collec-│   │  4 stacks    │  │
              │  │  tions   │   │              │  │
              │  └────┬─────┘   └──────┬───────┘  │
              │       │                │           │
              │       └────────┬───────┘           │
              │                ▼                   │
              │         ┌──────────┐               │
              │         │   D2.3   │               │
              │         │validate. │               │
              │         │   py     │               │
              │         └────┬─────┘               │
              └──────────────┼─────────────────────┘
                             │
                             ▼
         ┌───────────────────────────────────────────┐
         │              Phase 3                       │
         │           The Librarian                    │
         │              (3-5h)                        │
         │                                           │
         │  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
         │  │   D3.1   │  │   D3.4   │  │  D3.5   │ │
         │  │librarian │  │ session- │  │publish- │ │
         │  │   .md    │  │  start   │  │to-proj. │ │
         │  └────┬─────┘  └────┬─────┘  └────┬────┘ │
         │       │             │              │      │
         │       ▼             ▼              │      │
         │  ┌──────────┐  ┌──────────┐        │      │
         │  │   D3.2   │  │   D3.3   │        │      │
         │  │/librarian│  │hooks.json│        │      │
         │  │ command  │  │          │        │      │
         │  └────┬─────┘  └────┬─────┘        │      │
         └───────┼─────────────┼──────────────┼──────┘
                 │             │              │
                 └─────────┬───┘──────────────┘
                           │
                           ▼
         ┌───────────────────────────────────────────┐
         │              Phase 4                       │
         │       Integration Test & Polish            │
         │              (1-2h)                        │
         │                                           │
         │  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
         │  │D4.1 E2E  │  │D4.4      │  │ D4.5    │ │
         │  │D4.2 E2E  │  │rebuild.sh│  │README.md│ │
         │  │D4.3 E2E  │  │          │  │         │ │
         │  └──────────┘  └──────────┘  └─────────┘ │
         └──────────────────┬────────────────────────┘
                            │
                            ▼ (optional)
         ┌───────────────────────────────────────────┐
         │              Phase 5                       │
         │          Multi-platform                    │
         │           (1-2h, optional)                 │
         │                                           │
         │  ┌──────────┐ ┌──────────┐ ┌───────────┐ │
         │  │ OpenCode │ │  Codex   │ │  Copilot  │ │
         │  └──────────┘ └──────────┘ └───────────┘ │
         └───────────────────────────────────────────┘
```

### Dependency Rules

1. **Phase 0 phải hoàn thành trước** mọi phase khác (cleanup trước, build sau)
2. **Phase 1 phải hoàn thành trước Phase 2** (cần có library entries để references trong YAML hoạt động)
3. **Phase 2 phải hoàn thành trước Phase 3** (Librarian cần biết collections/stacks)
4. **Phase 1-3 phải hoàn thành trước Phase 4** (E2E test cần toàn bộ system)
5. **Phase 5 độc lập** — có thể làm bất cứ lúc nào sau Phase 3

### Deliverable Dependencies trong Phase

| Deliverable | Depends On |
|------------|-----------|
| D1.2 (import-skill.py) | Phase 0 |
| D1.3 (build-catalog.py) | Phase 0 |
| D1.4 (batch import) | D1.2 |
| D1.5 (catalog.json) | D1.3 + D1.4 |
| D2.1 (collections) | D1.4 (cần biết valid IDs) |
| D2.2 (stacks) | D1.4 (cần biết valid IDs) |
| D2.3 (validate.py) | D1.4 + D2.1 + D2.2 |
| D3.1 (librarian.md) | D1.5 + D2.1 + D2.2 |
| D3.2 (/librarian cmd) | D3.1 |
| D3.3 (hooks.json) | D3.4 |
| D3.4 (session-start) | D2.2 (cần stacks để suggest) |
| D3.5 (publish-to-project.py) | D1.4 + D2.1 + D2.2 |
| D4.1-4.3 (E2E tests) | Phase 1-3 all |
| D4.4 (rebuild.sh) | D1.2 + D1.3 + D2.3 |
| D4.5 (README.md) | Phase 1-3 all |

---

## Checklist Tổng Thể

### Phase 0
- [ ] Backup tạo thành công
- [ ] 6 files cũ đã xóa
- [ ] Cấu trúc thư mục mới tạo xong
- [ ] docs/ vẫn còn nguyên

### Phase 1
- [ ] `scripts/import-skill.py` hoạt động
- [ ] `scripts/build-catalog.py` hoạt động
- [ ] ~50 entries imported vào library/
- [ ] `library/catalog.json` generated và hợp lệ
- [ ] Mỗi entry có provenance.yaml

### Phase 2
- [ ] 4 collections tạo xong
- [ ] 4 stacks tạo xong
- [ ] `scripts/validate.py` hoạt động
- [ ] validate.py exit code 0

### Phase 3
- [ ] `library/agents/librarian.md` tạo xong
- [ ] `commands/librarian.md` tạo xong
- [ ] `hooks/hooks.json` tạo xong
- [ ] `hooks/session-start` tạo xong và executable
- [ ] `scripts/publish-to-project.py` hoạt động
- [ ] Proactive detection hoạt động

### Phase 4
- [ ] 3 E2E test scenarios pass
- [ ] 10 test scenarios pass
- [ ] `scripts/rebuild.sh` hoạt động
- [ ] `README.md` tạo xong

### Phase 5 (Optional)
- [ ] OpenCode skill file
- [ ] Codex skill file
- [ ] Copilot instructions fragment
