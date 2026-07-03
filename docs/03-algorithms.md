# 03 - Thuat toan (Algorithms)

> Tai lieu chi tiet cac thuat toan cot loi cua he thong **Agent Hub** -- thu vien ca nhan quan ly Skills/Agents voi AI Librarian.
>
> Muc dich: Mot lap trinh vien co the doc tai lieu nay va implement truc tiep ma khong can hoi them.

---

## Muc luc

1. [Thuat toan Import (import-skill.py)](#1-thuat-toan-import-import-skillpy)
2. [Thuat toan Build Catalog (build-catalog.py)](#2-thuat-toan-build-catalog-build-catalogpy)
3. [Thuat toan Stack Matching (Librarian su dung)](#3-thuat-toan-stack-matching)
4. [Thuat toan Publish (publish-to-project.py)](#4-thuat-toan-publish-publish-to-projectpy)
5. [Thuat toan Validation (validate.py)](#5-thuat-toan-validation-validatepy)
6. [Thuat toan Proactive Detection (session hook)](#6-thuat-toan-proactive-detection-session-hook)
7. [Thuat toan Conflict Detection](#7-thuat-toan-conflict-detection)

---

## Tong quan he thong

```
6 source projects (~407 entries)
        |
        v
  [import-skill.py]  -- chon loc ~50 entries
        |
        v
    library/
    +-- skills/{skill_name}/SKILL.md + provenance.yaml
    +-- agents/{agent_name}.md + provenance.yaml
        |
        v
  [build-catalog.py]  -- tao catalog.json voi metadata enriched
        |
        v
    catalog.json  (use_with, project_types, complexity, usage_pattern, ...)
        |
        v
  [Librarian Agent]  -- dung stack matching de recommend
        |
        v
  [publish-to-project.py]  -- deploy vao project cua user
        |
        v
    target/.claude/skills/  +  library-manifest.yaml
```

### Cau truc du lieu chung

```yaml
# provenance.yaml -- theo doi nguon goc cua moi entry
source_project: "superpowers"          # ten project goc
source_path: "skills/brainstorming/SKILL.md"  # duong dan trong project goc
imported_at: "2026-03-15T10:30:00Z"    # thoi diem import
imported_by: "dkhai"                   # nguoi import
original_hash: "sha256:abc123..."      # hash file goc tai thoi diem import
library_version: 1                     # so lan cap nhat trong library
```

```jsonc
// catalog.json -- metadata enriched cho moi entry
{
  "version": 1,
  "builtAt": "2026-03-30T05:48:49Z",
  "totalEntries": 50,
  "entries": [
    {
      "id": "brainstorming",
      "name": "brainstorming",
      "type": "skill",
      "source": "superpowers",
      "description": "...",
      "domains": ["planning", "design"],
      "technologies": ["typescript"],
      "phases": ["planning", "architecture"],
      "platforms": ["claude-code", "codex", "cursor", "opencode"],
      "tools": [],
      "cost": "medium",
      "stability": "stable",
      "complexity": "intermediate",
      "usage_pattern": "before-implementation",
      "project_types": ["web-app", "api", "cli"],
      "use_with": ["writing-plans", "executing-plans"],
      "conflicts_with": [],
      "curator_notes": "Nen dung truoc moi task sang tao...",
      "collections": ["core-workflow"],
      "stacks": ["web-fullstack", "ros2-robotics"]
    }
  ]
}
```

---

## 1. Thuat toan Import (import-skill.py)

### 1.1 Mo ta

Thuat toan import chon loc mot skill hoac agent tu 1 trong 6 source projects, copy vao thu vien chung (`library/`), tao file `provenance.yaml` de theo doi nguon goc, va trigger rebuild catalog.

### 1.2 Dac ta Input/Output

```
INPUT:
  - source_name: string    # ten project goc, vd: "superpowers", "gstack", "everything-claude-code"
  - skill_name: string     # ten skill hoac agent, vd: "brainstorming", "code-reviewer"
  - options:
      --force: boolean     # ghi de neu da ton tai (mac dinh: false)
      --type: "skill"|"agent"|"auto"  # loai entry (mac dinh: "auto" = tu dong phat hien)
      --dry-run: boolean   # chi hien thi thao tac, khong thuc hien (mac dinh: false)

OUTPUT:
  - library/skills/{skill_name}/SKILL.md        # (neu la skill)
  - library/skills/{skill_name}/provenance.yaml
  HOAC:
  - library/agents/{skill_name}.md               # (neu la agent)
  - library/agents/{skill_name}.provenance.yaml
  - catalog.json duoc rebuild (trigger tu dong)

EXIT CODES:
  0 = thanh cong
  1 = source khong ton tai
  2 = skill khong tim thay trong source
  3 = ten bi trung trong library (va khong co --force)
  4 = frontmatter khong hop le
  5 = loi he thong (I/O, permission)
```

### 1.3 Pseudocode

```python
#!/usr/bin/env python3
"""import-skill.py -- Import mot skill/agent tu source project vao library."""

import yaml
import hashlib
import shutil
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

# ── Cau hinh ─────────────────────────────────────────────────────────────────
HUB_ROOT = Path("~/Agent_Hub").expanduser()
LIBRARY_DIR = HUB_ROOT / "agent-hub-index" / "library"

# Bang anh xa source -> cac duong dan tim kiem
SOURCE_PATTERNS = {
    "superpowers": {
        "skill": ["{root}/skills/{name}/SKILL.md"],
        "agent": ["{root}/agents/{name}.md"],
    },
    "everything-claude-code": {
        "skill": ["{root}/skills/{name}/SKILL.md"],
        "agent": ["{root}/agents/{name}.md"],
        "command": ["{root}/commands/{name}.md"],
    },
    "gstack": {
        "skill": ["{root}/{name}/SKILL.md"],
    },
    "get-shit-done": {
        "agent": ["{root}/agents/{name}.md"],
        "command": ["{root}/commands/gsd/{name}.md"],
    },
    "openspec": {
        "skill": [
            "{root}/.claude/skills/{name}/SKILL.md",
            "{root}/.opencode/skills/{name}/SKILL.md",
        ],
    },
    "learn-claude-code": {
        "skill": ["{root}/skills/{name}/SKILL.md"],
    },
}

FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n?(.*)', re.DOTALL)

# ── Cac ham phu tro ──────────────────────────────────────────────────────────

def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """
    Doc file markdown, tach YAML frontmatter va body.

    Returns:
        (frontmatter_dict, body_text)
        Neu khong co frontmatter: ({}, full_text)

    Raises:
        ValueError: neu YAML khong parse duoc
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"YAML frontmatter khong hop le: {e}")

    return fm, match.group(2)


def compute_file_hash(path: Path) -> str:
    """Tinh SHA-256 hash cua file de theo doi thay doi."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def validate_frontmatter(fm: dict, entry_type: str) -> list[str]:
    """
    Kiem tra frontmatter co du cac truong bat buoc.

    Returns:
        Danh sach loi (rong = hop le)
    """
    errors = []

    # Truong bat buoc cho moi loai
    if not fm.get("name"):
        errors.append("Thieu truong 'name' trong frontmatter")

    if not fm.get("description"):
        errors.append("Thieu truong 'description' trong frontmatter")

    # Kiem tra kieu du lieu
    name = fm.get("name", "")
    if name and not re.match(r'^[a-z][a-z0-9-]*$', str(name)):
        errors.append(
            f"Ten '{name}' khong hop le. "
            f"Chi chap nhan: chu thuong, so, dau gach ngang. Bat dau bang chu."
        )

    # Kiem tra description khong phai la dict (loi YAML phoi bien)
    desc = fm.get("description")
    if isinstance(desc, dict):
        errors.append("Truong 'description' la object, can phai la string")

    return errors


def locate_source_file(source_name: str, skill_name: str) -> tuple[Path, str] | None:
    """
    Tim file goc trong source project.

    Thu tu tim kiem:
      1. Skill patterns (SKILL.md trong thu muc)
      2. Agent patterns (.md file)
      3. Command patterns (.md file)

    Returns:
        (path, detected_type) hoac None neu khong tim thay

    Do phuc tap: O(P) voi P = so luong patterns cua source (thuong la 2-4)
    """
    if source_name not in SOURCE_PATTERNS:
        return None

    patterns = SOURCE_PATTERNS[source_name]
    root = HUB_ROOT / source_name

    # Truong hop dac biet: openspec dung HUB_ROOT lam root
    if source_name == "openspec":
        root = HUB_ROOT

    if not root.exists():
        return None

    # Thu tung loai theo thu tu uu tien: skill > agent > command
    for entry_type in ["skill", "agent", "command"]:
        if entry_type not in patterns:
            continue

        for pattern_template in patterns[entry_type]:
            candidate = Path(
                pattern_template.format(root=root, name=skill_name)
            )
            if candidate.exists() and candidate.is_file():
                return candidate, entry_type

    return None


def create_provenance(
    source_name: str,
    source_path: Path,
    source_root: Path,
    file_hash: str,
) -> dict:
    """Tao du lieu provenance de luu vao provenance.yaml."""
    return {
        "source_project": source_name,
        "source_path": str(source_path.relative_to(source_root)),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "imported_by": "auto",  # hoac doc tu env/git config
        "original_hash": file_hash,
        "library_version": 1,
    }


# ── Thuat toan chinh ─────────────────────────────────────────────────────────

def import_skill(
    source_name: str,
    skill_name: str,
    force: bool = False,
    entry_type_hint: str = "auto",
    dry_run: bool = False,
) -> int:
    """
    Thuat toan import chinh.

    Do phuc tap thoi gian: O(P + F)
      - P = so patterns can kiem tra (2-6)
      - F = kich thuoc file (de doc + hash)

    Do phuc tap khong gian: O(F)
      - F = kich thuoc file can copy
    """

    # ── Buoc 1: Kiem tra source ton tai ──────────────────────────────────────
    if source_name not in SOURCE_PATTERNS:
        print(f"LOI: Source '{source_name}' khong ton tai.", file=sys.stderr)
        print(f"  Cac source hop le: {', '.join(SOURCE_PATTERNS.keys())}")
        return 1  # EXIT_SOURCE_NOT_FOUND

    # ── Buoc 2: Tim file goc ────────────────────────────────────────────────
    result = locate_source_file(source_name, skill_name)

    if result is None:
        print(
            f"LOI: Khong tim thay '{skill_name}' trong source '{source_name}'.",
            file=sys.stderr,
        )
        # Goi y: liet ke cac skill co san
        print(f"  Goi y: Kiem tra lai ten skill hoac chay 'list-skills {source_name}'")
        return 2  # EXIT_SKILL_NOT_FOUND

    source_path, detected_type = result

    # Neu user chi dinh type, dung type do; neu khong, dung detected_type
    if entry_type_hint != "auto":
        if entry_type_hint != detected_type:
            print(
                f"CANH BAO: File duoc phat hien la '{detected_type}' "
                f"nhung ban chi dinh '{entry_type_hint}'. Dung '{detected_type}'."
            )
        # Van dung detected_type vi no dua tren vi tri file thuc te

    entry_type = detected_type

    # ── Buoc 3: Parse va validate frontmatter ────────────────────────────────
    try:
        fm, body = parse_frontmatter(source_path)
    except ValueError as e:
        print(f"LOI: {e}", file=sys.stderr)
        return 4  # EXIT_INVALID_FRONTMATTER

    if not fm:
        print(
            f"CANH BAO: File '{source_path}' khong co YAML frontmatter. "
            f"Se tao frontmatter mac dinh."
        )
        fm = {
            "name": skill_name,
            "description": f"Imported from {source_name}",
        }

    errors = validate_frontmatter(fm, entry_type)
    if errors:
        print(f"LOI: Frontmatter khong hop le:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 4  # EXIT_INVALID_FRONTMATTER

    # ── Buoc 4: Kiem tra trung ten trong library ─────────────────────────────
    if entry_type == "skill":
        target_dir = LIBRARY_DIR / "skills" / skill_name
        target_file = target_dir / "SKILL.md"
        provenance_file = target_dir / "provenance.yaml"
    elif entry_type == "agent":
        target_dir = LIBRARY_DIR / "agents"
        target_file = target_dir / f"{skill_name}.md"
        provenance_file = target_dir / f"{skill_name}.provenance.yaml"
    else:  # command -- luu nhu skill
        target_dir = LIBRARY_DIR / "skills" / skill_name
        target_file = target_dir / "SKILL.md"
        provenance_file = target_dir / "provenance.yaml"

    if target_file.exists() and not force:
        print(
            f"LOI: '{skill_name}' da ton tai trong library tai {target_file}.",
            file=sys.stderr,
        )
        print(f"  Dung --force de ghi de.")
        return 3  # EXIT_NAME_CONFLICT

    already_exists = target_file.exists()

    # ── Buoc 5: Tinh hash file goc ──────────────────────────────────────────
    file_hash = compute_file_hash(source_path)

    # ── Buoc 6: Thuc hien copy (neu khong phai dry-run) ─────────────────────
    if dry_run:
        action = "GHI DE" if already_exists else "TAO MOI"
        print(f"[DRY RUN] Se {action}:")
        print(f"  Nguon:  {source_path}")
        print(f"  Dich:   {target_file}")
        print(f"  Prov:   {provenance_file}")
        print(f"  Type:   {entry_type}")
        print(f"  Hash:   {file_hash}")
        return 0

    # Tao thu muc neu chua ton tai
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy file chinh
    if entry_type == "skill":
        # Copy toan bo thu muc skill (co the co file phu nhu spec, scripts)
        source_skill_dir = source_path.parent
        for item in source_skill_dir.iterdir():
            if item.name == "provenance.yaml":
                continue  # khong copy provenance cu
            dest = target_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
    else:
        # Agent/command: chi copy file .md
        shutil.copy2(source_path, target_file)

    # ── Buoc 7: Tao provenance.yaml ─────────────────────────────────────────
    source_root = HUB_ROOT / source_name
    if source_name == "openspec":
        source_root = HUB_ROOT

    provenance = create_provenance(source_name, source_path, source_root, file_hash)

    # Neu dang ghi de, tang library_version
    if already_exists and provenance_file.exists():
        try:
            old_prov = yaml.safe_load(provenance_file.read_text())
            provenance["library_version"] = old_prov.get("library_version", 0) + 1
            provenance["previous_hash"] = old_prov.get("original_hash")
        except Exception:
            pass  # Neu doc provenance cu loi, bat dau lai tu version 1

    with open(provenance_file, "w", encoding="utf-8") as f:
        yaml.dump(provenance, f, default_flow_style=False, allow_unicode=True)

    # ── Buoc 8: Trigger catalog rebuild ──────────────────────────────────────
    print(f"{'Ghi de' if already_exists else 'Import'} thanh cong: {skill_name}")
    print(f"  Type:   {entry_type}")
    print(f"  Nguon:  {source_name}:{source_path.name}")
    print(f"  Dich:   {target_file}")

    # Goi build-catalog.py
    import subprocess
    result = subprocess.run(
        [sys.executable, str(HUB_ROOT / "agent-hub-index" / "build-catalog.py")],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("  Catalog rebuild: OK")
    else:
        print(f"  CANH BAO: Catalog rebuild that bai: {result.stderr[:200]}")

    return 0


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Import skill/agent vao library")
    parser.add_argument("source_name", help="Ten source project")
    parser.add_argument("skill_name", help="Ten skill hoac agent")
    parser.add_argument("--force", action="store_true", help="Ghi de neu da ton tai")
    parser.add_argument("--type", dest="entry_type", default="auto",
                        choices=["skill", "agent", "auto"])
    parser.add_argument("--dry-run", action="store_true", help="Chi hien thi, khong lam")
    args = parser.parse_args()

    sys.exit(import_skill(
        args.source_name, args.skill_name,
        force=args.force,
        entry_type_hint=args.entry_type,
        dry_run=args.dry_run,
    ))
```

### 1.4 Do phuc tap

| Metric | Gia tri | Giai thich |
|--------|---------|------------|
| Thoi gian | O(P + F) | P = so pattern tim kiem (2-6), F = kich thuoc file |
| Khong gian | O(F) | Luu tru noi dung file trong bo nho khi copy |
| I/O | 2-3 file doc, 2-3 file ghi | Doc source, ghi target + provenance |

### 1.5 Cac truong hop dac biet (Edge Cases)

| Truong hop | Xu ly |
|------------|-------|
| Source project khong ton tai tren disk | Tra ve exit code 1 voi thong bao ro rang |
| Skill co ten nhung frontmatter rong | Tao frontmatter mac dinh voi name + description co ban |
| Frontmatter co `description` la dict (loi YAML) | Bao loi cu the, exit code 4 |
| Ten skill chua ky tu dac biet (VD: `my skill!`) | Validation tu choi, chi chap nhan `[a-z][a-z0-9-]*` |
| Skill da ton tai nhung tu source khac | Bao loi name conflict; user dung `--force` de ghi de |
| Skill directory co file phu (scripts/, spec.md) | Copy toan bo directory, khong chi SKILL.md |
| provenance.yaml cu da ton tai | Tang `library_version`, luu `previous_hash` |
| Quyen ghi bi tu choi (permission denied) | Exception duoc bat, exit code 5 |
| File goc bi xoa giua qua trinh import | `shutil.copy2` raise exception, exit code 5 |

### 1.6 Vi du minh hoa

**Vi du 1: Import skill thanh cong**

```bash
$ python import-skill.py superpowers brainstorming

# Buoc noi bo:
# 1. Tim: ~/Agent_Hub/superpowers/skills/brainstorming/SKILL.md  -> TIM THAY
# 2. Parse frontmatter: name="brainstorming", description="You MUST use this..."
# 3. Validate: OK (name hop le, description co)
# 4. Kiem tra: library/skills/brainstorming/ chua ton tai
# 5. Hash: sha256:a1b2c3...
# 6. Copy: skills/brainstorming/ -> library/skills/brainstorming/
#    Files copied: SKILL.md, spec-document-reviewer-prompt.md, visual-companion.md, scripts/
# 7. Tao: library/skills/brainstorming/provenance.yaml
# 8. Chay: build-catalog.py

Import thanh cong: brainstorming
  Type:   skill
  Nguon:  superpowers:SKILL.md
  Dich:   library/skills/brainstorming/SKILL.md
  Catalog rebuild: OK
```

**Vi du 2: Name conflict**

```bash
$ python import-skill.py gstack brainstorming
LOI: 'brainstorming' da ton tai trong library tai library/skills/brainstorming/SKILL.md.
  Dung --force de ghi de.

$ python import-skill.py gstack brainstorming --force
Ghi de thanh cong: brainstorming
  Type:   skill
  Nguon:  gstack:SKILL.md
  Dich:   library/skills/brainstorming/SKILL.md
  Catalog rebuild: OK
```

**Vi du 3: Dry run**

```bash
$ python import-skill.py superpowers systematic-debugging --dry-run
[DRY RUN] Se TAO MOI:
  Nguon:  $HOME/Agent_Hub/superpowers/skills/systematic-debugging/SKILL.md
  Dich:   library/skills/systematic-debugging/SKILL.md
  Prov:   library/skills/systematic-debugging/provenance.yaml
  Type:   skill
  Hash:   sha256:d4e5f6...
```

---

## 2. Thuat toan Build Catalog (build-catalog.py)

### 2.1 Mo ta

Thuat toan quet toan bo thu vien (`library/`), doc frontmatter + provenance + enrichment data tu tung entry, suy luan metadata (domains, technologies, phases), va tao ra file `catalog.json` thong nhat.

Day la buoc "lam giau" (enrichment) -- bien du lieu tho tu cac file markdown thanh metadata co cau truc de Librarian agent co the tim kiem va recommend hieu qua.

### 2.2 Dac ta Input/Output

```
INPUT:
  - library/skills/*/SKILL.md          # Tat ca skill files
  - library/skills/*/provenance.yaml   # Provenance cho moi skill
  - library/skills/*/enrichment.yaml   # (tuy chon) Metadata bo sung tu curator
  - library/agents/*.md                # Tat ca agent files
  - library/agents/*.provenance.yaml   # Provenance cho moi agent
  - library/agents/*.enrichment.yaml   # (tuy chon)
  - domain-keywords.json               # Bang tu khoa cho inference
  - collections/*.yaml                 # (tuy chon) Dinh nghia collection
  - stacks/*.yaml                      # (tuy chon) Dinh nghia stack

OUTPUT:
  - catalog.json                       # File catalog chinh
    {
      version: number,
      builtAt: ISO8601 string,
      totalEntries: number,
      entries: CatalogEntry[]
    }

EXIT CODES:
  0 = thanh cong
  1 = library/ khong ton tai
  2 = khong co entry nao hop le
  3 = loi validation (use_with ref khong ton tai, v.v.)
```

### 2.3 Cau truc CatalogEntry

```typescript
interface CatalogEntry {
  // === Thong tin co ban (tu frontmatter) ===
  id: string;                    // unique, vd: "brainstorming"
  name: string;                  // ten hien thi
  type: "skill" | "agent";      // loai entry
  description: string;           // mo ta ngan (tu frontmatter)

  // === Nguon goc (tu provenance.yaml) ===
  source: string;                // source project goc
  source_path: string;           // duong dan trong source
  imported_at: string;           // thoi diem import
  library_version: number;       // phien ban trong library

  // === Metadata suy luan (tu keyword extraction) ===
  domains: string[];             // vd: ["planning", "workflow"]
  technologies: string[];        // vd: ["typescript", "react"]
  phases: string[];              // vd: ["planning", "architecture"]

  // === Metadata enriched (tu enrichment.yaml hoac tu dong) ===
  platforms: string[];           // vd: ["claude-code", "cursor"]
  tools: string[];               // cac tool can thiet
  cost: "light"|"medium"|"heavy";
  stability: "experimental"|"beta"|"stable";
  complexity: "beginner"|"intermediate"|"advanced";
  usage_pattern: string;         // vd: "before-implementation", "on-demand"
  project_types: string[];       // vd: ["web-app", "api", "cli"]

  // === Quan he (tu enrichment.yaml) ===
  use_with: string[];            // IDs cua cac skill nen dung cung
  conflicts_with: string[];      // IDs cua cac skill xung dot

  // === Phan loai (tu collections/stacks) ===
  collections: string[];         // vd: ["core-workflow", "testing-suite"]
  stacks: string[];              // vd: ["web-fullstack", "ros2-robotics"]

  // === Tim kiem ===
  relevanceKeywords: string[];   // tu khoa cho full-text search
  curator_notes: string;         // ghi chu tu nguoi quan ly
}
```

### 2.4 Thuat toan Keyword Extraction

Day la thuat toan con duoc dung de suy luan `domains`, `technologies`, `phases` tu noi dung van ban.

```python
# ── Bang tu khoa (doc tu domain-keywords.json) ────────────────────────────

# Moi category la mot dict: { key: [keyword1, keyword2, ...] }
# Vi du:
# DOMAIN_KEYWORDS = {
#   "robotics": ["ros", "ros2", "lidar", "slam", "sensor", ...],
#   "web-frontend": ["react", "vue", "angular", "css", ...],
#   ...
# }

def extract_keywords_from_text(
    text: str,
    keyword_table: dict[str, list[str]],
) -> list[str]:
    """
    Thuat toan keyword extraction.

    CACH HOAT DONG:
    1. Chuyen text thanh lowercase
    2. Voi moi category trong keyword_table:
       a. Kiem tra tung keyword co xuat hien trong text khong
       b. Dung substring matching (khong phai whole-word) de bat ca:
          - "ros2" trong "using ros2 for navigation"
          - "react" trong "reactjs application"
       c. Neu BAT KY keyword nao match -> them category vao ket qua
       d. Dung ngay sau khi tim thay keyword dau tien (early exit per category)
    3. Tra ve danh sach cac category da match

    DO PHUC TAP:
    - Worst case: O(C * K * T)
      C = so categories (~16 cho domains)
      K = so keywords trung binh moi category (~15)
      T = do dai text
    - Best case: O(C * T) khi moi category match keyword dau tien
    - Thuc te: T thuong < 5000 chars, tong ~16*15 = 240 keyword checks
      -> Rat nhanh, < 1ms cho moi entry
    """
    text_lower = text.lower()
    matched = []

    for category_key, keywords in keyword_table.items():
        for kw in keywords:
            if kw in text_lower:
                matched.append(category_key)
                break  # Chi can 1 keyword match la du cho category nay

    return matched


def extract_relevance_keywords(
    text: str,
    keyword_tables: dict,
) -> list[str]:
    """
    Trich xuat cac tu khoa rieng le de ho tro full-text search.

    CACH HOAT DONG:
    1. Tim tat ca cac keyword tu domain/tech/phase tables co trong text
    2. Tach text thanh cac tu don (>= 3 ky tu)
    3. Loc bo stop words
    4. Hop nhat 2 tap va gioi han 60 tu khoa

    MUC DICH:
    - Cho phep Librarian match "pytorch" truc tiep tu query cua user
    - Khong can phai biet "pytorch" thuoc category "ai-ml"
    """
    text_lower = text.lower()
    found = set()

    # Buoc 1: Tim matched keywords tu cac bang
    for table in [
        keyword_tables["DOMAIN_KEYWORDS"],
        keyword_tables["TECH_KEYWORDS"],
        keyword_tables["PHASE_KEYWORDS"],
    ]:
        for key, keywords in table.items():
            for kw in keywords:
                if kw in text_lower:
                    found.add(kw)

    # Buoc 2: Tach tu don
    STOP_WORDS = {
        "use", "when", "the", "for", "and", "with", "all", "any",
        "this", "that", "you", "your", "are", "can", "will", "have",
        "has", "been", "being", "from", "before", "after", "during",
        "while", "used", "using", "must",
    }

    words = re.findall(r'\b[a-z][a-z0-9_-]{2,}\b', text_lower)
    for word in words:
        if word not in STOP_WORDS:
            found.add(word)

    # Buoc 3: Gioi han va sap xep
    return sorted(found)[:60]
```

### 2.5 Thuat toan Scoring (suy luan complexity, cost)

```python
def infer_cost(file_path: Path) -> str:
    """
    Suy luan 'cost' (muc do tai nguyen) dua tren kich thuoc file.

    Logic:
      < 5KB   -> "light"    (skill don gian, nhanh)
      < 20KB  -> "medium"   (skill trung binh)
      >= 20KB -> "heavy"    (skill phuc tap, nhieu buoc)

    Ly do dung kich thuoc file:
    - File lon thuong chua nhieu buoc, nhieu dieu kien
    - Tuong quan tot voi thoi gian AI xu ly
    - Don gian va khong can parse noi dung
    """
    size = file_path.stat().st_size
    if size < 5_000:
        return "light"
    elif size < 20_000:
        return "medium"
    return "heavy"


def infer_complexity(fm: dict, body: str, cost: str) -> str:
    """
    Suy luan 'complexity' dua tren nhieu tin hieu.

    Logic:
      1. Neu frontmatter co 'complexity' -> dung truc tiep
      2. Neu khong, dung tieu chi sau:
         - "beginner": cost=light VA khong co cac tu nhu "advanced", "complex"
         - "advanced": cost=heavy HOAC co "advanced", "expert", "complex architecture"
         - "intermediate": mac dinh cho moi truong hop khac
    """
    # Uu tien gia tri tu enrichment
    if fm.get("complexity"):
        return fm["complexity"]

    body_lower = body.lower()

    advanced_signals = [
        "advanced", "expert", "complex architecture",
        "distributed", "concurrent", "multi-agent",
    ]
    beginner_signals = [
        "simple", "basic", "beginner", "getting started",
        "introduction", "first step",
    ]

    has_advanced = any(s in body_lower for s in advanced_signals)
    has_beginner = any(s in body_lower for s in beginner_signals)

    if has_advanced or cost == "heavy":
        return "advanced"
    if has_beginner and cost == "light":
        return "beginner"
    return "intermediate"


def infer_stability(body: str, source_stability: str) -> str:
    """
    Suy luan do on dinh.

    Logic (uu tien tu tren xuong):
      1. Tim "experimental", "wip", "draft", "prototype" trong body -> "experimental"
      2. Tim "beta", "evolving", "preview" -> "beta"
      3. Mac dinh: lay tu source project (vd: gstack mac dinh la "beta")
    """
    body_lower = body.lower()

    if any(w in body_lower for w in ["experimental", "wip", "draft", "prototype"]):
        return "experimental"
    if any(w in body_lower for w in ["beta", "evolving", "preview"]):
        return "beta"

    return source_stability


def infer_usage_pattern(fm: dict, body: str, entry_type: str) -> str:
    """
    Suy luan cach su dung (usage pattern).

    Categories:
      - "always-on":             Luon duoc load (preamble-tier skills)
      - "before-implementation": Dung truoc khi code
      - "during-implementation": Dung trong khi code
      - "after-implementation":  Dung sau khi code (review, test)
      - "on-demand":             Goi khi can (slash command)
      - "session-hook":          Tu dong chay khi bat dau session
    """
    if fm.get("preamble-tier") or fm.get("preamble_tier"):
        return "always-on"

    body_lower = body.lower()
    name = fm.get("name", "").lower()

    if any(w in name for w in ["plan", "brainstorm", "design", "spec"]):
        return "before-implementation"
    if any(w in name for w in ["review", "test", "verify", "finish"]):
        return "after-implementation"
    if any(w in body_lower for w in ["session start", "hook", "on session"]):
        return "session-hook"
    if entry_type == "command":
        return "on-demand"

    return "during-implementation"
```

### 2.6 Pseudocode chinh

```python
#!/usr/bin/env python3
"""build-catalog.py -- Build catalog.json tu library/."""

import json
import yaml
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# ── Cau hinh ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
LIBRARY_DIR = SCRIPT_DIR / "library"
CATALOG_PATH = SCRIPT_DIR / "catalog.json"
KEYWORDS_PATH = SCRIPT_DIR / "domain-keywords.json"
COLLECTIONS_DIR = SCRIPT_DIR / "collections"
STACKS_DIR = SCRIPT_DIR / "stacks"

FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n?(.*)', re.DOTALL)


def scan_library() -> list[dict]:
    """
    Quet library/ va tra ve danh sach cac entry tho (raw).

    Quet 2 thu muc:
      1. library/skills/*/SKILL.md
      2. library/agents/*.md

    Moi entry bao gom:
      - path: Path den file .md
      - type: "skill" | "agent"
      - dir_name: ten thu muc (cho skill) hoac ten file (cho agent)

    Do phuc tap: O(S + A)
      S = so skill directories
      A = so agent files
    """
    entries = []

    skills_dir = LIBRARY_DIR / "skills"
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                entries.append({
                    "path": skill_file,
                    "type": "skill",
                    "dir_name": skill_dir.name,
                })

    agents_dir = LIBRARY_DIR / "agents"
    if agents_dir.exists():
        for agent_file in sorted(agents_dir.glob("*.md")):
            # Bo qua file provenance va enrichment
            if agent_file.stem.endswith(".provenance") or \
               agent_file.stem.endswith(".enrichment"):
                continue
            entries.append({
                "path": agent_file,
                "type": "agent",
                "dir_name": agent_file.stem,
            })

    return entries


def load_provenance(entry_path: Path, entry_type: str, dir_name: str) -> dict:
    """
    Doc provenance.yaml cho entry.

    Vi tri file:
      - Skill: library/skills/{name}/provenance.yaml
      - Agent: library/agents/{name}.provenance.yaml

    Tra ve dict rong neu file khong ton tai.
    """
    if entry_type == "skill":
        prov_path = entry_path.parent / "provenance.yaml"
    else:
        prov_path = entry_path.parent / f"{dir_name}.provenance.yaml"

    if not prov_path.exists():
        return {}

    try:
        return yaml.safe_load(prov_path.read_text()) or {}
    except Exception:
        return {}


def load_enrichment(entry_path: Path, entry_type: str, dir_name: str) -> dict:
    """
    Doc enrichment.yaml -- metadata bo sung tu curator.

    Vi tri file:
      - Skill: library/skills/{name}/enrichment.yaml
      - Agent: library/agents/{name}.enrichment.yaml

    Enrichment co the chua:
      - use_with: ["writing-plans", "executing-plans"]
      - conflicts_with: ["old-planner"]
      - project_types: ["web-app", "api"]
      - curator_notes: "Ghi chu tu curator..."
      - complexity: "intermediate"
      - usage_pattern: "before-implementation"

    Tra ve dict rong neu file khong ton tai.
    """
    if entry_type == "skill":
        enr_path = entry_path.parent / "enrichment.yaml"
    else:
        enr_path = entry_path.parent / f"{dir_name}.enrichment.yaml"

    if not enr_path.exists():
        return {}

    try:
        return yaml.safe_load(enr_path.read_text()) or {}
    except Exception:
        return {}


def load_collection_membership(collections_dir: Path) -> dict[str, list[str]]:
    """
    Doc tat ca collection YAML va tra ve:
      { entry_id: [collection_name, ...] }

    Format collection YAML:
      name: core-workflow
      description: ...
      entries:
        - brainstorming
        - writing-plans
        - executing-plans
    """
    membership = defaultdict(list)

    if not collections_dir.exists():
        return membership

    for coll_file in collections_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(coll_file.read_text()) or {}
        except Exception:
            continue

        coll_name = data.get("name", coll_file.stem)
        for entry_id in data.get("entries", []):
            membership[entry_id].append(coll_name)

    return membership


def load_stack_membership(stacks_dir: Path) -> dict[str, list[str]]:
    """
    Doc tat ca stack YAML va tra ve:
      { entry_id: [stack_name, ...] }

    Format stack YAML:
      name: web-fullstack
      description: ...
      project_signals:
        technologies: ["typescript", "react", "postgres"]
        domains: ["web-frontend", "web-backend"]
        file_patterns: ["package.json", "tsconfig.json"]
      entries:
        - brainstorming
        - writing-plans
        - test-driven-development
    """
    membership = defaultdict(list)

    if not stacks_dir.exists():
        return membership

    for stack_file in stacks_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(stack_file.read_text()) or {}
        except Exception:
            continue

        stack_name = data.get("name", stack_file.stem)
        for entry_id in data.get("entries", []):
            membership[entry_id].append(stack_name)

    return membership


def build_catalog_entry(
    raw_entry: dict,
    kw_data: dict,
    provenance: dict,
    enrichment: dict,
    collection_membership: dict[str, list[str]],
    stack_membership: dict[str, list[str]],
    source_stability_map: dict[str, str],
) -> dict | None:
    """
    Xay dung mot CatalogEntry day du tu cac nguon du lieu.

    THU TU UU TIEN khi co xung dot:
      1. enrichment.yaml (cao nhat -- curator quyet dinh)
      2. frontmatter (tac gia skill quyet dinh)
      3. suy luan tu dong (thap nhat -- may tinh doan)

    Do phuc tap: O(T) voi T = do dai text (cho keyword extraction)
    """
    path = raw_entry["path"]
    entry_type = raw_entry["type"]
    dir_name = raw_entry["dir_name"]

    # ── Parse frontmatter ────────────────────────────────────────────────
    fm, body = parse_frontmatter(path)

    # ── Thong tin co ban ─────────────────────────────────────────────────
    name = fm.get("name") or dir_name
    name = str(name).strip()
    entry_id = name  # Trong library, ID = name (khong co prefix source)

    description = fm.get("description", "")
    if isinstance(description, dict):
        description = ""
    description = str(description).strip()

    # Fallback: dong dau tien cua body
    if not description:
        for line in body.splitlines():
            line = line.strip().lstrip("#").strip()
            if line and not line.startswith("<!--"):
                description = line[:200]
                break

    # ── Keyword extraction ───────────────────────────────────────────────
    combined_text = f"{name} {description} {body[:3000]}"

    domains = extract_keywords_from_text(combined_text, kw_data["DOMAIN_KEYWORDS"])
    technologies = extract_keywords_from_text(combined_text, kw_data["TECH_KEYWORDS"])
    phases = extract_keywords_from_text(combined_text, kw_data["PHASE_KEYWORDS"])

    # Enrichment override
    if enrichment.get("domains"):
        domains = enrichment["domains"]
    if enrichment.get("technologies"):
        technologies = enrichment["technologies"]
    if enrichment.get("phases"):
        phases = enrichment["phases"]

    # Default phases
    if not phases:
        if entry_type == "agent":
            phases = ["development", "review"]
        else:
            phases = ["development"]

    # ── Platforms ────────────────────────────────────────────────────────
    source = provenance.get("source_project", "unknown")
    platforms = enrichment.get("platforms") or fm.get("platforms") or []
    if not platforms:
        # Mac dinh tu source project
        DEFAULT_PLATFORMS = {
            "superpowers": ["claude-code", "codex", "cursor", "opencode"],
            "everything-claude-code": ["claude-code", "cursor", "opencode", "codex"],
            "gstack": ["claude-code"],
            "get-shit-done": ["claude-code", "codex", "opencode", "cursor", "copilot"],
            "openspec": ["claude-code", "opencode"],
            "learn-claude-code": ["claude-code"],
        }
        platforms = DEFAULT_PLATFORMS.get(source, ["claude-code"])

    # ── Suy luan cac truong con lai ─────────────────────────────────────
    source_stability = source_stability_map.get(source, "stable")
    cost = enrichment.get("cost") or infer_cost(path)
    stability = enrichment.get("stability") or infer_stability(body, source_stability)
    complexity = enrichment.get("complexity") or infer_complexity(fm, body, cost)
    usage_pattern = enrichment.get("usage_pattern") or infer_usage_pattern(fm, body, entry_type)
    project_types = enrichment.get("project_types", [])

    # ── Quan he ──────────────────────────────────────────────────────────
    use_with = enrichment.get("use_with", [])
    conflicts_with = enrichment.get("conflicts_with", [])
    curator_notes = enrichment.get("curator_notes", "")

    # ── Phan loai ────────────────────────────────────────────────────────
    collections = collection_membership.get(entry_id, [])
    stacks = stack_membership.get(entry_id, [])

    # ── Tools va model ───────────────────────────────────────────────────
    tools_raw = fm.get("tools") or fm.get("allowed-tools") or []
    if isinstance(tools_raw, str):
        tools_raw = [t.strip() for t in tools_raw.split(",")]
    tools = [str(t) for t in tools_raw]

    model = fm.get("model")
    if model:
        model = str(model)

    # ── Relevance keywords ───────────────────────────────────────────────
    relevance_keywords = extract_relevance_keywords(combined_text, kw_data)

    return {
        "id": entry_id,
        "name": name,
        "type": entry_type,
        "description": description,
        "source": source,
        "source_path": provenance.get("source_path", ""),
        "imported_at": provenance.get("imported_at", ""),
        "library_version": provenance.get("library_version", 1),
        "domains": sorted(set(domains)),
        "technologies": sorted(set(technologies)),
        "phases": sorted(set(phases)),
        "platforms": sorted(set(str(p) for p in platforms)),
        "tools": tools,
        "model": model,
        "cost": cost,
        "stability": stability,
        "complexity": complexity,
        "usage_pattern": usage_pattern,
        "project_types": sorted(set(project_types)),
        "use_with": use_with,
        "conflicts_with": conflicts_with,
        "collections": sorted(set(collections)),
        "stacks": sorted(set(stacks)),
        "relevanceKeywords": relevance_keywords,
        "curator_notes": curator_notes,
    }


def validate_catalog(entries: list[dict]) -> list[str]:
    """
    Kiem tra tinh nhat quan cua catalog sau khi build.

    KIEM TRA:
    1. Khong co ID trung lap
    2. Moi use_with reference phai tro den entry ton tai
    3. Moi conflicts_with reference phai tro den entry ton tai

    Returns:
        Danh sach loi (rong = hop le)
    """
    errors = []
    all_ids = set()

    # Kiem tra ID trung lap
    for entry in entries:
        if entry["id"] in all_ids:
            errors.append(f"ID trung lap: '{entry['id']}'")
        all_ids.add(entry["id"])

    # Kiem tra references
    for entry in entries:
        for ref_id in entry.get("use_with", []):
            if ref_id not in all_ids:
                errors.append(
                    f"Entry '{entry['id']}' co use_with='{ref_id}' "
                    f"nhung '{ref_id}' khong ton tai trong catalog"
                )

        for ref_id in entry.get("conflicts_with", []):
            if ref_id not in all_ids:
                errors.append(
                    f"Entry '{entry['id']}' co conflicts_with='{ref_id}' "
                    f"nhung '{ref_id}' khong ton tai trong catalog"
                )

    return errors


def build_catalog() -> int:
    """
    Thuat toan build catalog chinh.

    Do phuc tap tong:
      O(N * T + C + S)
      N = so entry trong library (~50)
      T = kich thuoc text trung binh (~5KB)
      C = so collection files
      S = so stack files

    Thuc te: < 500ms cho 50 entries
    """

    # ── Buoc 1: Kiem tra library/ ton tai ────────────────────────────────
    if not LIBRARY_DIR.exists():
        print(f"LOI: library/ khong ton tai tai {LIBRARY_DIR}", file=sys.stderr)
        return 1

    # ── Buoc 2: Load du lieu tham chieu ──────────────────────────────────
    kw_data = json.loads(KEYWORDS_PATH.read_text())
    collection_membership = load_collection_membership(COLLECTIONS_DIR)
    stack_membership = load_stack_membership(STACKS_DIR)

    source_stability_map = {
        "superpowers": "stable",
        "everything-claude-code": "stable",
        "gstack": "beta",
        "get-shit-done": "stable",
        "openspec": "stable",
        "learn-claude-code": "stable",
    }

    # ── Buoc 3: Quet library/ ────────────────────────────────────────────
    raw_entries = scan_library()

    if not raw_entries:
        print("LOI: Khong tim thay entry nao trong library/", file=sys.stderr)
        return 2

    print(f"Tim thay {len(raw_entries)} entries trong library/")

    # ── Buoc 4: Build tung entry ─────────────────────────────────────────
    catalog_entries = []

    for raw in raw_entries:
        # Load provenance
        provenance = load_provenance(
            raw["path"], raw["type"], raw["dir_name"]
        )

        # Load enrichment
        enrichment = load_enrichment(
            raw["path"], raw["type"], raw["dir_name"]
        )

        # Build entry
        entry = build_catalog_entry(
            raw, kw_data, provenance, enrichment,
            collection_membership, stack_membership,
            source_stability_map,
        )

        if entry is not None:
            catalog_entries.append(entry)
            print(f"  + {entry['id']} ({entry['type']}, {entry['source']})")

    # ── Buoc 5: Validate ─────────────────────────────────────────────────
    errors = validate_catalog(catalog_entries)

    if errors:
        print(f"\nCACH BAO: {len(errors)} van de validation:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        # Khong that bai -- chi canh bao (de curator sua)

    # ── Buoc 6: Ghi catalog.json ─────────────────────────────────────────
    catalog = {
        "version": 1,
        "builtAt": datetime.now(timezone.utc).isoformat(),
        "totalEntries": len(catalog_entries),
        "entries": catalog_entries,
    }

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    size_kb = CATALOG_PATH.stat().st_size / 1024
    print(f"\nGhi catalog.json: {len(catalog_entries)} entries, {size_kb:.1f} KB")

    return 0


if __name__ == "__main__":
    sys.exit(build_catalog())
```

### 2.7 Do phuc tap

| Giai doan | Do phuc tap | Chi tiet |
|-----------|-------------|----------|
| Quet library/ | O(N) | N = so entries |
| Load keywords | O(1) | Doc 1 file JSON |
| Load collections/stacks | O(C + S) | C = collection files, S = stack files |
| Parse frontmatter (moi entry) | O(T) | T = kich thuoc file |
| Keyword extraction (moi entry) | O(K * T) | K = tong so keywords (~200) |
| Relevance keywords (moi entry) | O(K * T + W) | W = so tu trong text |
| Validation | O(N * R) | R = so references trung binh moi entry |
| **Tong** | **O(N * K * T)** | Thuc te < 500ms cho N=50 |

### 2.8 Cac truong hop dac biet

| Truong hop | Xu ly |
|------------|-------|
| library/ rong (chua import gi) | Exit code 2, thong bao ro |
| Skill co SKILL.md nhung thieu provenance.yaml | Van build duoc, provenance fields se la rong |
| enrichment.yaml co loi YAML syntax | Bo qua enrichment, dung suy luan tu dong |
| Hai skill co cung ten | Bao loi duplicate ID trong validation |
| use_with tro den skill chua import | Canh bao trong validation (khong fail) |
| collection.yaml reference skill khong ton tai | Canh bao (khong fail), collection van duoc load |
| File .md khong co frontmatter | Dung dir_name lam name, dong dau lam description |
| Body text qua lon (> 100KB) | Chi doc 3000 ky tu dau cho keyword extraction |

### 2.9 Vi du minh hoa

**Input: library/ co 3 entries**

```
library/
+-- skills/
|   +-- brainstorming/
|   |   +-- SKILL.md             # frontmatter: name, description
|   |   +-- provenance.yaml      # source: superpowers
|   |   +-- enrichment.yaml      # use_with: [writing-plans]
|   +-- systematic-debugging/
|       +-- SKILL.md
|       +-- provenance.yaml      # source: superpowers
+-- agents/
    +-- code-reviewer.md
    +-- code-reviewer.provenance.yaml  # source: superpowers
```

**Output: catalog.json (rut gon)**

```json
{
  "version": 1,
  "builtAt": "2026-03-30T12:00:00Z",
  "totalEntries": 3,
  "entries": [
    {
      "id": "brainstorming",
      "name": "brainstorming",
      "type": "skill",
      "description": "You MUST use this before any creative work...",
      "source": "superpowers",
      "domains": ["design", "planning", "workflow"],
      "technologies": ["typescript"],
      "phases": ["architecture", "planning"],
      "complexity": "intermediate",
      "usage_pattern": "before-implementation",
      "use_with": ["writing-plans"],
      "conflicts_with": [],
      "collections": ["core-workflow"],
      "stacks": ["web-fullstack"]
    },
    {
      "id": "systematic-debugging",
      "name": "systematic-debugging",
      "type": "skill",
      "source": "superpowers",
      "domains": ["debugging"],
      "phases": ["debugging"],
      "use_with": [],
      "collections": ["core-workflow"],
      "stacks": ["web-fullstack", "ros2-robotics"]
    },
    {
      "id": "code-reviewer",
      "name": "code-reviewer",
      "type": "agent",
      "source": "superpowers",
      "domains": ["workflow"],
      "phases": ["review"],
      "usage_pattern": "after-implementation",
      "use_with": [],
      "collections": [],
      "stacks": []
    }
  ]
}
```

---

## 3. Thuat toan Stack Matching

### 3.1 Mo ta

Thuat toan nay duoc **Librarian agent** su dung de tu dong xac dinh stack phu hop nhat cho mot project. No phan tich cac "tin hieu" (signals) tu project files hoac mo ta project, roi so khop voi cac stack da dinh nghia.

**Stack** la mot nhom skills duoc pre-configured cho mot loai project cu the. Vi du:
- `web-fullstack`: brainstorming + writing-plans + test-driven-development + ...
- `ros2-robotics`: brainstorming + systematic-debugging + ...

### 3.2 Dac ta Input/Output

```
INPUT (mot trong hai):
  Option A - Natural language:
    project_description: string
    # Vi du: "ROS2 robot voi LiDAR va camera de mapping"

  Option B - Project files (tu dong scan):
    project_path: Path
    # Se doc cac file sau (neu co):
    #   - CLAUDE.md / .claude/settings.json  (project config)
    #   - package.json                        (Node.js)
    #   - pyproject.toml / setup.py           (Python)
    #   - CMakeLists.txt                      (C++/CMake)
    #   - Cargo.toml                          (Rust)
    #   - go.mod                              (Go)
    #   - build.gradle / pom.xml              (Java)
    #   - pubspec.yaml                        (Flutter)
    #   - *.sln / *.csproj                    (C#/.NET)

OUTPUT:
  ranked_stacks: list[StackMatch]
    # 1-3 stacks, sap xep theo diem giam dan

  StackMatch:
    stack_name: string          # "web-fullstack"
    score: float                # 0.0 - 100.0
    match_details:
      tech_matches: list[str]   # ["typescript", "react", "postgres"]
      domain_matches: list[str] # ["web-frontend", "web-backend"]
      file_matches: list[str]   # ["package.json", "tsconfig.json"]
    explanation: string         # "Project co package.json voi React + Postgres..."
```

### 3.3 Dinh nghia Stack

```yaml
# stacks/web-fullstack.yaml
name: web-fullstack
description: "Stack cho du an web full-stack voi frontend + backend + database"
project_signals:
  technologies:
    - typescript
    - javascript
    - react
    - postgres
    - docker
  domains:
    - web-frontend
    - web-backend
    - data
    - devops
  file_patterns:
    - package.json
    - tsconfig.json
    - docker-compose.yml
    - .env
    - prisma/schema.prisma
    - next.config.*
    - vite.config.*
entries:
  - brainstorming
  - writing-plans
  - executing-plans
  - test-driven-development
  - systematic-debugging
  - finishing-a-development-branch
  - verification-before-completion
```

```yaml
# stacks/ros2-robotics.yaml
name: ros2-robotics
description: "Stack cho du an ROS2 robotics"
project_signals:
  technologies:
    - ros2
    - cpp
    - python
    - docker
  domains:
    - robotics
    - devops
    - testing
  file_patterns:
    - CMakeLists.txt
    - package.xml
    - colcon.meta
    - launch/*.py
    - config/*.yaml
    - urdf/*.xacro
entries:
  - brainstorming
  - writing-plans
  - systematic-debugging
  - test-driven-development
```

### 3.4 Thuat toan Signal Extraction

```python
def extract_signals_from_description(description: str) -> dict:
    """
    Trich xuat tin hieu tu mo ta bang ngon ngu tu nhien.

    Returns:
        {
            "technologies": ["ros2", "cpp", "python"],
            "domains": ["robotics", "devops"],
            "file_patterns": []  # khong co tu description
        }
    """
    desc_lower = description.lower()

    technologies = []
    for tech, keywords in TECH_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            technologies.append(tech)

    domains = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            domains.append(domain)

    return {
        "technologies": technologies,
        "domains": domains,
        "file_patterns": [],  # Khong the suy luan file patterns tu text
    }


def extract_signals_from_project(project_path: Path) -> dict:
    """
    Trich xuat tin hieu tu project files thuc te.

    CHIEN LUOC QUET:
    Quet cac file cu the (khong quet toan bo project) de giu toc do nhanh.

    Do phuc tap: O(F * D)
      F = so file can kiem tra (~15)
      D = kich thuoc trung binh cua noi dung file can parse (~5KB)
    """
    signals = {
        "technologies": set(),
        "domains": set(),
        "file_patterns": set(),
    }

    # ── 1. Kiem tra su ton tai cua cac file dac trung ────────────────────
    FILE_TO_TECH = {
        "package.json": "typescript",    # hoac javascript, kiem tra noi dung
        "tsconfig.json": "typescript",
        "pyproject.toml": "python",
        "setup.py": "python",
        "requirements.txt": "python",
        "CMakeLists.txt": "cpp",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "build.gradle": "java",
        "pom.xml": "java",
        "pubspec.yaml": "dart",         # Flutter/Dart
        "Gemfile": "ruby",
        "Dockerfile": "docker",
        "docker-compose.yml": "docker",
        "docker-compose.yaml": "docker",
    }

    for filename, tech in FILE_TO_TECH.items():
        file_path = project_path / filename
        if file_path.exists():
            signals["technologies"].add(tech)
            signals["file_patterns"].add(filename)

    # ── 2. Kiem tra file patterns dac biet (glob) ────────────────────────
    GLOB_PATTERNS = {
        "*.sln": "csharp",
        "*.csproj": "csharp",
        "launch/*.py": "ros2",
        "*.xacro": "ros2",
    }

    for pattern, tech in GLOB_PATTERNS.items():
        if list(project_path.glob(pattern)):
            signals["technologies"].add(tech)
            signals["file_patterns"].add(pattern)

    # ── 3. Parse package.json de lay chi tiet ────────────────────────────
    pkg_json = project_path / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            all_deps = {}
            all_deps.update(pkg.get("dependencies", {}))
            all_deps.update(pkg.get("devDependencies", {}))

            # Map dependencies -> technologies
            DEP_TO_TECH = {
                "react": "react",
                "next": "react",
                "vue": "vue",
                "angular": "angular",
                "express": "typescript",
                "fastify": "typescript",
                "prisma": "postgres",
                "@prisma/client": "postgres",
                "pg": "postgres",
                "mongoose": "mongodb",
                "redis": "redis",
                "jest": None,     # testing, khong phai tech
                "vitest": None,
                "playwright": None,
            }

            # Map dependencies -> domains
            DEP_TO_DOMAIN = {
                "react": "web-frontend",
                "next": "web-frontend",
                "vue": "web-frontend",
                "express": "web-backend",
                "fastify": "web-backend",
                "prisma": "data",
                "@prisma/client": "data",
                "pg": "data",
                "mongoose": "data",
                "jest": "testing",
                "vitest": "testing",
                "playwright": "testing",
            }

            for dep in all_deps:
                dep_base = dep.split("/")[-1]  # @prisma/client -> client
                # Kiem tra ten dep (khong phai version)
                for dep_key, tech in DEP_TO_TECH.items():
                    if dep_key in dep and tech:
                        signals["technologies"].add(tech)
                for dep_key, domain in DEP_TO_DOMAIN.items():
                    if dep_key in dep and domain:
                        signals["domains"].add(domain)

        except (json.JSONDecodeError, Exception):
            pass  # package.json khong doc duoc, bo qua

    # ── 4. Parse CMakeLists.txt de phat hien ROS2 ───────────────────────
    cmake_file = project_path / "CMakeLists.txt"
    if cmake_file.exists():
        try:
            cmake_content = cmake_file.read_text().lower()

            ros2_indicators = [
                "find_package(ament",
                "find_package(rclcpp",
                "find_package(rclpy",
                "ament_package",
                "ament_cmake",
                "rosidl_generate",
            ]

            if any(ind in cmake_content for ind in ros2_indicators):
                signals["technologies"].add("ros2")
                signals["domains"].add("robotics")
        except Exception:
            pass

    # ── 5. Parse package.xml (ROS2) ──────────────────────────────────────
    pkg_xml = project_path / "package.xml"
    if pkg_xml.exists():
        signals["technologies"].add("ros2")
        signals["domains"].add("robotics")
        signals["file_patterns"].add("package.xml")

    # ── 6. Parse pyproject.toml ──────────────────────────────────────────
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text().lower()
            if "django" in content:
                signals["domains"].add("web-backend")
            if "fastapi" in content:
                signals["domains"].add("web-backend")
            if "pytorch" in content or "torch" in content:
                signals["technologies"].add("pytorch")
                signals["domains"].add("ai-ml")
            if "pytest" in content:
                signals["domains"].add("testing")
        except Exception:
            pass

    # ── 7. Suy luan domain tu technologies ───────────────────────────────
    TECH_TO_DOMAIN = {
        "react": "web-frontend",
        "ros2": "robotics",
        "pytorch": "ai-ml",
        "docker": "devops",
        "postgres": "data",
        "android": "mobile",
        "swift": "mobile",
        "kotlin": "mobile",
        "dart": "mobile",
    }

    for tech in list(signals["technologies"]):
        if tech in TECH_TO_DOMAIN:
            signals["domains"].add(TECH_TO_DOMAIN[tech])

    return {
        "technologies": list(signals["technologies"]),
        "domains": list(signals["domains"]),
        "file_patterns": list(signals["file_patterns"]),
    }
```

### 3.5 Thuật toán Scoring (Dành cho Tự động Matching)

> **Lưu ý Kiến trúc:**
> Đây là thuật toán "Stack Matching" được sử dụng chủ yếu bởi **session hook** để tự động gợi ý stack khi mở project mới.
> Thuật toán này dựa trên việc parse cấu trúc file của project.
> Đối với AI Librarian (prompt-based interactive matching), agent sử dụng hệ thống tính điểm riêng biệt dựa trên keyword & semantic match (xem doc 05).

```python
def score_stack_match(
    stack: dict,
    project_signals: dict,
) -> tuple[float, dict]:
    """
    Tinh diem so khop giua 1 stack va project signals.

    CONG THUC TINH DIEM:

      score = (tech_score * 0.30) + (domain_score * 0.20) + (file_score * 0.50)

    CHI TIET:

    1. Technology Score (trong so 30%):
       - Dem so technologies trung nhau giua project va stack
       - Chia cho max(so tech cua stack, 1)
       - Nhan 100 de normalize

       tech_score = (so_tech_match / tong_tech_stack) * 100

       Vi du: project co [typescript, react, docker]
              stack can [typescript, react, postgres, docker]
              -> match 3/4 = 75.0 -> tech_score = 75.0

    2. Domain Score (trong so 20%):
       - Tuong tu technology score
       - Dem so domains trung nhau

       domain_score = (so_domain_match / tong_domain_stack) * 100

    3. File Pattern Score (trong so 50%):
       - TRONG SO CAO NHAT vi file patterns la tin hieu chinh xac nhat
       - File co mat = chac chan la loai project do
       - Dung glob matching cho patterns co wildcard

       file_score = (so_file_match / tong_file_patterns_stack) * 100

    TRONG SO:
      - File patterns: 50% -- tin hieu chinh xac nhat (file ton tai = su that)
      - Technologies:  30% -- tin hieu manh (tu dependencies)
      - Domains:       20% -- tin hieu yeu hon (co the suy luan sai)

    Returns:
        (score, match_details)
        score: 0.0 - 100.0
    """
    stack_signals = stack.get("project_signals", {})

    # ── Technology matching ──────────────────────────────────────────────
    stack_techs = set(stack_signals.get("technologies", []))
    project_techs = set(project_signals.get("technologies", []))

    tech_matches = list(stack_techs & project_techs)
    tech_score = (len(tech_matches) / max(len(stack_techs), 1)) * 100

    # ── Domain matching ──────────────────────────────────────────────────
    stack_domains = set(stack_signals.get("domains", []))
    project_domains = set(project_signals.get("domains", []))

    domain_matches = list(stack_domains & project_domains)
    domain_score = (len(domain_matches) / max(len(stack_domains), 1)) * 100

    # ── File pattern matching ────────────────────────────────────────────
    stack_file_patterns = stack_signals.get("file_patterns", [])
    project_file_patterns = set(project_signals.get("file_patterns", []))

    file_matches = []
    for pattern in stack_file_patterns:
        # Exact match hoac glob match
        if pattern in project_file_patterns:
            file_matches.append(pattern)
        elif "*" in pattern:
            # Glob: kiem tra xem project co file nao match pattern khong
            # Da duoc resolve thanh ten file cu the trong extract_signals
            for pf in project_file_patterns:
                if _glob_match(pattern, pf):
                    file_matches.append(pattern)
                    break

    file_score = (len(file_matches) / max(len(stack_file_patterns), 1)) * 100

    # ── Tinh diem tong ───────────────────────────────────────────────────
    WEIGHT_TECH = 0.30
    WEIGHT_DOMAIN = 0.20
    WEIGHT_FILE = 0.50

    total_score = (
        tech_score * WEIGHT_TECH +
        domain_score * WEIGHT_DOMAIN +
        file_score * WEIGHT_FILE
    )

    match_details = {
        "tech_matches": sorted(tech_matches),
        "tech_score": round(tech_score, 1),
        "domain_matches": sorted(domain_matches),
        "domain_score": round(domain_score, 1),
        "file_matches": sorted(file_matches),
        "file_score": round(file_score, 1),
        "weights": {
            "technology": WEIGHT_TECH,
            "domain": WEIGHT_DOMAIN,
            "file_pattern": WEIGHT_FILE,
        },
    }

    return round(total_score, 2), match_details


def _glob_match(pattern: str, filename: str) -> bool:
    """
    Don gian hoa glob matching.
    "*.json" matches "package.json"
    "launch/*.py" matches "launch/nav.py"
    """
    import fnmatch
    return fnmatch.fnmatch(filename, pattern)
```

### 3.6 Thuat toan Tie-Breaking

```python
def rank_stacks(
    stacks: list[dict],
    project_signals: dict,
    top_k: int = 3,
) -> list[dict]:
    """
    Xep hang tat ca stacks va tra ve top 1-3.

    QUY TAC TIE-BREAKING (khi 2 stack co cung diem):

    1. Uu tien stack co nhieu file_matches hon
       Ly do: file patterns la tin hieu chinh xac nhat

    2. Uu tien stack co nhieu tech_matches hon
       Ly do: technologies la tin hieu manh thu 2

    3. Uu tien stack co it entries hon
       Ly do: stack nho hon = chuyen biet hon = phu hop hon

    4. Uu tien theo thu tu alphabet cua ten stack
       Ly do: Dam bao ket qua nhat quan (deterministic)

    NGUONG TOI THIEU:
    - Chi tra ve stack co diem >= 20.0
    - Neu khong co stack nao dat nguong -> tra ve danh sach rong
      (Librarian se thong bao "khong tim thay stack phu hop")

    Do phuc tap: O(S * log(S))
      S = so stacks (thuong < 20)
    """
    scored_stacks = []

    for stack in stacks:
        score, details = score_stack_match(stack, project_signals)

        if score < 20.0:
            continue  # Bo qua stack khong du diem

        scored_stacks.append({
            "stack_name": stack["name"],
            "score": score,
            "match_details": details,
            "entry_count": len(stack.get("entries", [])),
            "explanation": _generate_explanation(stack, details),
        })

    # Sap xep voi tie-breaking
    scored_stacks.sort(key=lambda s: (
        -s["score"],                                    # Diem giam dan
        -len(s["match_details"]["file_matches"]),       # Nhieu file match hon
        -len(s["match_details"]["tech_matches"]),       # Nhieu tech match hon
        s["entry_count"],                               # It entry hon (chuyen biet hon)
        s["stack_name"],                                # Alphabet
    ))

    return scored_stacks[:top_k]


def _generate_explanation(stack: dict, details: dict) -> str:
    """Tao giai thich bang ngon ngu tu nhien cho ket qua matching."""
    parts = []

    if details["file_matches"]:
        files_str = ", ".join(details["file_matches"][:3])
        parts.append(f"Project co cac file: {files_str}")

    if details["tech_matches"]:
        techs_str = ", ".join(details["tech_matches"][:3])
        parts.append(f"su dung technologies: {techs_str}")

    if details["domain_matches"]:
        domains_str = ", ".join(details["domain_matches"][:2])
        parts.append(f"thuoc domains: {domains_str}")

    explanation = "; ".join(parts) if parts else "Matching dua tren tin hieu chung"
    return f"Stack '{stack['name']}' phu hop vi: {explanation}."


def match_stack(
    project_path: Path = None,
    project_description: str = None,
    stacks_dir: Path = None,
) -> list[dict]:
    """
    Entry point chinh cho stack matching.

    Su dung:
      1. Tu project files:  match_stack(project_path="/path/to/project")
      2. Tu mo ta:           match_stack(project_description="ROS2 robot voi LiDAR")
      3. Ca hai:             match_stack(project_path=..., project_description=...)
         -> Hop nhat signals tu ca hai nguon
    """
    if stacks_dir is None:
        stacks_dir = Path("~/Agent_Hub/agent-hub-index/stacks").expanduser()

    # ── Thu thap signals ─────────────────────────────────────────────────
    signals = {"technologies": [], "domains": [], "file_patterns": []}

    if project_path and project_path.exists():
        file_signals = extract_signals_from_project(project_path)
        signals["technologies"].extend(file_signals["technologies"])
        signals["domains"].extend(file_signals["domains"])
        signals["file_patterns"].extend(file_signals["file_patterns"])

    if project_description:
        desc_signals = extract_signals_from_description(project_description)
        signals["technologies"].extend(desc_signals["technologies"])
        signals["domains"].extend(desc_signals["domains"])

    # Loai bo trung lap
    signals = {
        k: list(set(v)) for k, v in signals.items()
    }

    if not any(signals.values()):
        return []  # Khong co tin hieu nao

    # ── Load stacks ──────────────────────────────────────────────────────
    stacks = []
    if stacks_dir.exists():
        for stack_file in stacks_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(stack_file.read_text())
                if data:
                    stacks.append(data)
            except Exception:
                continue

    if not stacks:
        return []  # Khong co stack nao duoc dinh nghia

    # ── Ranking ──────────────────────────────────────────────────────────
    return rank_stacks(stacks, signals, top_k=3)
```

### 3.7 Do phuc tap

| Giai doan | Do phuc tap | Chi tiet |
|-----------|-------------|----------|
| Extract signals (files) | O(F * D) | F=15 files, D=avg content size |
| Extract signals (description) | O(K * T) | K=keywords, T=text length |
| Score 1 stack | O(T + D + P) | T=techs, D=domains, P=file patterns |
| Rank all stacks | O(S * log(S)) | S=so stacks |
| **Tong** | **O(F*D + S*(T+D+P))** | Thuc te < 200ms |

### 3.8 Cac truong hop dac biet

| Truong hop | Xu ly |
|------------|-------|
| Project rong (khong co file nao) | Tra ve danh sach rong, Librarian bao "can mo ta project" |
| Project co nhieu ngon ngu (polyglot) | Tra ve nhieu stacks, moi stack cho 1 aspect |
| Khong co stack nao dat nguong 20.0 | Tra ve rong, Librarian goi y tao custom stack |
| Project dung tech khong co trong stack nao | Tra ve rong + goi y dua tren domain matching |
| Mo ta bang tieng khong phai tieng Anh | Keyword matching van hoat dong neu co tu tieng Anh (vd: "ROS2") |
| Hai stacks co cung diem chinh xac | Tie-breaking theo: file_matches > tech_matches > entry_count > alphabet |
| stacks/ directory chua ton tai | Tra ve rong, khong loi |

### 3.9 Vi du minh hoa

**Vi du 1: Web project**

```
Project files:
  package.json (co react, next, prisma, jest)
  tsconfig.json
  docker-compose.yml
  prisma/schema.prisma

Extracted signals:
  technologies: [typescript, react, postgres, docker]
  domains: [web-frontend, web-backend, data, devops, testing]
  file_patterns: [package.json, tsconfig.json, docker-compose.yml, prisma/schema.prisma]

Stack: web-fullstack
  stack.technologies: [typescript, javascript, react, postgres, docker]
  stack.domains: [web-frontend, web-backend, data, devops]
  stack.file_patterns: [package.json, tsconfig.json, docker-compose.yml, .env,
                         prisma/schema.prisma, next.config.*, vite.config.*]

Scoring:
  tech_matches: [typescript, react, postgres, docker]  -> 4/5 = 80.0
  domain_matches: [web-frontend, web-backend, data, devops]  -> 4/4 = 100.0
  file_matches: [package.json, tsconfig.json, docker-compose.yml, prisma/schema.prisma] -> 4/7 = 57.1

  total = 80.0 * 0.30 + 100.0 * 0.20 + 57.1 * 0.50
        = 24.0 + 20.0 + 28.55
        = 72.55

Ket qua:
  #1: web-fullstack (72.55) -- "Project co cac file: docker-compose.yml, package.json,
       tsconfig.json; su dung technologies: docker, postgres, react; thuoc domains:
       data, devops, web-backend."
```

**Vi du 2: ROS2 project**

```
Project files:
  CMakeLists.txt (co find_package(ament_cmake), find_package(rclcpp))
  package.xml
  launch/nav.py
  config/params.yaml

Extracted signals:
  technologies: [cpp, ros2, python]
  domains: [robotics]
  file_patterns: [CMakeLists.txt, package.xml, launch/*.py]

Stack: ros2-robotics
  stack.technologies: [ros2, cpp, python, docker]
  stack.domains: [robotics, devops, testing]
  stack.file_patterns: [CMakeLists.txt, package.xml, colcon.meta,
                         launch/*.py, config/*.yaml, urdf/*.xacro]

Scoring:
  tech_matches: [ros2, cpp, python]  -> 3/4 = 75.0
  domain_matches: [robotics]  -> 1/3 = 33.3
  file_matches: [CMakeLists.txt, package.xml, launch/*.py] -> 3/6 = 50.0

  total = 75.0 * 0.30 + 33.3 * 0.20 + 50.0 * 0.50
        = 22.5 + 6.66 + 25.0
        = 54.16

Ket qua:
  #1: ros2-robotics (54.16) -- "Project co cac file: CMakeLists.txt, package.xml;
       su dung technologies: cpp, python, ros2; thuoc domains: robotics."
```

---

## 4. Thuat toan Publish (publish-to-project.py)

### 4.1 Mo ta

Thuat toan deploy skills tu library vao mot project cu the. No copy cac file SKILL.md vao thu muc `.claude/skills/` cua project, deploy Librarian agent, va tao/cap nhat `library-manifest.yaml` de theo doi trang thai.

**Tinh chat quan trong: IDEMPOTENCY** -- chay lai voi cung input se khong tao file trung lap.

### 4.2 Dac ta Input/Output

```
INPUT:
  - mode (chon 1):
      a. stack_name: string        # "web-fullstack" -> lay tat ca skills tu stack
      b. skill_ids: list[string]   # ["brainstorming", "systematic-debugging"]
  - target_project_path: Path      # "$HOME/my-project"
  - options:
      --force: boolean             # ghi de file da ton tai (mac dinh: false)
      --dry-run: boolean           # chi hien thi, khong lam (mac dinh: false)
      --no-librarian: boolean      # khong copy librarian agent (mac dinh: false)
      --no-manifest: boolean       # khong tao manifest (mac dinh: false)

OUTPUT:
  - target/.claude/skills/{skill_id}/SKILL.md    # cho moi skill
  - target/.claude/agents/librarian.md            # Librarian agent
  - target/.claude/library-manifest.yaml          # Manifest theo doi

  library-manifest.yaml format:
    version: 1
    published_at: "2026-03-30T12:00:00Z"
    stack: "web-fullstack"              # hoac null neu publish tu skill_ids
    skills:
      - id: "brainstorming"
        version: 1
        hash: "sha256:abc..."
      - id: "systematic-debugging"
        version: 1
        hash: "sha256:def..."
    librarian_version: 1
    source_library: "$HOME/Agent_Hub/agent-hub-index/library"

EXIT CODES:
  0 = thanh cong
  1 = target path khong ton tai
  2 = stack khong tim thay
  3 = skill khong ton tai trong library
  4 = xung dot (skill da ton tai va khong co --force)
  5 = loi he thong (I/O, permission)
```

### 4.3 Pseudocode

```python
#!/usr/bin/env python3
"""publish-to-project.py -- Deploy skills tu library vao project."""

import yaml
import hashlib
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone

# ── Cau hinh ─────────────────────────────────────────────────────────────────
HUB_ROOT = Path("~/Agent_Hub").expanduser()
LIBRARY_DIR = HUB_ROOT / "agent-hub-index" / "library"
STACKS_DIR = HUB_ROOT / "agent-hub-index" / "stacks"
LIBRARIAN_PATH = LIBRARY_DIR / "agents" / "librarian.md"


def resolve_skill_ids(
    stack_name: str = None,
    skill_ids: list[str] = None,
) -> tuple[list[str], str | None]:
    """
    Resolve danh sach skill IDs tu stack hoac tu input truc tiep.

    Returns:
        (skill_ids, stack_name_or_none)

    Raises:
        FileNotFoundError: neu stack file khong ton tai
    """
    if stack_name:
        stack_file = STACKS_DIR / f"{stack_name}.yaml"
        if not stack_file.exists():
            raise FileNotFoundError(
                f"Stack '{stack_name}' khong tim thay tai {stack_file}"
            )

        data = yaml.safe_load(stack_file.read_text())
        resolved_ids = data.get("entries", [])

        if not resolved_ids:
            raise ValueError(f"Stack '{stack_name}' khong co entries nao")

        return resolved_ids, stack_name

    elif skill_ids:
        return skill_ids, None

    else:
        raise ValueError("Can cung cap stack_name hoac skill_ids")


def validate_skills_exist(skill_ids: list[str]) -> tuple[list[str], list[str]]:
    """
    Kiem tra tat ca skill IDs co ton tai trong library khong.

    Returns:
        (valid_ids, missing_ids)
    """
    valid = []
    missing = []

    for sid in skill_ids:
        skill_dir = LIBRARY_DIR / "skills" / sid
        skill_file = skill_dir / "SKILL.md"

        if skill_file.exists():
            valid.append(sid)
        else:
            missing.append(sid)

    return valid, missing


def check_conflicts(
    skill_ids: list[str],
    target_path: Path,
    force: bool,
) -> tuple[list[str], list[str]]:
    """
    Kiem tra xung dot voi cac skill da ton tai trong target project.

    Returns:
        (new_ids, existing_ids)
        - new_ids: skills chua co trong target (se duoc copy)
        - existing_ids: skills da co (se bi bo qua hoac ghi de neu --force)
    """
    new_ids = []
    existing_ids = []

    for sid in skill_ids:
        target_skill = target_path / ".claude" / "skills" / sid / "SKILL.md"
        if target_skill.exists():
            existing_ids.append(sid)
        else:
            new_ids.append(sid)

    return new_ids, existing_ids


def compute_file_hash(path: Path) -> str:
    """Tinh SHA-256 hash cua file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def publish_skill(
    skill_id: str,
    target_path: Path,
    force: bool = False,
) -> dict:
    """
    Copy 1 skill tu library vao target project.

    IDEMPOTENCY:
    - Neu file da ton tai va noi dung giong nhau -> bo qua (khong loi)
    - Neu file da ton tai va noi dung khac -> loi (tru khi --force)
    - Neu file chua ton tai -> copy

    Returns:
        {
            "id": skill_id,
            "action": "created" | "updated" | "skipped",
            "hash": "sha256:...",
        }
    """
    source_dir = LIBRARY_DIR / "skills" / skill_id
    source_file = source_dir / "SKILL.md"

    target_dir = target_path / ".claude" / "skills" / skill_id
    target_file = target_dir / "SKILL.md"

    source_hash = compute_file_hash(source_file)

    # Kiem tra idempotency
    if target_file.exists():
        target_hash = compute_file_hash(target_file)

        if source_hash == target_hash:
            # Noi dung giong nhau -> bo qua
            return {
                "id": skill_id,
                "action": "skipped",
                "hash": source_hash,
                "reason": "noi dung giong nhau",
            }

        if not force:
            return {
                "id": skill_id,
                "action": "conflict",
                "hash": source_hash,
                "reason": "file da ton tai voi noi dung khac",
            }

        # --force: ghi de
        action = "updated"
    else:
        action = "created"

    # Tao thu muc va copy
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_file, target_file)

    # Copy cac file phu (neu co) -- nhung CHI copy SKILL.md va cac .md files
    # Khong copy provenance.yaml, enrichment.yaml (chi dung noi bo library)
    for item in source_dir.iterdir():
        if item.name in ("provenance.yaml", "enrichment.yaml"):
            continue
        if item.is_file() and item.suffix == ".md" and item.name != "SKILL.md":
            shutil.copy2(item, target_dir / item.name)

    return {
        "id": skill_id,
        "action": action,
        "hash": source_hash,
    }


def publish_librarian(target_path: Path, force: bool = False) -> dict:
    """
    Copy librarian agent vao target project.

    Returns:
        {"action": "created" | "updated" | "skipped"}
    """
    if not LIBRARIAN_PATH.exists():
        return {"action": "skipped", "reason": "librarian.md khong ton tai trong library"}

    target_file = target_path / ".claude" / "agents" / "librarian.md"

    if target_file.exists():
        source_hash = compute_file_hash(LIBRARIAN_PATH)
        target_hash = compute_file_hash(target_file)

        if source_hash == target_hash:
            return {"action": "skipped", "reason": "giong nhau"}

        if not force:
            return {"action": "conflict", "reason": "da ton tai voi noi dung khac"}

    target_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LIBRARIAN_PATH, target_file)

    return {"action": "created" if not target_file.exists() else "updated"}


def create_manifest(
    target_path: Path,
    skill_results: list[dict],
    stack_name: str | None,
    librarian_result: dict,
) -> None:
    """
    Tao hoac cap nhat library-manifest.yaml.

    IDEMPOTENCY:
    - Neu manifest da ton tai, merge skills moi vao danh sach hien tai
    - Khong xoa skills da co (chi them moi hoac cap nhat)
    """
    manifest_path = target_path / ".claude" / "library-manifest.yaml"

    # Load manifest cu (neu co)
    existing_skills = {}
    if manifest_path.exists():
        try:
            old_manifest = yaml.safe_load(manifest_path.read_text()) or {}
            for skill in old_manifest.get("skills", []):
                existing_skills[skill["id"]] = skill
        except Exception:
            pass  # Manifest cu hong, tao moi hoan toan

    # Merge skills
    for result in skill_results:
        if result["action"] in ("created", "updated"):
            existing_skills[result["id"]] = {
                "id": result["id"],
                "version": 1,  # TODO: lay tu provenance
                "hash": result["hash"],
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
        elif result["action"] == "skipped" and result["id"] not in existing_skills:
            # Skill da co trong target nhung chua co trong manifest -> them vao
            existing_skills[result["id"]] = {
                "id": result["id"],
                "version": 1,
                "hash": result.get("hash", "unknown"),
                "published_at": datetime.now(timezone.utc).isoformat(),
            }

    manifest = {
        "version": 1,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "stack": stack_name,
        "skills": sorted(existing_skills.values(), key=lambda s: s["id"]),
        "librarian_version": 1 if librarian_result.get("action") != "skipped" else None,
        "source_library": str(LIBRARY_DIR),
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True)


# ── Thuat toan chinh ─────────────────────────────────────────────────────────

def publish(
    target_project_path: str,
    stack_name: str = None,
    skill_ids: list[str] = None,
    force: bool = False,
    dry_run: bool = False,
    no_librarian: bool = False,
    no_manifest: bool = False,
) -> int:
    """
    Thuat toan publish chinh.

    Do phuc tap:
      O(N * F)
      N = so skills can publish
      F = kich thuoc trung binh cua file (de copy + hash)

    Dam bao IDEMPOTENCY:
      - Chay lai 2 lan voi cung params -> ket qua giong nhau
      - Khong tao file trung lap
      - Manifest duoc merge, khong ghi de
    """
    target = Path(target_project_path)

    # ── Buoc 1: Validate target ─────────────────────────────────────────
    if not target.exists() or not target.is_dir():
        print(f"LOI: Target '{target}' khong ton tai hoac khong phai directory",
              file=sys.stderr)
        return 1

    # ── Buoc 2: Resolve skill IDs ────────────────────────────────────────
    try:
        resolved_ids, resolved_stack = resolve_skill_ids(stack_name, skill_ids)
    except FileNotFoundError as e:
        print(f"LOI: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"LOI: {e}", file=sys.stderr)
        return 2

    print(f"Se publish {len(resolved_ids)} skills vao {target}")
    if resolved_stack:
        print(f"  Stack: {resolved_stack}")

    # ── Buoc 3: Validate skills ton tai trong library ────────────────────
    valid_ids, missing_ids = validate_skills_exist(resolved_ids)

    if missing_ids:
        print(f"LOI: Cac skills sau khong ton tai trong library:", file=sys.stderr)
        for mid in missing_ids:
            print(f"  - {mid}", file=sys.stderr)
        return 3

    # ── Buoc 4: Kiem tra conflicts ───────────────────────────────────────
    new_ids, existing_ids = check_conflicts(valid_ids, target, force)

    if existing_ids and not force:
        print(f"CANH BAO: {len(existing_ids)} skills da ton tai trong target:")
        for eid in existing_ids:
            print(f"  - {eid}")
        print(f"  Dung --force de ghi de, hoac bo qua cac skills nay.")
        # Khong fail -- chi publish cac skills moi
        if not new_ids:
            print("Khong co skill moi nao de publish.")
            # Van tao manifest neu can

    # ── Buoc 5: Dry run check ────────────────────────────────────────────
    if dry_run:
        print(f"\n[DRY RUN] Se thuc hien:")
        for sid in new_ids:
            print(f"  TAO MOI: .claude/skills/{sid}/SKILL.md")
        for sid in existing_ids:
            if force:
                print(f"  GHI DE:  .claude/skills/{sid}/SKILL.md")
            else:
                print(f"  BO QUA:  .claude/skills/{sid}/SKILL.md (da ton tai)")
        if not no_librarian:
            print(f"  {'TAO/CAP NHAT' if LIBRARIAN_PATH.exists() else 'BO QUA'}: "
                  f".claude/agents/librarian.md")
        if not no_manifest:
            print(f"  TAO/CAP NHAT: .claude/library-manifest.yaml")
        return 0

    # ── Buoc 6: Publish tung skill ───────────────────────────────────────
    skill_results = []

    # Publish skills moi
    for sid in new_ids:
        result = publish_skill(sid, target, force=False)
        skill_results.append(result)
        print(f"  {result['action'].upper()}: {sid}")

    # Publish skills da ton tai (neu --force)
    for sid in existing_ids:
        result = publish_skill(sid, target, force=force)
        skill_results.append(result)
        print(f"  {result['action'].upper()}: {sid}")

    # ── Buoc 7: Publish librarian ────────────────────────────────────────
    librarian_result = {"action": "skipped"}
    if not no_librarian:
        librarian_result = publish_librarian(target, force=force)
        print(f"  LIBRARIAN: {librarian_result['action']}")

    # ── Buoc 8: Tao/cap nhat manifest ────────────────────────────────────
    if not no_manifest:
        create_manifest(target, skill_results, resolved_stack, librarian_result)
        print(f"  MANIFEST: created/updated")

    # ── Tong ket ─────────────────────────────────────────────────────────
    created = sum(1 for r in skill_results if r["action"] == "created")
    updated = sum(1 for r in skill_results if r["action"] == "updated")
    skipped = sum(1 for r in skill_results if r["action"] == "skipped")
    conflicts = sum(1 for r in skill_results if r["action"] == "conflict")

    print(f"\nTong ket: {created} tao moi, {updated} cap nhat, "
          f"{skipped} bo qua, {conflicts} xung dot")

    return 0


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Publish skills vao project")
    parser.add_argument("target", help="Duong dan den target project")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stack", help="Ten stack de publish")
    group.add_argument("--skills", nargs="+", help="Danh sach skill IDs")

    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-librarian", action="store_true")
    parser.add_argument("--no-manifest", action="store_true")
    args = parser.parse_args()

    sys.exit(publish(
        args.target,
        stack_name=args.stack,
        skill_ids=args.skills,
        force=args.force,
        dry_run=args.dry_run,
        no_librarian=args.no_librarian,
        no_manifest=args.no_manifest,
    ))
```

### 4.4 Do phuc tap

| Giai doan | Do phuc tap | Chi tiet |
|-----------|-------------|----------|
| Resolve skill IDs | O(1) hoac O(S) | S = so entries trong stack |
| Validate trong library | O(N) | N = so skill IDs |
| Check conflicts | O(N) | Kiem tra file ton tai |
| Publish moi skill | O(F) | F = kich thuoc file |
| Hash comparison | O(F) | Doc toan bo file |
| Tao manifest | O(N) | Merge skills |
| **Tong** | **O(N * F)** | Thuc te < 1s cho N=15 |

### 4.5 Cac truong hop dac biet

| Truong hop | Xu ly |
|------------|-------|
| Target chua co `.claude/` directory | Tu dong tao `.claude/skills/` va `.claude/agents/` |
| Chay lai cung lenh 2 lan (idempotency) | Lan 2: tat ca skills "skipped" (hash giong), manifest khong bi trung lap |
| --force voi skill co noi dung giong | Van "skipped" (hash comparison, khong can force) |
| Stack reference skill chua import vao library | Bao loi exit code 3 voi danh sach missing skills |
| Target la Git repo voi uncommitted changes | Khong can thiep -- user tu quyet dinh commit |
| Manifest da ton tai tu lan publish truoc | Merge: skills cu giu nguyen, skills moi them vao |
| Librarian.md khong ton tai trong library | Bo qua, khong loi (chi canh bao) |
| Permission denied khi ghi vao target | Exit code 5, thong bao cu the file nao |

### 4.6 Vi du minh hoa

**Vi du 1: Publish stack**

```bash
$ python publish-to-project.py $HOME/my-web-app --stack web-fullstack

Se publish 7 skills vao $HOME/my-web-app
  Stack: web-fullstack
  CREATED: brainstorming
  CREATED: writing-plans
  CREATED: executing-plans
  CREATED: test-driven-development
  CREATED: systematic-debugging
  CREATED: finishing-a-development-branch
  CREATED: verification-before-completion
  LIBRARIAN: created
  MANIFEST: created/updated

Tong ket: 7 tao moi, 0 cap nhat, 0 bo qua, 0 xung dot
```

**Vi du 2: Chay lai (idempotency)**

```bash
$ python publish-to-project.py $HOME/my-web-app --stack web-fullstack

Se publish 7 skills vao $HOME/my-web-app
  Stack: web-fullstack
  SKIPPED: brainstorming
  SKIPPED: writing-plans
  SKIPPED: executing-plans
  SKIPPED: test-driven-development
  SKIPPED: systematic-debugging
  SKIPPED: finishing-a-development-branch
  SKIPPED: verification-before-completion
  LIBRARIAN: skipped
  MANIFEST: created/updated

Tong ket: 0 tao moi, 0 cap nhat, 7 bo qua, 0 xung dot
```

**Vi du 3: Them skill rieng le**

```bash
$ python publish-to-project.py $HOME/my-web-app --skills code-reviewer

Se publish 1 skills vao $HOME/my-web-app
  CREATED: code-reviewer
  LIBRARIAN: skipped
  MANIFEST: created/updated

Tong ket: 1 tao moi, 0 cap nhat, 0 bo qua, 0 xung dot

# library-manifest.yaml bay gio co 8 skills (7 tu stack + 1 moi them)
```

---

## 5. Thuat toan Validation (validate.py)

### 5.1 Mo ta

Thuat toan kiem tra tinh nhat quan va day du cua toan bo he thong: library, catalog, collections, va stacks. Tra ve bao cao chi tiet voi ket qua pass/fail cho tung kiem tra.

### 5.2 Dac ta Input/Output

```
INPUT:
  - library_dir: Path              # library/ directory
  - catalog_path: Path             # catalog.json
  - collections_dir: Path          # collections/ directory
  - stacks_dir: Path               # stacks/ directory
  - options:
      --strict: boolean            # coi canh bao la loi (mac dinh: false)
      --json: boolean              # output dang JSON (mac dinh: false)
      --fix: boolean               # tu dong sua cac van de don gian (mac dinh: false)

OUTPUT:
  ValidationReport:
    total_checks: number
    passed: number
    failed: number
    warnings: number
    checks: list[CheckResult]

  CheckResult:
    id: string                     # "SKILL_HAS_MD", "CATALOG_REF_VALID", ...
    name: string                   # "Moi skill co SKILL.md"
    status: "pass" | "fail" | "warn"
    details: string                # Chi tiet khi fail/warn
    affected_items: list[string]   # Danh sach items bi anh huong

EXIT CODES:
  0 = tat ca pass (hoac chi co warning va khong --strict)
  1 = co it nhat 1 fail
  2 = loi he thong (thu muc khong ton tai)
```

### 5.3 Pseudocode

```python
#!/usr/bin/env python3
"""validate.py -- Kiem tra tinh nhat quan cua Agent Hub library."""

import json
import yaml
import sys
from pathlib import Path
from dataclasses import dataclass, field

# ── Cau hinh ─────────────────────────────────────────────────────────────────
HUB_ROOT = Path("~/Agent_Hub").expanduser()
INDEX_DIR = HUB_ROOT / "agent-hub-index"
LIBRARY_DIR = INDEX_DIR / "library"
CATALOG_PATH = INDEX_DIR / "catalog.json"
COLLECTIONS_DIR = INDEX_DIR / "collections"
STACKS_DIR = INDEX_DIR / "stacks"


@dataclass
class CheckResult:
    id: str
    name: str
    status: str  # "pass", "fail", "warn"
    details: str = ""
    affected_items: list[str] = field(default_factory=list)


class ValidationReport:
    def __init__(self):
        self.checks: list[CheckResult] = []

    def add(self, result: CheckResult):
        self.checks.append(result)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == "fail")

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if c.status == "warn")

    def is_ok(self, strict: bool = False) -> bool:
        if strict:
            return self.failed == 0 and self.warnings == 0
        return self.failed == 0


# ── Check 1: Moi skill co SKILL.md + provenance.yaml ────────────────────────

def check_skill_files(report: ValidationReport) -> set[str]:
    """
    KIEM TRA: Moi thu muc trong library/skills/ co SKILL.md va provenance.yaml.

    Returns:
        Set cua cac skill IDs hop le (de dung cho cac check tiep theo)

    Do phuc tap: O(S) voi S = so skill directories
    """
    skills_dir = LIBRARY_DIR / "skills"
    valid_skill_ids = set()
    missing_md = []
    missing_prov = []

    if not skills_dir.exists():
        report.add(CheckResult(
            id="SKILL_DIR_EXISTS",
            name="Thu muc library/skills/ ton tai",
            status="fail",
            details=f"Khong tim thay {skills_dir}",
        ))
        return valid_skill_ids

    report.add(CheckResult(
        id="SKILL_DIR_EXISTS",
        name="Thu muc library/skills/ ton tai",
        status="pass",
    ))

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_id = skill_dir.name
        skill_file = skill_dir / "SKILL.md"
        prov_file = skill_dir / "provenance.yaml"

        if not skill_file.exists():
            missing_md.append(skill_id)
        elif not prov_file.exists():
            missing_prov.append(skill_id)
            valid_skill_ids.add(skill_id)  # Van hop le, chi thieu provenance
        else:
            valid_skill_ids.add(skill_id)

    # Report SKILL.md check
    if missing_md:
        report.add(CheckResult(
            id="SKILL_HAS_MD",
            name="Moi skill co SKILL.md",
            status="fail",
            details=f"{len(missing_md)} skills thieu SKILL.md",
            affected_items=missing_md,
        ))
    else:
        report.add(CheckResult(
            id="SKILL_HAS_MD",
            name="Moi skill co SKILL.md",
            status="pass",
        ))

    # Report provenance check
    if missing_prov:
        report.add(CheckResult(
            id="SKILL_HAS_PROVENANCE",
            name="Moi skill co provenance.yaml",
            status="warn",
            details=f"{len(missing_prov)} skills thieu provenance.yaml",
            affected_items=missing_prov,
        ))
    else:
        report.add(CheckResult(
            id="SKILL_HAS_PROVENANCE",
            name="Moi skill co provenance.yaml",
            status="pass",
        ))

    return valid_skill_ids


# ── Check 2: Moi agent co frontmatter hop le ────────────────────────────────

def check_agent_files(report: ValidationReport) -> set[str]:
    """
    KIEM TRA: Moi file .md trong library/agents/ co YAML frontmatter hop le
    voi it nhat 'name' va 'description'.

    Returns:
        Set cua cac agent IDs hop le

    Do phuc tap: O(A * T) voi A = so agents, T = kich thuoc file
    """
    agents_dir = LIBRARY_DIR / "agents"
    valid_agent_ids = set()
    invalid_agents = []

    if not agents_dir.exists():
        report.add(CheckResult(
            id="AGENT_DIR_EXISTS",
            name="Thu muc library/agents/ ton tai",
            status="warn",
            details=f"Khong tim thay {agents_dir} (co the chua co agents nao)",
        ))
        return valid_agent_ids

    import re
    FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n?(.*)', re.DOTALL)

    for agent_file in sorted(agents_dir.glob("*.md")):
        if agent_file.stem.endswith((".provenance", ".enrichment")):
            continue

        agent_id = agent_file.stem
        text = agent_file.read_text(encoding="utf-8", errors="replace")

        match = FRONTMATTER_RE.match(text)
        if not match:
            invalid_agents.append(f"{agent_id}: thieu frontmatter")
            continue

        try:
            fm = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as e:
            invalid_agents.append(f"{agent_id}: YAML loi - {e}")
            continue

        if not fm.get("name"):
            invalid_agents.append(f"{agent_id}: thieu truong 'name'")
            continue

        if not fm.get("description"):
            invalid_agents.append(f"{agent_id}: thieu truong 'description'")
            # Chi warn, khong fail
            valid_agent_ids.add(agent_id)
            continue

        valid_agent_ids.add(agent_id)

    if invalid_agents:
        report.add(CheckResult(
            id="AGENT_VALID_FRONTMATTER",
            name="Moi agent co frontmatter hop le",
            status="fail",
            details=f"{len(invalid_agents)} agents khong hop le",
            affected_items=invalid_agents,
        ))
    else:
        report.add(CheckResult(
            id="AGENT_VALID_FRONTMATTER",
            name="Moi agent co frontmatter hop le",
            status="pass",
        ))

    return valid_agent_ids


# ── Check 3: catalog.json ton tai va day du ─────────────────────────────────

def check_catalog(
    report: ValidationReport,
    valid_skill_ids: set[str],
    valid_agent_ids: set[str],
) -> dict | None:
    """
    KIEM TRA:
    - catalog.json ton tai
    - Co entries cho tat ca skills va agents trong library
    - Khong co entry nao tro den skill/agent khong ton tai

    Returns:
        catalog dict (de dung cho cac check tiep theo) hoac None

    Do phuc tap: O(N) voi N = so entries trong catalog
    """
    if not CATALOG_PATH.exists():
        report.add(CheckResult(
            id="CATALOG_EXISTS",
            name="catalog.json ton tai",
            status="fail",
            details=f"Khong tim thay {CATALOG_PATH}. Chay build-catalog.py de tao.",
        ))
        return None

    try:
        catalog = json.loads(CATALOG_PATH.read_text())
    except json.JSONDecodeError as e:
        report.add(CheckResult(
            id="CATALOG_EXISTS",
            name="catalog.json ton tai va hop le",
            status="fail",
            details=f"JSON parse loi: {e}",
        ))
        return None

    report.add(CheckResult(
        id="CATALOG_EXISTS",
        name="catalog.json ton tai va hop le",
        status="pass",
    ))

    # Kiem tra catalog co entry cho moi library item
    catalog_ids = set(e["id"] for e in catalog.get("entries", []))
    all_library_ids = valid_skill_ids | valid_agent_ids

    missing_in_catalog = all_library_ids - catalog_ids
    extra_in_catalog = catalog_ids - all_library_ids

    if missing_in_catalog:
        report.add(CheckResult(
            id="CATALOG_COMPLETE",
            name="Catalog co du entries cho tat ca library items",
            status="fail",
            details=f"{len(missing_in_catalog)} items thieu trong catalog",
            affected_items=sorted(missing_in_catalog),
        ))
    else:
        report.add(CheckResult(
            id="CATALOG_COMPLETE",
            name="Catalog co du entries cho tat ca library items",
            status="pass",
        ))

    if extra_in_catalog:
        report.add(CheckResult(
            id="CATALOG_NO_ORPHANS",
            name="Catalog khong co entries mo coi (khong co trong library)",
            status="warn",
            details=f"{len(extra_in_catalog)} entries trong catalog khong co trong library",
            affected_items=sorted(extra_in_catalog),
        ))
    else:
        report.add(CheckResult(
            id="CATALOG_NO_ORPHANS",
            name="Catalog khong co entries mo coi",
            status="pass",
        ))

    return catalog


# ── Check 4: use_with references hop le ──────────────────────────────────────

def check_use_with_references(report: ValidationReport, catalog: dict):
    """
    KIEM TRA: Moi use_with reference trong catalog tro den entry ton tai.

    Do phuc tap: O(N * R) voi N = entries, R = trung binh so use_with moi entry
    """
    if not catalog:
        return

    entries = catalog.get("entries", [])
    catalog_ids = set(e["id"] for e in entries)

    broken_refs = []
    for entry in entries:
        for ref_id in entry.get("use_with", []):
            if ref_id not in catalog_ids:
                broken_refs.append(f"{entry['id']} -> {ref_id}")

    if broken_refs:
        report.add(CheckResult(
            id="USE_WITH_VALID",
            name="Tat ca use_with references tro den entries ton tai",
            status="fail",
            details=f"{len(broken_refs)} references bi hong",
            affected_items=broken_refs,
        ))
    else:
        report.add(CheckResult(
            id="USE_WITH_VALID",
            name="Tat ca use_with references hop le",
            status="pass",
        ))


# ── Check 5: Collection references hop le ───────────────────────────────────

def check_collection_references(report: ValidationReport, catalog_ids: set[str]):
    """
    KIEM TRA: Moi entry trong collection YAML tro den catalog ID ton tai.

    Do phuc tap: O(C * E) voi C = collections, E = entries moi collection
    """
    if not COLLECTIONS_DIR.exists():
        report.add(CheckResult(
            id="COLLECTIONS_VALID",
            name="Collection references hop le",
            status="pass",
            details="Thu muc collections/ chua ton tai (bo qua)",
        ))
        return

    broken_refs = []
    for coll_file in sorted(COLLECTIONS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(coll_file.read_text()) or {}
        except Exception:
            broken_refs.append(f"{coll_file.name}: YAML parse loi")
            continue

        coll_name = data.get("name", coll_file.stem)
        for entry_id in data.get("entries", []):
            if entry_id not in catalog_ids:
                broken_refs.append(f"{coll_name} -> {entry_id}")

    if broken_refs:
        report.add(CheckResult(
            id="COLLECTIONS_VALID",
            name="Collection references tro den catalog IDs ton tai",
            status="fail",
            details=f"{len(broken_refs)} references bi hong",
            affected_items=broken_refs,
        ))
    else:
        report.add(CheckResult(
            id="COLLECTIONS_VALID",
            name="Collection references hop le",
            status="pass",
        ))


# ── Check 6: Stack references hop le ────────────────────────────────────────

def check_stack_references(report: ValidationReport, catalog_ids: set[str]):
    """
    KIEM TRA: Moi entry trong stack YAML tro den catalog ID ton tai.

    Do phuc tap: O(S * E) voi S = stacks, E = entries moi stack
    """
    if not STACKS_DIR.exists():
        report.add(CheckResult(
            id="STACKS_VALID",
            name="Stack references hop le",
            status="pass",
            details="Thu muc stacks/ chua ton tai (bo qua)",
        ))
        return

    broken_refs = []
    for stack_file in sorted(STACKS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(stack_file.read_text()) or {}
        except Exception:
            broken_refs.append(f"{stack_file.name}: YAML parse loi")
            continue

        stack_name = data.get("name", stack_file.stem)
        for entry_id in data.get("entries", []):
            if entry_id not in catalog_ids:
                broken_refs.append(f"{stack_name} -> {entry_id}")

    if broken_refs:
        report.add(CheckResult(
            id="STACKS_VALID",
            name="Stack references tro den catalog IDs ton tai",
            status="fail",
            details=f"{len(broken_refs)} references bi hong",
            affected_items=broken_refs,
        ))
    else:
        report.add(CheckResult(
            id="STACKS_VALID",
            name="Stack references hop le",
            status="pass",
        ))


# ── Check 7: Khong co ID trung lap ──────────────────────────────────────────

def check_no_duplicate_ids(report: ValidationReport, catalog: dict):
    """
    KIEM TRA: Tat ca IDs trong catalog.json la duy nhat.

    Do phuc tap: O(N)
    """
    if not catalog:
        return

    entries = catalog.get("entries", [])
    seen_ids = {}
    duplicates = []

    for i, entry in enumerate(entries):
        eid = entry["id"]
        if eid in seen_ids:
            duplicates.append(f"'{eid}' xuat hien tai index {seen_ids[eid]} va {i}")
        else:
            seen_ids[eid] = i

    if duplicates:
        report.add(CheckResult(
            id="NO_DUPLICATE_IDS",
            name="Khong co ID trung lap trong catalog",
            status="fail",
            details=f"{len(duplicates)} IDs bi trung",
            affected_items=duplicates,
        ))
    else:
        report.add(CheckResult(
            id="NO_DUPLICATE_IDS",
            name="Khong co ID trung lap trong catalog",
            status="pass",
        ))


# ── Thuat toan chinh ─────────────────────────────────────────────────────────

def validate(strict: bool = False) -> tuple[ValidationReport, int]:
    """
    Chay tat ca cac kiem tra validation.

    THU TU CHAY:
    1. Check skill files         -> tra ve valid_skill_ids
    2. Check agent files         -> tra ve valid_agent_ids
    3. Check catalog             -> tra ve catalog dict
    4. Check use_with refs       -> dung catalog
    5. Check collection refs     -> dung catalog_ids
    6. Check stack refs          -> dung catalog_ids
    7. Check duplicate IDs       -> dung catalog

    Cac check co quan he phu thuoc:
      Check 4-7 phu thuoc vao Check 3 (can catalog)
      Check 3 phu thuoc vao Check 1-2 (can valid IDs)

    Do phuc tap tong: O(N * R + C * E + S * E)
      N = so entries, R = refs moi entry
      C = collections, S = stacks, E = entries moi collection/stack
    """
    report = ValidationReport()

    print("Agent Hub Library Validation")
    print("=" * 50)

    # ── Check 1: Skills ──────────────────────────────────────────────────
    valid_skill_ids = check_skill_files(report)

    # ── Check 2: Agents ──────────────────────────────────────────────────
    valid_agent_ids = check_agent_files(report)

    # ── Check 3: Catalog ─────────────────────────────────────────────────
    catalog = check_catalog(report, valid_skill_ids, valid_agent_ids)

    # ── Check 4-7: References (chi chay neu co catalog) ──────────────────
    if catalog:
        catalog_ids = set(e["id"] for e in catalog.get("entries", []))
        check_use_with_references(report, catalog)
        check_collection_references(report, catalog_ids)
        check_stack_references(report, catalog_ids)
        check_no_duplicate_ids(report, catalog)

    # ── In ket qua ───────────────────────────────────────────────────────
    print()
    for check in report.checks:
        icon = {"pass": "OK  ", "fail": "FAIL", "warn": "WARN"}[check.status]
        print(f"  [{icon}] {check.name}")
        if check.details:
            print(f"         {check.details}")
        if check.affected_items:
            for item in check.affected_items[:10]:
                print(f"           - {item}")
            if len(check.affected_items) > 10:
                print(f"           ... va {len(check.affected_items) - 10} items khac")

    print()
    print(f"Tong: {report.total} checks | "
          f"{report.passed} pass | "
          f"{report.failed} fail | "
          f"{report.warnings} warn")

    exit_code = 0 if report.is_ok(strict=strict) else 1
    return report, exit_code


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate Agent Hub library")
    parser.add_argument("--strict", action="store_true",
                        help="Coi warnings la errors")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON format")
    args = parser.parse_args()

    report, exit_code = validate(strict=args.strict)

    if args.json:
        output = {
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "warnings": report.warnings,
            "checks": [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "details": c.details,
                    "affected_items": c.affected_items,
                }
                for c in report.checks
            ],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

    sys.exit(exit_code)
```

### 5.4 Do phuc tap

| Check | Do phuc tap | Chi tiet |
|-------|-------------|----------|
| SKILL_HAS_MD | O(S) | S = skill directories |
| SKILL_HAS_PROVENANCE | O(S) | Kiem tra cung luc voi SKILL_HAS_MD |
| AGENT_VALID_FRONTMATTER | O(A * T) | A = agents, T = file size |
| CATALOG_EXISTS | O(1) | Kiem tra file ton tai |
| CATALOG_COMPLETE | O(N + L) | N = catalog entries, L = library items |
| USE_WITH_VALID | O(N * R) | R = trung binh refs moi entry |
| COLLECTIONS_VALID | O(C * E) | C = collections, E = entries |
| STACKS_VALID | O(S * E) | S = stacks, E = entries |
| NO_DUPLICATE_IDS | O(N) | Hash set lookup |
| **Tong** | **O(N * R)** | Thuc te < 100ms |

### 5.5 Cac truong hop dac biet

| Truong hop | Xu ly |
|------------|-------|
| library/ chua ton tai | SKILL_DIR_EXISTS fail, cac check con van chay (deu fail/skip) |
| catalog.json co JSON syntax loi | CATALOG_EXISTS fail, checks 4-7 bi skip |
| Skill directory rong (khong co file nao) | SKILL_HAS_MD fail cho skill do |
| Agent file co frontmatter nhung thieu description | Warn (khong fail) |
| Collection reference den skill da bi xoa | COLLECTIONS_VALID fail |
| --strict mode | Warnings cung bi tinh la failure |
| Thu muc collections/ chua ton tai | Pass (chua co collections la binh thuong) |

### 5.6 Vi du minh hoa

**Vi du: Validation thanh cong voi 1 warning**

```
$ python validate.py

Agent Hub Library Validation
==================================================

  [OK  ] Thu muc library/skills/ ton tai
  [OK  ] Moi skill co SKILL.md
  [WARN] Moi skill co provenance.yaml
         1 skills thieu provenance.yaml
           - code-formatter
  [OK  ] Moi agent co frontmatter hop le
  [OK  ] catalog.json ton tai va hop le
  [OK  ] Catalog co du entries cho tat ca library items
  [OK  ] Catalog khong co entries mo coi
  [OK  ] Tat ca use_with references hop le
  [OK  ] Collection references hop le
  [OK  ] Stack references hop le
  [OK  ] Khong co ID trung lap trong catalog

Tong: 11 checks | 10 pass | 0 fail | 1 warn
```

---

## 6. Thuat toan Proactive Detection (session hook)

### 6.1 Mo ta

Thuat toan nay chay tu dong moi khi bat dau mot phien lam viec (session) trong Claude Code. No kiem tra xem project hien tai da duoc cau hinh voi Agent Hub skills chua, va neu chua thi tu dong goi y stack phu hop.

Ngoai ra, neu project da co skills nhung phien ban trong library da moi hon, no se thong bao cho user.

### 6.2 Dac ta Input/Output

```
INPUT:
  - session_start_event:
      project_path: Path           # Duong dan den project hien tai
      # (Tu dong lay tu working directory cua Claude Code session)

OUTPUT (1 trong 3 truong hop):

  Truong hop A - Project chua cau hinh:
    context_injection: string
    # "Project nay chua co skills duoc cau hinh.
    #  Dua tren project files, toi goi y stack 'web-fullstack'.
    #  Chay /publish --stack web-fullstack de cai dat."

  Truong hop B - Co cap nhat moi:
    update_notification: string
    # "2 skills co phien ban moi trong library:
    #  - brainstorming (v1 -> v2)
    #  - systematic-debugging (v1 -> v3)
    #  Chay /update-skills de cap nhat."

  Truong hop C - Moi thu deu moi nhat:
    (khong output gi -- khong can thiep vao session)
```

### 6.3 Pseudocode

```python
#!/usr/bin/env python3
"""
proactive-detection.py -- Session hook cho Agent Hub.

Duoc goi tu Claude Code hook system khi session bat dau.
Output duoc inject vao session context.
"""

import json
import yaml
import sys
from pathlib import Path

HUB_ROOT = Path("~/Agent_Hub").expanduser()
LIBRARY_DIR = HUB_ROOT / "agent-hub-index" / "library"
STACKS_DIR = HUB_ROOT / "agent-hub-index" / "stacks"

# Import tu cac module khac
# from stack_matching import match_stack, extract_signals_from_project
# from import_skill import compute_file_hash


def check_manifest_exists(project_path: Path) -> dict | None:
    """
    Kiem tra xem project da co library-manifest.yaml chua.

    Returns:
        manifest dict neu ton tai, None neu khong
    """
    manifest_path = project_path / ".claude" / "library-manifest.yaml"

    if not manifest_path.exists():
        return None

    try:
        return yaml.safe_load(manifest_path.read_text()) or None
    except Exception:
        return None  # Manifest hong -> coi nhu chua co


def detect_updates(manifest: dict) -> list[dict]:
    """
    So sanh phien ban skills trong manifest voi library.

    CACH HOAT DONG:
    1. Voi moi skill trong manifest, doc hash da luu
    2. Tinh hash cua file tuong ung trong library
    3. Neu hash khac nhau -> co cap nhat moi

    Returns:
        Danh sach skills co cap nhat:
        [{"id": "brainstorming", "manifest_version": 1, "library_version": 2}]

    Do phuc tap: O(N * F)
      N = so skills trong manifest
      F = kich thuoc file trung binh (de tinh hash)
    """
    updates = []

    for skill in manifest.get("skills", []):
        skill_id = skill.get("id")
        if not skill_id:
            continue

        manifest_hash = skill.get("hash", "")

        # Tim file trong library
        library_file = LIBRARY_DIR / "skills" / skill_id / "SKILL.md"
        if not library_file.exists():
            continue  # Skill da bi xoa khoi library -- bo qua

        library_hash = compute_file_hash(library_file)

        if manifest_hash != library_hash:
            # Doc library version tu provenance
            prov_path = LIBRARY_DIR / "skills" / skill_id / "provenance.yaml"
            library_version = 1
            if prov_path.exists():
                try:
                    prov = yaml.safe_load(prov_path.read_text()) or {}
                    library_version = prov.get("library_version", 1)
                except Exception:
                    pass

            updates.append({
                "id": skill_id,
                "manifest_version": skill.get("version", 1),
                "library_version": library_version,
            })

    return updates


def generate_suggestion_message(
    project_path: Path,
    ranked_stacks: list[dict],
) -> str:
    """
    Tao thong bao goi y cho user khi project chua co skills.

    Returns:
        Chuoi text de inject vao session context
    """
    if not ranked_stacks:
        return (
            "Project nay chua co skills duoc cau hinh tu Agent Hub.\n"
            "Toi khong tu dong xac dinh duoc stack phu hop.\n"
            "Ban co the:\n"
            "  1. Mo ta project de toi goi y stack: /suggest-stack\n"
            "  2. Chon stack thu cong: /publish --stack <ten-stack>\n"
            "  3. Chon tung skill: /publish --skills <skill1> <skill2>"
        )

    best = ranked_stacks[0]
    msg_parts = [
        f"Project nay chua co skills duoc cau hinh tu Agent Hub.",
        f"Dua tren project files, toi goi y stack '{best['stack_name']}' "
        f"(do phu hop: {best['score']:.0f}%).",
        f"",
        f"Ly do: {best['explanation']}",
        f"",
        f"Chay lenh sau de cai dat:",
        f"  /publish --stack {best['stack_name']}",
    ]

    if len(ranked_stacks) > 1:
        msg_parts.append(f"")
        msg_parts.append(f"Cac lua chon khac:")
        for alt in ranked_stacks[1:]:
            msg_parts.append(
                f"  - {alt['stack_name']} ({alt['score']:.0f}%)"
            )

    return "\n".join(msg_parts)


def generate_update_message(updates: list[dict]) -> str:
    """Tao thong bao cap nhat cho user."""
    lines = [
        f"{len(updates)} skills co phien ban moi trong Agent Hub library:",
        "",
    ]

    for upd in updates:
        lines.append(
            f"  - {upd['id']} (v{upd['manifest_version']} -> v{upd['library_version']})"
        )

    lines.append("")
    lines.append("Chay /update-skills de cap nhat.")

    return "\n".join(lines)


# ── Thuat toan chinh ─────────────────────────────────────────────────────────

def proactive_detect(project_path: Path) -> str | None:
    """
    Thuat toan proactive detection chinh.

    LUONG XU LY:

    1. Kiem tra .claude/library-manifest.yaml
    2. NEU KHONG TON TAI:
       a. Scan project files de extract signals
       b. Chay stack matching
       c. Tra ve goi y stack
    3. NEU TON TAI:
       a. So sanh hash cua tung skill voi library
       b. Neu co hash khac -> thong bao cap nhat
       c. Neu tat ca giong nhau -> tra ve None (im lang)

    Do phuc tap:
      Truong hop A (chua cau hinh): O(F*D + S*(T+D+P))
        F = file scan, S = stacks, T/D/P = signals
      Truong hop B (kiem tra update): O(N * FileSize)
        N = so skills trong manifest
      Truong hop C (moi nhat): O(N * FileSize)
        (van phai tinh hash de kiem tra)

    Returns:
        Chuoi thong bao de inject, hoac None neu khong can
    """
    # ── Buoc 1: Kiem tra manifest ────────────────────────────────────────
    manifest = check_manifest_exists(project_path)

    # ── Truong hop A: Chua cau hinh ─────────────────────────────────────
    if manifest is None:
        # Scan project
        signals = extract_signals_from_project(project_path)

        # Kiem tra xem co signals nao khong
        has_signals = any(signals.values())

        if not has_signals:
            # Project rong hoac khong nhan ra duoc
            return (
                "Project nay chua co skills tu Agent Hub.\n"
                "Mo ta project de toi goi y skills phu hop: /suggest-stack"
            )

        # Chay stack matching
        ranked_stacks = match_stack(project_path=project_path)

        return generate_suggestion_message(project_path, ranked_stacks)

    # ── Truong hop B/C: Da cau hinh ─────────────────────────────────────
    updates = detect_updates(manifest)

    if updates:
        # Truong hop B: Co cap nhat
        return generate_update_message(updates)

    # Truong hop C: Moi thu deu moi nhat
    return None


# ── Entry point (duoc goi tu hook) ───────────────────────────────────────────

def main():
    """
    Hook entry point.

    Cach su dung trong Claude Code settings:

    ```json
    {
      "hooks": {
        "session_start": [
          {
            "command": "python3 ~/Agent_Hub/agent-hub-index/scripts/proactive-detect.py",
            "timeout": 5000
          }
        ]
      }
    }
    ```

    QUAN TRONG:
    - Timeout 5 giay de khong lam cham session start
    - Output stdout duoc inject vao session context
    - Khong output gi = khong can thiep
    """
    project_path = Path.cwd()

    # Kiem tra library ton tai
    if not LIBRARY_DIR.exists():
        return  # Agent Hub chua setup, im lang

    result = proactive_detect(project_path)

    if result:
        print(result)


if __name__ == "__main__":
    main()
```

### 6.4 Do phuc tap

| Truong hop | Do phuc tap | Thoi gian thuc te |
|------------|-------------|-------------------|
| A: Chua cau hinh | O(F*D + S*(T+D+P)) | < 500ms |
| B: Co cap nhat | O(N * FileSize) | < 200ms (N=15, files nho) |
| C: Moi nhat | O(N * FileSize) | < 200ms |
| **Worst case** | **O(F*D + S*(T+D+P))** | **< 500ms (trong timeout 5s)** |

### 6.5 Cac truong hop dac biet

| Truong hop | Xu ly |
|------------|-------|
| Agent Hub chua duoc setup (LIBRARY_DIR khong ton tai) | Im lang, khong output |
| Project o ngoai home directory (VD: /tmp) | Van chay binh thuong, scan files |
| Project rong (vua `mkdir`) | Goi y dung /suggest-stack voi mo ta |
| manifest.yaml bi hong (YAML loi) | Coi nhu chua cau hinh (truong hop A) |
| Skill trong manifest da bi xoa khoi library | Bo qua skill do, khong bao loi |
| Hook timeout (> 5s) | Claude Code tu dong kill process |
| Khong co quyen doc project files | Exception duoc bat, im lang |
| Project dung nhieu ngon ngu | Stack matching van hoat dong, tra ve stack phu hop nhat |

### 6.6 Vi du minh hoa

**Vi du 1: Project moi chua cau hinh**

```
User mo Claude Code trong $HOME/my-ros2-project/
Project co: CMakeLists.txt, package.xml, launch/nav.py

Session hook chay:
  1. Kiem tra .claude/library-manifest.yaml -> KHONG TON TAI
  2. Scan project:
     - CMakeLists.txt -> cpp, phat hien ament_cmake -> ros2
     - package.xml -> ros2, robotics
     - launch/*.py -> ros2
     Signals: technologies=[cpp, ros2, python], domains=[robotics]
  3. Stack matching:
     - ros2-robotics: score=54.16
     - web-fullstack: score=5.00 (duoi nguong 20.0)
  4. Output:

"Project nay chua co skills duoc cau hinh tu Agent Hub.
Dua tren project files, toi goi y stack 'ros2-robotics' (do phu hop: 54%).

Ly do: Stack 'ros2-robotics' phu hop vi: Project co cac file: CMakeLists.txt,
package.xml; su dung technologies: cpp, python, ros2; thuoc domains: robotics.

Chay lenh sau de cai dat:
  /publish --stack ros2-robotics"
```

**Vi du 2: Project da cau hinh, co cap nhat**

```
User mo Claude Code trong $HOME/my-web-app/
Project co .claude/library-manifest.yaml voi 7 skills

Session hook chay:
  1. Kiem tra manifest -> TON TAI
  2. So sanh hash:
     - brainstorming: manifest=sha256:aaa... library=sha256:bbb... -> KHAC
     - writing-plans: match
     - executing-plans: match
     - ... (5 skills khac deu match)
  3. Output:

"1 skills co phien ban moi trong Agent Hub library:

  - brainstorming (v1 -> v2)

Chay /update-skills de cap nhat."
```

**Vi du 3: Project da cau hinh, moi nhat**

```
Session hook chay:
  1. Kiem tra manifest -> TON TAI
  2. So sanh hash: tat ca 7 skills deu match
  3. Output: (khong co gi -- session bat dau binh thuong)
```

---

## 7. Thuat toan Conflict Detection

### 7.1 Mo ta

Thuat toan phat hien xung dot giua cac skills khi publish cung nhau. Hai skills "xung dot" khi chung khong nen duoc su dung dong thoi (vi du: 2 skills cung lam chuc nang brainstorming nhung theo cach khac nhau).

Thuat toan xay dung do thi xung dot (conflict graph) va phat hien cac cap xung dot.

### 7.2 Dac ta Input/Output

```
INPUT:
  - skill_ids: list[string]        # Danh sach skills se duoc publish cung
  - catalog: dict                  # catalog.json (chua truong conflicts_with)

OUTPUT:
  ConflictReport:
    has_conflicts: boolean
    conflicts: list[ConflictPair]
    suggestion: string             # Goi y giai quyet

  ConflictPair:
    skill_a: string
    skill_b: string
    reason: string                 # Ly do xung dot
    resolution: string             # Goi y giai quyet cu the

  Neu khong co xung dot:
    { has_conflicts: false, conflicts: [], suggestion: "" }
```

### 7.3 Pseudocode

```python
#!/usr/bin/env python3
"""
conflict-detection.py -- Phat hien xung dot giua cac skills.

Duoc goi boi publish-to-project.py truoc khi thuc hien publish.
"""

from dataclasses import dataclass


@dataclass
class ConflictPair:
    skill_a: str
    skill_b: str
    reason: str
    resolution: str


@dataclass
class ConflictReport:
    has_conflicts: bool
    conflicts: list[ConflictPair]
    suggestion: str


def build_conflict_graph(
    skill_ids: list[str],
    catalog: dict,
) -> dict[str, list[tuple[str, str]]]:
    """
    Xay dung do thi xung dot (adjacency list).

    CACH HOAT DONG:
    1. Tao dict anh xa: skill_id -> catalog entry
    2. Voi moi skill, kiem tra truong conflicts_with
    3. Neu conflicts_with chua skill khac trong danh sach -> them canh

    Luu y: Do thi la VO HUONG (A xung dot B <=> B xung dot A)
    nhung ta chi can luu 1 chieu de tranh trung lap trong bao cao.

    INPUT:
      skill_ids = ["brainstorming", "old-planner", "writing-plans"]
      catalog entries:
        brainstorming.conflicts_with = ["old-planner"]
        old-planner.conflicts_with = ["brainstorming"]
        writing-plans.conflicts_with = []

    OUTPUT (adjacency list):
      {
        "brainstorming": [("old-planner", "Duoc khai bao trong conflicts_with")],
        "old-planner": [("brainstorming", "Duoc khai bao trong conflicts_with")],
      }

    Do phuc tap: O(N * C)
      N = so skills trong danh sach
      C = so luong conflicts_with trung binh moi skill
    """
    # Build lookup table
    catalog_lookup = {}
    for entry in catalog.get("entries", []):
        catalog_lookup[entry["id"]] = entry

    skill_set = set(skill_ids)
    graph: dict[str, list[tuple[str, str]]] = {sid: [] for sid in skill_ids}

    for sid in skill_ids:
        entry = catalog_lookup.get(sid)
        if not entry:
            continue

        for conflict_id in entry.get("conflicts_with", []):
            if conflict_id in skill_set:
                reason = _get_conflict_reason(entry, catalog_lookup.get(conflict_id))
                graph[sid].append((conflict_id, reason))

    return graph


def _get_conflict_reason(entry_a: dict, entry_b: dict | None) -> str:
    """
    Xac dinh ly do xung dot giua 2 skills.

    HEURISTICS:
    1. Neu cung domain + cung phase -> "Chuc nang trung lap"
    2. Neu cung usage_pattern -> "Cung thoi diem su dung"
    3. Mac dinh -> "Duoc khai bao trong conflicts_with"
    """
    if not entry_b:
        return "Duoc khai bao trong conflicts_with"

    # Kiem tra trung lap domain + phase
    shared_domains = set(entry_a.get("domains", [])) & set(entry_b.get("domains", []))
    shared_phases = set(entry_a.get("phases", [])) & set(entry_b.get("phases", []))

    if shared_domains and shared_phases:
        return (
            f"Chuc nang trung lap: cung domain ({', '.join(shared_domains)}) "
            f"va cung phase ({', '.join(shared_phases)})"
        )

    # Kiem tra usage_pattern
    if (entry_a.get("usage_pattern") and
        entry_a.get("usage_pattern") == entry_b.get("usage_pattern")):
        return f"Cung thoi diem su dung: {entry_a['usage_pattern']}"

    return "Duoc khai bao trong conflicts_with"


def detect_conflicts(
    skill_ids: list[str],
    catalog: dict,
) -> ConflictReport:
    """
    Thuat toan phat hien xung dot chinh.

    LUONG XU LY:
    1. Build conflict graph
    2. Duyet graph, tim tat ca cac cap xung dot
    3. De-duplicate (vi do thi vo huong)
    4. Tao bao cao voi goi y giai quyet

    Do phuc tap: O(N * C)
      N = so skills
      C = so conflicts_with trung binh

    Truong hop tot nhat: O(N) khi khong co xung dot nao
    Truong hop xau nhat: O(N^2) khi moi skill xung dot voi moi skill khac
      (khong xay ra trong thuc te)
    """

    # ── Buoc 1: Build conflict graph ─────────────────────────────────────
    graph = build_conflict_graph(skill_ids, catalog)

    # ── Buoc 2: Tim cac cap xung dot (de-duplicate) ─────────────────────
    seen_pairs = set()
    conflict_pairs = []

    for skill_id, neighbors in graph.items():
        for conflict_id, reason in neighbors:
            # Tao key sap xep de de-duplicate
            pair_key = tuple(sorted([skill_id, conflict_id]))

            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            resolution = _suggest_resolution(
                skill_id, conflict_id, catalog
            )

            conflict_pairs.append(ConflictPair(
                skill_a=pair_key[0],
                skill_b=pair_key[1],
                reason=reason,
                resolution=resolution,
            ))

    # ── Buoc 3: Tao bao cao ─────────────────────────────────────────────
    if not conflict_pairs:
        return ConflictReport(
            has_conflicts=False,
            conflicts=[],
            suggestion="Khong co xung dot. Tat ca skills co the dung cung nhau.",
        )

    suggestion_parts = [
        f"Phat hien {len(conflict_pairs)} xung dot.",
        "Goi y: Loai bo mot trong hai skills xung dot, hoac dung --force neu ban biet minh dang lam gi.",
    ]

    return ConflictReport(
        has_conflicts=True,
        conflicts=conflict_pairs,
        suggestion="\n".join(suggestion_parts),
    )


def _suggest_resolution(
    skill_a: str,
    skill_b: str,
    catalog: dict,
) -> str:
    """
    Goi y giai quyet xung dot giua 2 skills.

    CHIEN LUOC:
    1. Uu tien skill co stability="stable" hon "beta"/"experimental"
    2. Uu tien skill tu source co nhieu entry hon (mature hon)
    3. Uu tien skill co nhieu use_with references hon (tich hop tot hon)
    """
    catalog_lookup = {e["id"]: e for e in catalog.get("entries", [])}

    entry_a = catalog_lookup.get(skill_a, {})
    entry_b = catalog_lookup.get(skill_b, {})

    # So sanh stability
    stability_order = {"stable": 3, "beta": 2, "experimental": 1}
    stab_a = stability_order.get(entry_a.get("stability", "stable"), 0)
    stab_b = stability_order.get(entry_b.get("stability", "stable"), 0)

    if stab_a > stab_b:
        return f"Goi y giu '{skill_a}' (stability: {entry_a.get('stability')}) va loai '{skill_b}'"
    elif stab_b > stab_a:
        return f"Goi y giu '{skill_b}' (stability: {entry_b.get('stability')}) va loai '{skill_a}'"

    # So sanh so use_with
    refs_a = len(entry_a.get("use_with", []))
    refs_b = len(entry_b.get("use_with", []))

    if refs_a > refs_b:
        return f"Goi y giu '{skill_a}' (tich hop tot hon voi {refs_a} skills khac) va loai '{skill_b}'"
    elif refs_b > refs_a:
        return f"Goi y giu '{skill_b}' (tich hop tot hon voi {refs_b} skills khac) va loai '{skill_a}'"

    # Khong phan biet duoc -> de user quyet dinh
    return f"Ca hai co do uu tien tuong duong. Chon '{skill_a}' hoac '{skill_b}' tuy theo nhu cau."


# ── Entry point ──────────────────────────────────────────────────────────────

def check_and_report(
    skill_ids: list[str],
    catalog_path: str = None,
) -> bool:
    """
    Helper function cho publish-to-project.py.

    Returns:
        True neu khong co xung dot (an toan de publish)
        False neu co xung dot (can user xac nhan)
    """
    import json
    from pathlib import Path

    if catalog_path is None:
        catalog_path = Path("~/Agent_Hub/agent-hub-index/library/catalog.json").expanduser()
    else:
        catalog_path = Path(catalog_path)

    if not catalog_path.exists():
        print("CANH BAO: catalog.json khong ton tai, bo qua conflict check")
        return True

    catalog = json.loads(catalog_path.read_text())
    report = detect_conflicts(skill_ids, catalog)

    if not report.has_conflicts:
        return True

    print(f"\n{'='*50}")
    print(f"PHAT HIEN XUNG DOT")
    print(f"{'='*50}\n")

    for conflict in report.conflicts:
        print(f"  XUNG DOT: '{conflict.skill_a}' <-> '{conflict.skill_b}'")
        print(f"    Ly do: {conflict.reason}")
        print(f"    Giai quyet: {conflict.resolution}")
        print()

    print(report.suggestion)
    print()

    return False
```

### 7.4 Do phuc tap

| Giai doan | Do phuc tap | Chi tiet |
|-----------|-------------|----------|
| Build lookup table | O(E) | E = so entries trong catalog |
| Build conflict graph | O(N * C) | N = skills, C = avg conflicts_with |
| De-duplicate pairs | O(P) | P = so pairs (sap xep + hash set) |
| Generate resolution | O(1) moi pair | Lookup va so sanh |
| **Tong** | **O(E + N * C)** | Thuc te < 10ms |

### 7.5 Cac truong hop dac biet

| Truong hop | Xu ly |
|------------|-------|
| Khong co xung dot nao | Tra ve report voi has_conflicts=false |
| Skill A xung dot B nhung B khong khai bao nguoc lai | Van phat hien (chi can 1 chieu) |
| Skill trong danh sach khong co trong catalog | Bo qua (khong crash) |
| catalog.json khong ton tai | Canh bao va tra ve True (an toan de publish) |
| Xung dot vong (A->B, B->C, C->A) | Moi cap duoc bao cao rieng: A-B, B-C, A-C |
| Tat ca skills xung dot voi nhau | Bao cao N*(N-1)/2 pairs, goi y chon 1 |
| Skill xung dot voi chinh no (loi data) | Bo qua (pair_key se giong nhau) |

### 7.6 Vi du minh hoa

**Vi du 1: Co xung dot**

```python
skill_ids = ["brainstorming", "old-planner", "writing-plans", "systematic-debugging"]

# catalog.json:
# brainstorming.conflicts_with = ["old-planner"]
# old-planner.conflicts_with = ["brainstorming"]
# writing-plans.conflicts_with = []
# systematic-debugging.conflicts_with = []

# Ket qua:
report = detect_conflicts(skill_ids, catalog)
# report.has_conflicts = True
# report.conflicts = [
#   ConflictPair(
#     skill_a="brainstorming",
#     skill_b="old-planner",
#     reason="Chuc nang trung lap: cung domain (planning) va cung phase (planning)",
#     resolution="Goi y giu 'brainstorming' (stability: stable) va loai 'old-planner'"
#   )
# ]
```

Output:

```
==================================================
PHAT HIEN XUNG DOT
==================================================

  XUNG DOT: 'brainstorming' <-> 'old-planner'
    Ly do: Chuc nang trung lap: cung domain (planning) va cung phase (planning)
    Giai quyet: Goi y giu 'brainstorming' (stability: stable) va loai 'old-planner'

Phat hien 1 xung dot.
Goi y: Loai bo mot trong hai skills xung dot, hoac dung --force neu ban biet minh dang lam gi.
```

**Vi du 2: Khong co xung dot**

```python
skill_ids = ["brainstorming", "writing-plans", "systematic-debugging"]

report = detect_conflicts(skill_ids, catalog)
# report.has_conflicts = False
# report.conflicts = []
# report.suggestion = "Khong co xung dot. Tat ca skills co the dung cung nhau."
```

---

## Phu luc A: Tong hop do phuc tap

| Thuat toan | Thoi gian | Khong gian | Thoi gian thuc te |
|------------|-----------|------------|-------------------|
| Import | O(P + F) | O(F) | < 100ms |
| Build Catalog | O(N * K * T) | O(N * T) | < 500ms |
| Stack Matching | O(F*D + S*(T+D+P)) | O(S) | < 200ms |
| Publish | O(N * F) | O(F) | < 1s |
| Validation | O(N * R) | O(N) | < 100ms |
| Proactive Detection | O(F*D + S*(T+D+P)) | O(S) | < 500ms |
| Conflict Detection | O(E + N * C) | O(N) | < 10ms |

**Ghi chu ky hieu:**
- N = so entries (~50)
- F = kich thuoc file trung binh (~5KB)
- K = tong so keywords trong tables (~200)
- T = do dai text (~3000 chars)
- S = so stacks (~10)
- P = so file patterns moi stack (~7)
- D = so file can scan trong project (~15)
- R = so references trung binh moi entry (~3)
- C = so conflicts_with trung binh (~1)
- E = tong entries trong catalog

## Phu luc B: Luong du lieu tong the

```
                 +-----------------+
                 | 6 Source Projects|
                 | (~407 entries)   |
                 +--------+--------+
                          |
                    import-skill.py
                    (chon loc ~50)
                          |
                          v
                 +--------+--------+
                 |    library/      |
                 |  skills/ + agents/|
                 |  + provenance.yaml|
                 |  + enrichment.yaml|
                 +--------+--------+
                          |
                   build-catalog.py
                   (enrichment + inference)
                          |
                          v
                 +--------+--------+
                 |  catalog.json    |
                 |  collections/    |
                 |  stacks/         |
                 +--------+--------+
                          |
            +-------------+-------------+
            |                           |
     stack-matching             conflict-detection
     (Librarian agent)         (truoc khi publish)
            |                           |
            +-------------+-------------+
                          |
                  publish-to-project.py
                          |
                          v
                 +--------+--------+
                 | Target Project   |
                 | .claude/         |
                 |   skills/        |
                 |   agents/        |
                 |   library-manifest|
                 +--------+--------+
                          |
                proactive-detection
                (session hook)
                          |
                          v
                  +-------+-------+
                  | Goi y stack   |
                  | hoac thong bao|
                  | cap nhat      |
                  +---------------+
```

## Phu luc C: Kiem tra nhanh (Quick Reference)

### Lenh su dung thuong ngay

```bash
# Import skill tu source project
python import-skill.py superpowers brainstorming
python import-skill.py gstack investigate --force
python import-skill.py everything-claude-code commit-message --dry-run

# Build catalog
python build-catalog.py

# Publish stack vao project
python publish-to-project.py /path/to/project --stack web-fullstack
python publish-to-project.py /path/to/project --skills brainstorming writing-plans
python publish-to-project.py /path/to/project --stack ros2-robotics --dry-run

# Validate library
python validate.py
python validate.py --strict
python validate.py --json

# Tim kiem skills (co san)
python scripts/search.py "ROS2 LiDAR camera calibration"
python scripts/search.py "web app React Postgres" --phases planning,development
```

### File layout

```
~/Agent_Hub/agent-hub-index/
+-- library/
|   +-- skills/
|   |   +-- brainstorming/
|   |   |   +-- SKILL.md
|   |   |   +-- provenance.yaml
|   |   |   +-- enrichment.yaml (tuy chon)
|   |   +-- systematic-debugging/
|   |       +-- SKILL.md
|   |       +-- provenance.yaml
|   +-- agents/
|       +-- librarian.md
|       +-- librarian.provenance.yaml
|       +-- code-reviewer.md
|       +-- code-reviewer.provenance.yaml
+-- catalog.json
+-- collections/
|   +-- core-workflow.yaml
|   +-- testing-suite.yaml
+-- stacks/
|   +-- web-fullstack.yaml
|   +-- ros2-robotics.yaml
+-- domain-keywords.json
+-- scripts/
|   +-- import-skill.py
|   +-- build-catalog.py
|   +-- publish-to-project.py
|   +-- validate.py
|   +-- proactive-detect.py
|   +-- conflict-detection.py
|   +-- search.py (co san)
+-- build-registry.py (co san -- scan tat ca source projects)
+-- registry.json (co san -- full registry cua 407 entries)
+-- registry-index.json (co san -- lightweight index)
+-- docs/
    +-- 03-algorithms.md (tai lieu nay)
```
