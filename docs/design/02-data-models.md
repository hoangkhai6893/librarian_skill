# 02 — Data Models

> Tai lieu mo ta chi tiet toan bo cac schema du lieu trong he thong **Agent Hub** — thu vien ca nhan ve Skills/Agents voi AI Librarian.
>
> Muc dich: Bat ky lap trinh vien nao doc tai lieu nay deu co the viet code validation (JSON Schema, Zod, Pydantic, v.v.) ma khong can hoi them.

---

## Muc luc

1. [catalog.json — Danh muc thu vien chinh](#1-catalogjson--danh-muc-thu-vien-chinh)
2. [provenance.yaml — Truy xuat nguon goc](#2-provenanceyaml--truy-xuat-nguon-goc)
3. [library-manifest.yaml — Phieu muon sach](#3-library-manifestyaml--phieu-muon-sach)
4. [Collection YAML — Nhom chu de](#4-collection-yaml--nhom-chu-de)
5. [Stack YAML — Bo kit du an](#5-stack-yaml--bo-kit-du-an)
6. [SKILL.md — Dinh dang file Skill](#6-skillmd--dinh-dang-file-skill)
7. [Agent .md — Dinh dang file Agent](#7-agent-md--dinh-dang-file-agent)
8. [So do quan he giua cac schema](#8-so-do-quan-he-giua-cac-schema)
9. [Phu luc: Controlled Vocabularies](#9-phu-luc-controlled-vocabularies)

---

## 1. catalog.json — Danh muc thu vien chinh

### 1.1 Mo ta

`catalog.json` la file trung tam cua thu vien duoc curate (~50 entry). Day la "the muc luc" ma AI Librarian su dung de tim kiem, goi y va ket hop cac skill/agent cho nguoi dung. Moi entry dai dien cho mot skill, agent, hoac command da duoc danh gia va chon loc tu cac source project.

### 1.2 Vi tri file

```
Agent_Hub/library/catalog.json
```

### 1.3 Cau truc tong the

```json
{
  "version": 1,
  "updated_at": "2026-03-30T10:00:00Z",
  "entries": [
    { /* CatalogEntry */ }
  ]
}
```

### 1.4 Bang mo ta truong — CatalogEntry

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `id` | `string` | **Co** | Dinh danh duy nhat, dung lam khoa chinh. Format: lowercase, dung dau gach ngang de noi cac tu. | Regex: `^[a-z][a-z0-9-]*$`. Toi da 64 ky tu. Khong duoc trung voi bat ky `id` nao khac trong catalog. | `"systematic-debugging"` |
| `name` | `string` | **Co** | Ten hien thi than thien cho nguoi dung. | Toi thieu 2 ky tu, toi da 100 ky tu. | `"Systematic Debugging"` |
| `type` | `string` | **Co** | Loai entry. | Mot trong: `"skill"`, `"agent"`, `"command"`. | `"skill"` |
| `from` | `string` | **Co** | Du an nguon goc da cung cap entry nay. | Mot trong: `"superpowers"`, `"everything-claude-code"`, `"gstack"`, `"get-shit-done"`, `"openspec"`, `"learn-claude-code"`. | `"superpowers"` |
| `description` | `string` | **Co** | Mo ta ngan gon chuc nang cua entry (1-2 cau). | Toi thieu 10 ky tu, toi da 500 ky tu. | `"Huong dan debug co he thong: thu thap chung cu, lap gia thuyet, kiem chung tung buoc."` |
| `domains` | `string[]` | **Co** | Cac linh vuc ma entry nay ap dung. | Moi phan tu phai thuoc Controlled Vocabulary `DOMAINS` (xem Phu luc). Mang khong rong, toi da 5 phan tu. | `["debugging", "workflow"]` |
| `technologies` | `string[]` | **Co** | Cac cong nghe lien quan. | Moi phan tu phai thuoc Controlled Vocabulary `TECHNOLOGIES` (xem Phu luc). Co the la mang rong `[]` neu entry khong gioi han cong nghe cu the. Toi da 10 phan tu. | `["python", "typescript"]` |
| `phases` | `string[]` | **Co** | Cac giai doan phat trien phan mem ma entry nay ho tro. | Moi phan tu phai thuoc Controlled Vocabulary `PHASES` (xem Phu luc). Mang khong rong, toi da 5 phan tu. | `["debugging", "testing"]` |
| `project_types` | `string[]` | **Co** | Cac loai du an phu hop. | Moi phan tu phai thuoc Controlled Vocabulary `PROJECT_TYPES` (xem Phu luc). Dung `["any"]` neu ap dung cho moi loai du an. Toi da 5 phan tu. | `["any"]` |
| `complexity` | `string` | **Co** | Muc do phuc tap/kinh nghiem can thiet de su dung entry. | Mot trong: `"beginner"`, `"intermediate"`, `"advanced"`. | `"intermediate"` |
| `use_with` | `string[]` | **Co** | Danh sach `id` cua cac entry bo sung — nen dung kem de tang hieu qua. | Moi phan tu phai la `id` ton tai trong catalog. Co the la mang rong `[]`. Khong duoc chua chinh `id` cua entry hien tai. | `["brainstorming", "code-review"]` |
| `conflicts_with` | `string[]` | **Co** | Danh sach `id` cua cac entry xung dot — khong nen dung dong thoi. | Moi phan tu phai la `id` ton tai trong catalog. Co the la mang rong `[]`. Khong duoc chua chinh `id` cua entry hien tai. | `["quick-fix-mode"]` |
| `superseded_by` | `string \| null` | **Co** | Neu entry da bi thay the boi entry khac, ghi `id` cua entry moi. Neu chua bi thay the, ghi `null`. | Neu khac `null`, gia tri phai la `id` ton tai trong catalog va khong duoc tro ve chinh minh. | `null` |
| `usage_pattern` | `string` | **Co** | Cach entry duoc su dung trong workflow. | Mot trong: `"prerequisite"` (can chay truoc cac entry khac), `"standalone"` (dung doc lap), `"companion"` (dung kem entry khac), `"optional"` (tuy chon, khong bat buoc). | `"standalone"` |
| `invocation_style` | `string` | **Co** | Cach entry duoc kich hoat. | Mot trong: `"explicit"` (nguoi dung goi truc tiep), `"proactive"` (AI tu dong goi khi phat hien nhu cau), `"background"` (chay ngam, khong can tuong tac). | `"explicit"` |
| `curator_notes` | `string` | **Co** | Ghi chu cua nguoi quan ly thu vien: tai sao entry nay co gia tri, khi nao KHONG nen dung. | Toi thieu 10 ky tu, toi da 1000 ky tu. | `"Rat hieu qua cho bug phuc tap. Khong can thiet cho loi don gian nhu typo hay loi cu phap."` |
| `outputs` | `string[]` | **Co** | Cac loai artifact ma entry tao ra. | Cac gia tri thuong gap: `"design-doc"`, `"plan"`, `"test-suite"`, `"code-review"`, `"implementation"`, `"debug-report"`, `"documentation"`, `"config"`, `"migration"`, `"refactored-code"`, `"api-spec"`, `"deployment-script"`. Co the la mang rong `[]`. | `["debug-report"]` |
| `consumes` | `string[]` | **Co** | Cac loai artifact ma entry can lam dau vao. | Cung su dung controlled vocabulary nhu `outputs`. Co the la mang rong `[]`. | `["implementation"]` |

### 1.5 Quy tac validation

1. **Tinh duy nhat cua `id`**: Khong duoc co hai entry nao co cung `id`.
2. **Tham chieu hop le**: Tat ca `id` trong `use_with`, `conflicts_with`, va `superseded_by` phai tro den entry ton tai trong `entries`.
3. **Khong tu tham chieu**: `use_with` va `conflicts_with` khong duoc chua `id` cua chinh entry do.
4. **Doi xung cua `conflicts_with`**: Neu A co `conflicts_with: ["B"]` thi B cung phai co `conflicts_with: ["A"]`.
5. **Mang `domains` khong rong**: Moi entry phai co it nhat 1 domain.
6. **Mang `phases` khong rong**: Moi entry phai co it nhat 1 phase.
7. **Entry bi thay the**: Neu `superseded_by` khac `null`, entry do van ton tai trong catalog nhung AI Librarian se uu tien goi y entry moi hon.
8. **Format `id`**: Chi chua ky tu `a-z`, `0-9`, va dau `-`. Bat dau bang chu cai. Khong ket thuc bang dau `-`.

### 1.6 Vi du hoan chinh

```json
{
  "version": 1,
  "updated_at": "2026-03-30T10:00:00Z",
  "entries": [
    {
      "id": "systematic-debugging",
      "name": "Systematic Debugging",
      "type": "skill",
      "from": "superpowers",
      "description": "Huong dan debug co he thong: thu thap chung cu, lap gia thuyet, kiem chung tung buoc thay vi doan mua va thu sai.",
      "domains": ["debugging", "workflow"],
      "technologies": [],
      "phases": ["debugging"],
      "project_types": ["any"],
      "complexity": "intermediate",
      "use_with": ["brainstorming", "code-review"],
      "conflicts_with": [],
      "superseded_by": null,
      "usage_pattern": "standalone",
      "invocation_style": "proactive",
      "curator_notes": "Day la skill quan trong nhat khi gap bug phuc tap. AI se tu dong kich hoat khi phat hien nguoi dung dang debug. Khong can thiet cho loi don gian nhu typo hay loi cu phap co thong bao ro rang.",
      "outputs": ["debug-report"],
      "consumes": ["implementation"]
    },
    {
      "id": "tdd-workflow",
      "name": "TDD Workflow",
      "type": "skill",
      "from": "everything-claude-code",
      "description": "Quy trinh Test-Driven Development: viet test truoc, implement sau, refactor de dat green.",
      "domains": ["testing", "workflow"],
      "technologies": ["typescript", "python"],
      "phases": ["development", "testing"],
      "project_types": ["web-fullstack", "api-service", "cli-tool"],
      "complexity": "intermediate",
      "use_with": ["code-review"],
      "conflicts_with": [],
      "superseded_by": null,
      "usage_pattern": "standalone",
      "invocation_style": "explicit",
      "curator_notes": "Ap dung tot cho cac feature moi co logic ro rang. Khong nen ep dung khi lam prototype nhanh hoac kham pha y tuong.",
      "outputs": ["test-suite", "implementation"],
      "consumes": ["plan"]
    },
    {
      "id": "security-audit",
      "name": "Security Audit Agent",
      "type": "agent",
      "from": "get-shit-done",
      "description": "Agent chuyen kiem tra bao mat: quet OWASP Top 10, phan tich dependency, va kiem tra cau hinh.",
      "domains": ["security"],
      "technologies": [],
      "phases": ["review", "testing"],
      "project_types": ["web-fullstack", "api-service"],
      "complexity": "advanced",
      "use_with": ["code-review"],
      "conflicts_with": [],
      "superseded_by": null,
      "usage_pattern": "companion",
      "invocation_style": "explicit",
      "curator_notes": "Nen chay truoc moi lan deploy len production. Tieu ton nhieu token (model opus). Khong can thiet cho du an noi bo khong co du lieu nhay cam.",
      "outputs": ["code-review"],
      "consumes": ["implementation"]
    }
  ]
}
```

### 1.7 Quan he voi cac schema khac

- `catalog.json` la nguon su that duy nhat (single source of truth) cho cac `id`. Tat ca cac schema khac tham chieu toi `id` trong catalog.
- `provenance.yaml` theo doi nguon goc cua moi entry co trong catalog.
- `Collection YAML` va `Stack YAML` tham chieu `id` tu catalog trong danh sach entries cua chung.
- `library-manifest.yaml` ghi lai cac entry da duoc publish vao du an, cung tham chieu theo `id`.

---

## 2. provenance.yaml — Truy xuat nguon goc

### 2.1 Mo ta

Moi entry trong catalog co mot file `provenance.yaml` tuong ung, theo doi chinh xac entry do duoc import tu dau, phien ban nao, ai import, va da bi tuy chinh hay chua. Day la co che dam bao traceability — biet duoc moi skill/agent den tu dau de co the dong bo lai khi source project cap nhat.

### 2.2 Vi tri file

```
Agent_Hub/library/provenance/{entry-id}.yaml
```

Trong do `{entry-id}` la truong `id` tuong ung trong `catalog.json`.

### 2.3 Bang mo ta truong

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `source_project` | `string` | **Co** | Ten du an nguon goc. | Phai la mot trong cac gia tri hop le cua truong `from` trong catalog: `"superpowers"`, `"everything-claude-code"`, `"gstack"`, `"get-shit-done"`, `"openspec"`, `"learn-claude-code"`. | `"superpowers"` |
| `source_path` | `string` | **Co** | Duong dan tuong doi trong du an nguon, tro toi file goc. | Phai la duong dan tuong doi hop le (khong bat dau bang `/`). Phai ket thuc bang `.md`. | `"skills/systematic-debugging/SKILL.md"` |
| `source_version` | `string` | **Co** | Phien ban cua du an nguon tai thoi diem import. Co the la git tag, commit hash (7+ ky tu), hoac semantic version. | Regex: `^(v?\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?|[a-f0-9]{7,40})$`. | `"v2.1.0"` |
| `imported_at` | `string` | **Co** | Thoi diem import, dinh dang ISO 8601 voi timezone. | Regex: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$`. | `"2026-03-15T08:30:00Z"` |
| `imported_by` | `string` | **Co** | Nguoi hoac he thong thuc hien import. | Khong rong. Toi da 100 ky tu. | `"dkhai"` |
| `last_synced` | `string` | **Co** | Lan dong bo cuoi cung voi source project. | Cung dinh dang ISO 8601 nhu `imported_at`. Phai >= `imported_at`. | `"2026-03-28T14:00:00Z"` |
| `customized` | `boolean` | **Co** | `true` neu noi dung SKILL.md/Agent .md da bi chinh sua sau khi import (so voi ban goc). | Phai la `true` hoac `false`. | `false` |
| `notes` | `string` | **Co** | Ghi chu ve ly do import, cac tuy chinh da thuc hien (neu co), hoac luu y dac biet. | Co the la chuoi rong `""`. Toi da 2000 ky tu. | `"Import vi day la skill debug tot nhat. Da chinh sua phan ví du cho phu hop du an ROS2."` |

### 2.4 Quy tac validation

1. **Tuong ung 1-1 voi catalog**: Moi file `provenance/{entry-id}.yaml` phai co entry tuong ung trong `catalog.json` voi cung `id`.
2. **Nhat quan voi catalog**: Truong `source_project` phai khop voi truong `from` cua entry tuong ung trong catalog.
3. **Thu tu thoi gian**: `last_synced` phai lon hon hoac bang `imported_at`.
4. **Ghi chu khi tuy chinh**: Neu `customized` la `true`, truong `notes` khong duoc rong — phai giai thich da tuy chinh nhung gi.
5. **Duong dan ton tai**: `source_path` nen tro den file thuc su ton tai trong du an nguon (validation nay co the soft-check).

### 2.5 Vi du hoan chinh

```yaml
# provenance/systematic-debugging.yaml
source_project: "superpowers"
source_path: "skills/systematic-debugging/SKILL.md"
source_version: "v2.1.0"
imported_at: "2026-03-15T08:30:00Z"
imported_by: "dkhai"
last_synced: "2026-03-28T14:00:00Z"
customized: false
notes: "Core debugging skill — import nguyen ban goc. Phu hop cho moi du an."
```

```yaml
# provenance/ros2-navigation-planner.yaml
source_project: "gstack"
source_path: "ros2-navigation/SKILL.md"
source_version: "a1b2c3d"
imported_at: "2026-03-10T12:00:00+07:00"
imported_by: "dkhai"
last_synced: "2026-03-10T12:00:00+07:00"
customized: true
notes: "Da them vi du cu the cho du an AGV trong nha xuong. Bo phan navigation outdoor vi khong can thiet."
```

### 2.6 Quan he voi cac schema khac

- Moi `provenance.yaml` tham chieu nguoc ve mot entry trong `catalog.json` thong qua ten file (trung voi `id`).
- Truong `source_project` phai khop voi truong `from` cua catalog entry.
- Khi AI Librarian goi y dong bo (sync), no doc `last_synced` va `source_version` de xac dinh co phien ban moi hay khong.

---

## 3. library-manifest.yaml — Phieu muon sach

### 3.1 Mo ta

Moi du an (project) su dung Agent Hub se co mot file `library-manifest.yaml` tai root. Day la "phieu muon sach" — ghi lai nhung skill/agent nao tu thu vien da duoc publish (cai dat) vao du an nay, tu luc nao, phien ban nao. AI Librarian doc file nay de biet du an dang dung nhung gi va goi y bo sung hoac cap nhat.

### 3.2 Vi tri file

```
<project-root>/library-manifest.yaml
```

### 3.3 Bang mo ta truong — Root level

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `schema_version` | `integer` | **Co** | Phien ban schema cua file nay. Hien tai luon la `1`. | Phai bang `1`. Khi schema thay doi trong tuong lai, gia tri nay se tang len. | `1` |
| `library_source` | `string` | **Co** | Duong dan tuyet doi hoac tuong doi den thu muc `library` cua Agent Hub. | Khong rong. Nen la duong dan tuyet doi de tranh loi khi chuyen may. | `"$HOME/Agent_Hub/library"` |
| `created_at` | `string` | **Co** | Thoi diem tao file manifest lan dau, ISO 8601. | Dinh dang ISO 8601 voi timezone. | `"2026-03-01T09:00:00Z"` |
| `updated_at` | `string` | **Co** | Thoi diem cap nhat cuoi cung cua manifest (bat ky thay doi nao), ISO 8601. | Dinh dang ISO 8601 voi timezone. Phai >= `created_at`. | `"2026-03-28T16:30:00Z"` |
| `stack` | `string \| null` | **Co** | ID cua stack da duoc ap dung (neu co). Neu du an khong dung stack nao, ghi `null`. | Neu khac `null`, phai la `id` hop le cua mot Stack YAML ton tai. | `"ros2-autonomous"` |
| `entries` | `ManifestEntry[]` | **Co** | Danh sach cac entry da duoc publish vao du an. | Mang co the rong `[]`. Khong duoc co 2 entry trung `id`. | *(Xem bang duoi)* |

### 3.4 Bang mo ta truong — ManifestEntry

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `id` | `string` | **Co** | ID cua entry da publish, tham chieu den `catalog.json`. | Phai khop voi `id` ton tai trong `catalog.json`. Regex: `^[a-z][a-z0-9-]*$`. | `"systematic-debugging"` |
| `type` | `string` | **Co** | Loai entry. | Mot trong: `"skill"`, `"agent"`. (Command khong duoc publish vao manifest vi duoc goi truc tiep.) | `"skill"` |
| `from` | `string` | **Co** | Du an nguon goc. | Phai khop voi truong `from` cua entry tuong ung trong `catalog.json`. | `"superpowers"` |
| `published_at` | `string` | **Co** | Thoi diem publish vao du an nay, ISO 8601. | Dinh dang ISO 8601 voi timezone. | `"2026-03-15T10:00:00Z"` |
| `version` | `string` | **Co** | Phien ban cua entry tai thoi diem publish. | Khong rong. Co the la semantic version hoac git commit hash. | `"v2.1.0"` |

### 3.5 Quy tac validation

1. **`schema_version` phai bang `1`**: Hien tai chi co phien ban 1.
2. **`id` duy nhat trong `entries`**: Khong duoc co 2 ManifestEntry co cung `id`.
3. **Tham chieu hop le**: Moi `id` trong `entries` phai ton tai trong `catalog.json`.
4. **Nhat quan `type` va `from`**: Cac truong `type` va `from` phai khop voi entry tuong ung trong catalog.
5. **Thu tu thoi gian**: `updated_at` >= `created_at`. `published_at` cua moi entry phai >= `created_at` cua manifest.
6. **`type` chi co `skill` hoac `agent`**: Kieu `command` khong xuat hien trong manifest vi command duoc goi truc tiep tu catalog, khong can publish.
7. **Stack nhat quan**: Neu `stack` khac `null`, tat ca `core_skills` cua stack do nen xuat hien trong `entries` (validation warning, khong phai error).

### 3.6 Vi du hoan chinh

```yaml
# <project-root>/library-manifest.yaml
schema_version: 1
library_source: "$HOME/Agent_Hub/library"
created_at: "2026-03-01T09:00:00Z"
updated_at: "2026-03-28T16:30:00Z"
stack: "ros2-autonomous"

entries:
  - id: "systematic-debugging"
    type: "skill"
    from: "superpowers"
    published_at: "2026-03-15T10:00:00Z"
    version: "v2.1.0"

  - id: "tdd-workflow"
    type: "skill"
    from: "everything-claude-code"
    published_at: "2026-03-16T11:00:00Z"
    version: "v1.3.2"

  - id: "security-audit"
    type: "agent"
    from: "get-shit-done"
    published_at: "2026-03-20T14:30:00Z"
    version: "v1.0.0"
```

### 3.7 Quan he voi cac schema khac

- Moi `id` trong `entries` tham chieu den `catalog.json`.
- Truong `stack` tham chieu den `Stack YAML` (theo `id` cua stack).
- Truong `version` cua ManifestEntry nen khop voi `source_version` trong `provenance.yaml` tuong ung.
- AI Librarian so sanh `version` trong manifest voi phien ban moi nhat trong provenance de goi y cap nhat.

---

## 4. Collection YAML — Nhom chu de

### 4.1 Mo ta

Collection la nhom chu de duoc curate — mot tap hop cac entry tu catalog duoc nhom lai theo muc dich su dung cu the, voi thu tu va vai tro ro rang. Vi du: "Bo skill cho review code", "Workflow phat trien web fullstack", "Bo cong cu cho team moi bat dau". Collection giup nguoi dung nhanh chong tim duoc bo skill/agent phu hop thay vi chon tung cai mot.

### 4.2 Vi tri file

```
Agent_Hub/library/collections/{collection-id}.yaml
```

### 4.3 Bang mo ta truong — Root level

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `id` | `string` | **Co** | Dinh danh duy nhat cua collection. | Regex: `^[a-z][a-z0-9-]*$`. Toi da 64 ky tu. Khong trung voi collection nao khac. | `"code-quality-essentials"` |
| `name` | `string` | **Co** | Ten hien thi. | Toi thieu 2 ky tu, toi da 100 ky tu. | `"Code Quality Essentials"` |
| `curator` | `string` | **Co** | Nguoi tao/quan ly collection nay. | Khong rong. Toi da 100 ky tu. | `"dkhai"` |
| `description` | `string` | **Co** | Mo ta collection nay la gi va danh cho ai. | Toi thieu 10 ky tu, toi da 500 ky tu. | `"Bo 5 skill/agent thiet yeu de dam bao chat luong code cho moi du an."` |
| `curator_notes` | `string` | **Co** | Ghi chu co quan diem cua nguoi curate — tai sao chon cac entry nay, khi nao nen/khong nen dung collection nay. | Toi thieu 10 ky tu, toi da 1000 ky tu. | `"Collection nay la xuong song cua moi du an nghiem tuc. Tuy nhien voi prototype nhanh (< 1 ngay), chi can dung brainstorming va systematic-debugging la du."` |
| `entries` | `CollectionEntry[]` | **Co** | Danh sach cac entry trong collection, co thu tu va vai tro. | Mang khong rong, toi thieu 2 entry. Khong duoc co 2 entry trung `id`. | *(Xem bang duoi)* |
| `tags` | `string[]` | **Co** | Cac tag giup tim kiem va phan loai collection. | Mang khong rong, toi thieu 1 tag. Moi tag la lowercase, chi chua `a-z`, `0-9`, dau `-`. Toi da 10 tags. | `["quality", "review", "essential"]` |
| `complexity` | `string` | **Co** | Muc do phuc tap chung cua collection. | Mot trong: `"beginner"`, `"intermediate"`, `"advanced"`. | `"intermediate"` |
| `project_types` | `string[]` | **Co** | Cac loai du an phu hop voi collection nay. | Moi phan tu phai thuoc Controlled Vocabulary `PROJECT_TYPES` (xem Phu luc). Dung `["any"]` neu phu hop moi loai. Toi da 5 phan tu. | `["any"]` |

### 4.4 Bang mo ta truong — CollectionEntry

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `id` | `string` | **Co** | ID cua entry, phai ton tai trong `catalog.json`. | Regex: `^[a-z][a-z0-9-]*$`. Phai ton tai trong catalog. | `"code-review"` |
| `role` | `string` | **Co** | Vai tro cua entry trong collection nay. | Khong rong. Toi da 200 ky tu. Mo ta ngan gon entry lam gi trong boi canh cua collection. | `"Kiem tra chat luong code sau khi implement"` |
| `sequence` | `integer` | **Co** | Thu tu su dung trong collection (1-based). | So nguyen duong, bat dau tu 1. Khong duoc co 2 entry co cung `sequence`. Phai lien tuc (1, 2, 3... khong duoc nhay). | `3` |
| `when` | `string` | Khong | Dieu kien hoac thoi diem nen su dung entry nay. | Toi da 300 ky tu. Bo qua hoac de `null` neu khong can. | `"Sau khi hoan thanh implement va truoc khi tao PR"` |
| `note` | `string` | Khong | Ghi chu bo sung. | Toi da 500 ky tu. Bo qua hoac de `null` neu khong can. | `"Co the bo qua cho cac hotfix khan cap"` |

### 4.5 Quy tac validation

1. **`id` collection duy nhat**: Khong trung voi bat ky collection nao khac.
2. **Entry ton tai trong catalog**: Moi `id` trong `entries` phai ton tai trong `catalog.json`.
3. **`id` entry khong trung trong collection**: Mot entry chi xuat hien toi da 1 lan trong 1 collection.
4. **`sequence` lien tuc va bat dau tu 1**: Voi n entry, cac gia tri sequence phai la 1, 2, 3, ..., n.
5. **Toi thieu 2 entry**: Collection phai co it nhat 2 entry (neu chi co 1, khong can tao collection).
6. **Tags hop le**: Moi tag chi chua `a-z`, `0-9`, va `-`.
7. **Entry khong bi superseded**: Cac entry trong collection khong nen co `superseded_by` khac `null` trong catalog (validation warning).

### 4.6 Vi du hoan chinh

```yaml
# collections/code-quality-essentials.yaml
id: "code-quality-essentials"
name: "Code Quality Essentials"
curator: "dkhai"
description: "Bo 5 skill/agent thiet yeu de dam bao chat luong code cho moi du an — tu luc len y tuong den khi review xong."
curator_notes: >
  Day la collection nen ap dung cho moi du an nghiem tuc.
  Thu tu da duoc sap xep theo luong cong viec tu nhien:
  brainstorm truoc, implement giua, review cuoi.
  Voi prototype nhanh (< 1 ngay), chi can entry 1 va 4 la du.

entries:
  - id: "brainstorming"
    role: "Kham pha y tuong va yeu cau truoc khi code"
    sequence: 1
    when: "Luon luon bat dau voi buoc nay"
    note: null

  - id: "tdd-workflow"
    role: "Viet test truoc de dinh huong implementation"
    sequence: 2
    when: "Sau khi da co ke hoach tu brainstorming"
    note: "Bo qua neu lam UI prototype"

  - id: "systematic-debugging"
    role: "Giai quyet bug co he thong trong qua trinh phat trien"
    sequence: 3
    when: "Khi gap bug trong luc implement"
    note: null

  - id: "code-review"
    role: "Kiem tra chat luong code sau khi implement"
    sequence: 4
    when: "Sau khi hoan thanh implement va truoc khi tao PR"
    note: "Co the bo qua cho cac hotfix khan cap"

  - id: "security-audit"
    role: "Kiem tra bao mat truoc khi deploy"
    sequence: 5
    when: "Truoc moi lan deploy len staging hoac production"
    note: "Bat buoc cho du an co du lieu nguoi dung"

tags: ["quality", "review", "essential", "workflow"]
complexity: "intermediate"
project_types: ["any"]
```

### 4.7 Quan he voi cac schema khac

- Moi `id` trong `entries` tham chieu den `catalog.json`.
- Collection khong phu thuoc vao Stack, nhung mot Stack co the goi y cac Collection lien quan.
- AI Librarian su dung `tags`, `complexity`, va `project_types` de match collection voi nhu cau nguoi dung.

---

## 5. Stack YAML — Bo kit du an

### 5.1 Mo ta

Stack la bo kit du an (pre-built project kit) — mot cau hinh san co ket hop cac skill/agent tu catalog de phuc vu mot loai du an cu the. Vi du: "ROS2 Autonomous Robot", "Web Fullstack TypeScript", "ML Research Pipeline". Stack bao gom tin hieu nhan dang du an (project signals), skill co ban (core), skill quy trinh (workflow), va huong dan kich hoat (activation).

### 5.2 Vi tri file

```
Agent_Hub/library/stacks/{stack-id}.yaml
```

### 5.3 Bang mo ta truong — Root level

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `id` | `string` | **Co** | Dinh danh duy nhat cua stack. | Regex: `^[a-z][a-z0-9-]*$`. Toi da 64 ky tu. | `"ros2-autonomous"` |
| `name` | `string` | **Co** | Ten hien thi. | Toi thieu 2 ky tu, toi da 100 ky tu. | `"ROS2 Autonomous Robot"` |
| `description` | `string` | **Co** | Mo ta muc dich va doi tuong cua stack. | Toi thieu 10 ky tu, toi da 500 ky tu. | `"Bo kit day du cho du an robot tu hanh su dung ROS2, bao gom navigation, perception va system integration."` |
| `project_signals` | `ProjectSignals` | **Co** | Cac tin hieu de AI Librarian tu dong nhan dang loai du an. | Xem bang duoi. | *(Xem bang duoi)* |
| `core_skills` | `CoreSkillRef[]` | **Co** | Cac skill co ban — luon duoc cai dat khi dung stack nay. | Mang khong rong, toi thieu 1 entry. Moi `id` phai ton tai trong catalog. | *(Xem bang duoi)* |
| `workflow_skills` | `WorkflowSkillRef[]` | **Co** | Cac skill quy trinh — dung trong cac giai doan cu the. | Co the la mang rong `[]`. Moi `id` phai ton tai trong catalog. | *(Xem bang duoi)* |
| `ship_cycle` | `ShipCycleRef[]` | Khong | Cac skill cho chu ky ship (deploy, monitor, v.v.). | Co the bo qua hoac de `[]`. Moi `id` phai ton tai trong catalog. | *(Xem bang duoi)* |
| `activation` | `ActivationCommands` | **Co** | Cau lenh cai dat cho tung source project. | Xem bang duoi. | *(Xem bang duoi)* |

### 5.4 Bang mo ta truong — ProjectSignals

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `technologies` | `string[]` | **Co** | Cac cong nghe dac trung cua loai du an nay. | Moi phan tu thuoc Controlled Vocabulary `TECHNOLOGIES`. Mang khong rong. | `["python", "cpp", "ros2"]` |
| `domains` | `string[]` | **Co** | Cac domain dac trung. | Moi phan tu thuoc Controlled Vocabulary `DOMAINS`. Mang khong rong. | `["robotics", "ai-ml"]` |
| `file_patterns` | `string[]` | **Co** | Cac ten file/thu muc dac trung ma AI Librarian dung de nhan dang du an. Khi thay cac file nay trong du an, AI se goi y stack tuong ung. | Moi phan tu la glob pattern hoac ten file cu the. Mang khong rong. | `["CMakeLists.txt", "package.xml", "*.launch.py", "colcon.meta"]` |

### 5.5 Bang mo ta truong — CoreSkillRef

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `id` | `string` | **Co** | ID cua skill trong catalog. | Phai ton tai trong `catalog.json`. | `"ros2-node-architecture"` |
| `why` | `string` | **Co** | Giai thich ngan gon (1 cau) tai sao skill nay la core cho stack. | Toi thieu 5 ky tu, toi da 200 ky tu. | `"Moi du an ROS2 can thiet ke node architecture dung chuan."` |

### 5.6 Bang mo ta truong — WorkflowSkillRef

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `id` | `string` | **Co** | ID cua skill trong catalog. | Phai ton tai trong `catalog.json`. | `"systematic-debugging"` |
| `when` | `string` | **Co** | Khi nao nen su dung skill nay trong quy trinh lam viec. | Toi thieu 5 ky tu, toi da 300 ky tu. | `"Khi gap loi runtime hoac behavior bat thuong trong robot."` |

### 5.7 Bang mo ta truong — ShipCycleRef

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `id` | `string` | **Co** | ID cua skill trong catalog. | Phai ton tai trong `catalog.json`. | `"deployment-checklist"` |
| `when` | `string` | **Co** | Khi nao su dung trong chu ky ship. | Toi thieu 5 ky tu, toi da 300 ky tu. | `"Truoc moi lan flash firmware len robot thuc te."` |

### 5.8 Bang mo ta truong — ActivationCommands

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `superpowers` | `string` | **Co** | Lenh cai dat skill tu du an superpowers. | Khong rong. La cau lenh shell hop le. | `"claude skill add /path/to/superpowers/skills/systematic-debugging"` |
| `everything-claude-code` | `string` | **Co** | Lenh cai dat tu everything-claude-code. | Khong rong. La cau lenh shell hop le. | `"node scripts/install.js --module tdd-workflow"` |
| `gstack` | `string` | **Co** | Lenh cai dat tu gstack. | Khong rong. La cau lenh shell hop le. | `"gstack install ros2-navigation"` |
| `get-shit-done` | `string` | **Co** | Lenh cai dat tu get-shit-done. | Khong rong. La cau lenh shell hop le. | `"gsd install security-audit"` |

### 5.9 Quy tac validation

1. **`id` stack duy nhat**: Khong trung voi bat ky stack nao khac.
2. **Tat ca `id` tham chieu hop le**: Moi `id` trong `core_skills`, `workflow_skills`, va `ship_cycle` phai ton tai trong `catalog.json`.
3. **Khong trung lap entry**: Mot `id` chi xuat hien mot lan trong toan bo stack (tren tat ca `core_skills`, `workflow_skills`, va `ship_cycle`).
4. **Khong xung dot**: Cac entry trong cung stack khong duoc xung dot voi nhau (kiem tra `conflicts_with` trong catalog).
5. **Core skills khong rong**: Phai co it nhat 1 core skill.
6. **Project signals khong rong**: Tat ca mang trong `project_signals` phai co it nhat 1 phan tu.
7. **Activation day du**: Tat ca 4 truong trong `activation` phai co gia tri (du co the la lenh placeholder nhu `"# khong ap dung"` neu source do khong co skill tuong ung).

### 5.10 Vi du hoan chinh

```yaml
# stacks/ros2-autonomous.yaml
id: "ros2-autonomous"
name: "ROS2 Autonomous Robot"
description: >
  Bo kit day du cho du an robot tu hanh su dung ROS2.
  Bao gom skill cho thiet ke node architecture, navigation stack,
  perception pipeline, va system integration testing.

project_signals:
  technologies: ["python", "cpp", "ros2"]
  domains: ["robotics", "ai-ml"]
  file_patterns:
    - "CMakeLists.txt"
    - "package.xml"
    - "*.launch.py"
    - "colcon.meta"
    - "*.msg"
    - "*.srv"
    - "*.action"

core_skills:
  - id: "ros2-node-architecture"
    why: "Moi du an ROS2 can thiet ke node architecture dung chuan de de bao tri va mo rong."
  - id: "systematic-debugging"
    why: "Debug robot phuc tap hon debug web — can phuong phap co he thong."
  - id: "brainstorming"
    why: "Robot tu hanh co nhieu quyet dinh thiet ke — can brainstorm ky truoc khi code."

workflow_skills:
  - id: "tdd-workflow"
    when: "Khi implement logic dieu khien (controller) hoac node moi co behavior ro rang."
  - id: "code-review"
    when: "Truoc khi merge bat ky PR nao thay doi logic dieu khien hoac navigation."

ship_cycle:
  - id: "deployment-checklist"
    when: "Truoc moi lan flash firmware hoac deploy len robot thuc te."
  - id: "security-audit"
    when: "Khi du an bat dau ket noi mang (remote operation, fleet management)."

activation:
  superpowers: "claude skill add ~/Agent_Hub/superpowers/skills/systematic-debugging"
  everything-claude-code: "node ~/Agent_Hub/everything-claude-code/scripts/install.js --module tdd-workflow"
  gstack: "gstack install ros2-navigation"
  get-shit-done: "gsd install security-audit"
```

### 5.11 Quan he voi cac schema khac

- Tat ca `id` trong `core_skills`, `workflow_skills`, `ship_cycle` tham chieu den `catalog.json`.
- `library-manifest.yaml` co truong `stack` tham chieu den `id` cua Stack.
- Khi AI Librarian ap dung stack, no tao/cap nhat `library-manifest.yaml` trong du an va publish tat ca core_skills.
- `project_signals.file_patterns` duoc AI Librarian dung de auto-detect: khi mo du an, quet file he thong, neu match thi goi y stack.

---

## 6. SKILL.md — Dinh dang file Skill

### 6.1 Mo ta

Moi skill trong thu vien duoc luu tru duoi dang file Markdown voi YAML frontmatter. Phan frontmatter chua metadata co cau truc, phan body chua huong dan chi tiet dang Markdown tu do. Day la dinh dang chuan ma Claude Code (va cac AI coding tool khac) doc de hieu cach su dung skill.

### 6.2 Vi tri file

```
Agent_Hub/library/skills/{skill-id}/SKILL.md
```

### 6.3 Cau truc file

```markdown
---
name: "Ten skill"
description: "Use when..."
---

# Noi dung huong dan chi tiet (Markdown body)
```

### 6.4 Bang mo ta truong — YAML Frontmatter

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `name` | `string` | **Co** | Ten cua skill, dung de hien thi. | Toi thieu 2 ky tu, toi da 100 ky tu. Nen viet dang Title Case. | `"Systematic Debugging"` |
| `description` | `string` | **Co** | Mo ta ngan gon bat dau bang "Use when..." — giup AI hieu khi nao nen kich hoat skill nay. | **Phai bat dau bang "Use when"** (case-insensitive). Toi thieu 15 ky tu, toi da 500 ky tu. Nen la 1-2 cau. | `"Use when encountering bugs that aren't immediately obvious. Guides systematic evidence collection and hypothesis testing."` |

### 6.5 Quy tac validation — Frontmatter

1. **YAML hop le**: Phan giua hai dong `---` phai la YAML hop le.
2. **`description` bat dau bang "Use when"**: Day la quy uoc bat buoc de AI biet dieu kien kich hoat. Cho phep variations: "Use when", "use when", "USE WHEN".
3. **Khong chua truong thua**: Frontmatter chi nen chua `name` va `description`. Cac truong khac (neu can) duoc quan ly boi `catalog.json` va `provenance.yaml`.
4. **Encoding UTF-8**: File phai duoc luu dang UTF-8.

### 6.6 Quy tac validation — Markdown body

1. **Khong rong**: Phan body sau frontmatter phai co noi dung (toi thieu 50 ky tu).
2. **Co it nhat 1 heading**: Body nen co it nhat 1 Markdown heading (`#`, `##`, v.v.).
3. **Khong chua secret**: Khong chua API key, password, hoac thong tin nhay cam.

### 6.7 Vi du hoan chinh

```markdown
---
name: "Systematic Debugging"
description: "Use when encountering bugs that aren't immediately obvious. Guides systematic evidence collection, hypothesis formation, and step-by-step verification instead of guessing."
---

# Systematic Debugging

## Khi nao su dung
- Bug khong ro nguyen nhan tu thong bao loi
- Bug tai xuat khong on dinh (intermittent)
- Loi xay ra sau khi merge nhieu thay doi

## Quy trinh

### Buoc 1: Thu thap chung cu
- Doc ky thong bao loi va stack trace
- Xac dinh input/output thuc te so voi ky vong
- Kiem tra log va monitoring data

### Buoc 2: Lap gia thuyet
- Liet ke toi da 3 nguyen nhan co the
- Xep hang theo kha nang xay ra
- Voi moi gia thuyet, xac dinh cach kiem chung

### Buoc 3: Kiem chung
- Bat dau voi gia thuyet co kha nang cao nhat
- Thiet ke test case nho nhat co the tai tao bug
- Xac nhan hoac bac bo gia thuyet truoc khi chuyen sang cai tiep theo

### Buoc 4: Sua loi va xac nhan
- Viet test tai tao bug TRUOC khi sua
- Ap dung fix nho nhat co the
- Chay lai tat ca test de dam bao khong co regression

## Luu y
- KHONG doan mua va thu sai (trial and error)
- KHONG sua nhieu cho cung luc
- Ghi chep lai qua trinh debug de hoc tu kinh nghiem
```

### 6.8 Quan he voi cac schema khac

- Ten thu muc chua SKILL.md phai khop voi `id` cua entry tuong ung trong `catalog.json`.
- Truong `name` va `description` trong frontmatter nen nhat quan voi `name` va `description` trong catalog (catalog la nguon chinh, SKILL.md la noi AI doc khi thuc thi).
- `provenance.yaml` theo doi nguon goc va phien ban cua file SKILL.md nay.

---

## 7. Agent .md — Dinh dang file Agent

### 7.1 Mo ta

Agent khac voi Skill o cho: Agent la mot "nhan vat" co cong cu (tools) duoc cap phep, model cu the, va hanh vi rieng. File Agent .md cung su dung YAML frontmatter nhung co them cac truong `tools` va `model`. Phan body chua chi dan chi tiet cho AI ve cach Agent hoat dong.

### 7.2 Vi tri file

```
Agent_Hub/library/agents/{agent-id}.md
```

### 7.3 Cau truc file

```markdown
---
name: "Ten agent"
description: "Mo ta chuc nang"
tools: ["tool1", "tool2"]
model: "sonnet"
---

# Huong dan cho Agent (Markdown body)
```

### 7.4 Bang mo ta truong — YAML Frontmatter

| Truong | Kieu | Bat buoc | Mo ta | Rang buoc | Vi du |
|--------|------|----------|-------|-----------|-------|
| `name` | `string` | **Co** | Ten cua agent. | Toi thieu 2 ky tu, toi da 100 ky tu. | `"Security Audit Agent"` |
| `description` | `string` | **Co** | Mo ta chuc nang cua agent (1-2 cau). | Toi thieu 10 ky tu, toi da 500 ky tu. Khong bat buoc bat dau bang "Use when" nhu Skill, nhung nen mo ta ro muc dich. | `"Quet bao mat toan dien theo OWASP Top 10, phan tich dependency vulnerabilities, va kiem tra cau hinh bao mat."` |
| `tools` | `string[]` | **Co** | Danh sach cac tool ma agent duoc phep su dung. | Mang co the rong `[]` (agent chi su dung suy luan, khong can tool). Cac gia tri thuong gap: `"Read"`, `"Write"`, `"Edit"`, `"Bash"`, `"Glob"`, `"Grep"`, `"WebSearch"`, `"WebFetch"`, `"NotebookEdit"`. | `["Read", "Bash", "Grep", "Glob"]` |
| `model` | `string` | **Co** | Model AI duoc su dung cho agent. | Mot trong: `"haiku"` (nhe, nhanh, re), `"sonnet"` (can bang), `"opus"` (manh nhat, dat nhat). | `"sonnet"` |

### 7.5 Quy tac validation — Frontmatter

1. **YAML hop le**: Phan frontmatter phai la YAML hop le.
2. **`model` hop le**: Chi chap nhan `"haiku"`, `"sonnet"`, hoac `"opus"`.
3. **`tools` hop le**: Moi tool trong mang phai la ten tool da biet. Danh sach tools hop le:
   - Core tools: `"Read"`, `"Write"`, `"Edit"`, `"Bash"`, `"Glob"`, `"Grep"`
   - Extended tools: `"WebSearch"`, `"WebFetch"`, `"NotebookEdit"`, `"TodoWrite"`
   - Tool ten viet dung Title Case (bat dau bang chu hoa).
4. **Khong trung tool**: Mang `tools` khong duoc co phan tu trung lap.
5. **Encoding UTF-8**: File phai duoc luu dang UTF-8.

### 7.6 Quy tac validation — Markdown body

1. **Khong rong**: Body phai co noi dung (toi thieu 50 ky tu).
2. **Co heading**: Nen co it nhat 1 Markdown heading.
3. **Khong chua secret**: Tuong tu SKILL.md.

### 7.7 Huong dan chon `model`

| Model | Khi nao dung | Token cost | Do chinh xac |
|-------|-------------|------------|-------------|
| `haiku` | Task don gian, lap di lap lai, khong can suy luan sau. Vi du: format code, tao boilerplate. | Thap | Trung binh |
| `sonnet` | Task can bang giua toc do va chat luong. Vi du: code review, refactor, viet test. | Trung binh | Cao |
| `opus` | Task phuc tap, can suy luan sau, phan tich toan dien. Vi du: security audit, architecture review, debug phuc tap. | Cao | Rat cao |

### 7.8 Vi du hoan chinh

```markdown
---
name: "Security Audit Agent"
description: "Quet bao mat toan dien theo OWASP Top 10, phan tich dependency vulnerabilities, va kiem tra cau hinh bao mat. Tao bao cao chi tiet voi muc do nghiem trong va huong khac phuc."
tools: ["Read", "Bash", "Grep", "Glob"]
model: "opus"
---

# Security Audit Agent

## Vai tro
Ban la chuyen gia bao mat. Nhiem vu cua ban la kiem tra toan dien
ma nguon va cau hinh cua du an de tim lo hong bao mat.

## Quy trinh kiem tra

### 1. Quet dependency
- Doc package.json / requirements.txt / Cargo.toml
- Chay `npm audit` / `pip-audit` / `cargo audit`
- Liet ke cac dependency co CVE da biet

### 2. Kiem tra OWASP Top 10
- **Injection**: Tim cac cho dung input nguoi dung truc tiep trong query/command
- **Broken Auth**: Kiem tra cach xu ly session, token, password
- **Sensitive Data Exposure**: Tim hardcoded secret, API key, password
- **XXE**: Kiem tra cac XML parser co disable external entities khong
- **Broken Access Control**: Kiem tra authorization logic
- **Security Misconfiguration**: Kiem tra cau hinh server, CORS, headers
- **XSS**: Tim cac cho render user input khong escape
- **Insecure Deserialization**: Kiem tra cac cho deserialize data tu ben ngoai
- **Known Vulnerabilities**: Cross-reference voi dependency scan
- **Insufficient Logging**: Kiem tra co log cac security event khong

### 3. Kiem tra cau hinh
- HTTPS enforcement
- CORS policy
- Security headers (CSP, HSTS, X-Frame-Options)
- Environment variables (khong hardcode secret)

## Dinh dang bao cao
Tao bao cao voi cac muc:
- **CRITICAL**: Can sua ngay, co the bi khai thac
- **HIGH**: Can sua som, rui ro cao
- **MEDIUM**: Nen sua, rui ro trung binh
- **LOW**: Co the cai thien, rui ro thap
- **INFO**: Goi y tot nhat (best practice)
```

### 7.9 Quan he voi cac schema khac

- Ten file (bo phan `.md`) hoac ten thu muc phai khop voi `id` trong `catalog.json`.
- Entry tuong ung trong catalog phai co `type: "agent"`.
- `provenance.yaml` theo doi nguon goc cua file agent nay.
- Truong `model` anh huong den `cost` trong registry (haiku = light, sonnet = medium, opus = heavy).

---

## 8. So do quan he giua cac schema

```
                    ┌─────────────────────┐
                    │   catalog.json       │
                    │  (Single Source of   │
                    │   Truth cho IDs)     │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼───────────────────┐
            │                  │                    │
            ▼                  ▼                    ▼
  ┌──────────────────┐ ┌──────────────┐  ┌──────────────────┐
  │ provenance.yaml  │ │ SKILL.md     │  │ Agent .md        │
  │ (1 file/entry)   │ │ (1 file/     │  │ (1 file/agent)   │
  │                  │ │  skill)      │  │                  │
  │ Theo doi nguon   │ │ Noi dung     │  │ Noi dung +       │
  │ goc & phien ban  │ │ huong dan    │  │ tools + model    │
  └──────────────────┘ └──────────────┘  └──────────────────┘
            │
            │ source_project == catalog.from
            │
            ▼
  ┌──────────────────┐
  │ Source Projects   │
  │ (superpowers,    │
  │  everything-     │
  │  claude-code,    │
  │  gstack, ...)    │
  └──────────────────┘

  ┌──────────────────┐         ┌──────────────────┐
  │ Collection YAML  │         │ Stack YAML       │
  │                  │         │                  │
  │ entries[].id ────┼────────►│ core_skills[].id │
  │ tham chieu       │  cung   │ workflow_skills[] │
  │ catalog.json     │  tham   │ ship_cycle[]     │
  │                  │  chieu  │                  │
  └──────────────────┘  ──►   └────────┬─────────┘
                               catalog  │
                               .json    │
                                        ▼
                              ┌──────────────────┐
                              │ library-manifest  │
                              │ .yaml             │
                              │                  │
                              │ entries[].id ──► catalog.json
                              │ stack ──► Stack YAML (id)
                              │                  │
                              │ (Dat trong moi   │
                              │  du an su dung   │
                              │  Agent Hub)      │
                              └──────────────────┘
```

### Tom tat quan he

| Schema A | Truong | Tham chieu den | Schema B | Truong |
|----------|--------|---------------|----------|--------|
| `provenance.yaml` | `source_project` | == | `catalog.json` entry | `from` |
| `provenance.yaml` | ten file | == | `catalog.json` entry | `id` |
| `Collection YAML` | `entries[].id` | ton tai trong | `catalog.json` | `entries[].id` |
| `Stack YAML` | `core_skills[].id` | ton tai trong | `catalog.json` | `entries[].id` |
| `Stack YAML` | `workflow_skills[].id` | ton tai trong | `catalog.json` | `entries[].id` |
| `Stack YAML` | `ship_cycle[].id` | ton tai trong | `catalog.json` | `entries[].id` |
| `library-manifest.yaml` | `entries[].id` | ton tai trong | `catalog.json` | `entries[].id` |
| `library-manifest.yaml` | `stack` | ton tai trong | `Stack YAML` | `id` |
| `library-manifest.yaml` | `entries[].from` | == | `catalog.json` entry | `from` |
| `library-manifest.yaml` | `entries[].version` | lien quan den | `provenance.yaml` | `source_version` |
| `SKILL.md` | ten thu muc | == | `catalog.json` entry | `id` |
| `Agent .md` | ten file (bo `.md`) | == | `catalog.json` entry | `id` |

---

## 9. Phu luc: Controlled Vocabularies

Cac danh sach gia tri duoc kiem soat (controlled vocabulary) duoc su dung xuyen suot cac schema. Bat ky gia tri nao khong nam trong danh sach se bi tu choi boi validator.

### 9.1 DOMAINS

Cac linh vuc ung dung. Su dung trong `catalog.json`, `Stack YAML`, va `Collection YAML`.

| Gia tri | Mo ta |
|---------|-------|
| `robotics` | Robot, ROS/ROS2, dieu khien tu dong, sensor |
| `web-frontend` | Giao dien web: React, Vue, Angular, CSS, HTML |
| `web-backend` | API, server, database, middleware |
| `mobile` | Ung dung di dong: Android, iOS, Flutter |
| `devops` | CI/CD, Docker, Kubernetes, infrastructure as code |
| `data` | Co so du lieu, data pipeline, ETL, analytics |
| `security` | Bao mat, OWASP, audit, ma hoa |
| `ai-ml` | Machine learning, LLM, training, inference |
| `workflow` | Quy trinh lam viec, Git workflow, project management |
| `debugging` | Tim va sua loi, profiling, monitoring |
| `testing` | Unit test, integration test, E2E, TDD |
| `planning` | Lap ke hoach, roadmap, requirement analysis |
| `design` | Thiet ke UX/UI, wireframe, accessibility |
| `documentation` | Tai lieu, README, API docs, changelog |
| `research` | Nghien cuu, paper, thi nghiem, benchmark |
| `infrastructure` | Cloud (AWS, GCP, Azure), server, networking |

### 9.2 TECHNOLOGIES

Cac cong nghe/ngon ngu/framework. Su dung trong `catalog.json` va `Stack YAML`.

| Gia tri | Mo ta |
|---------|-------|
| `python` | Python va he sinh thai (Django, FastAPI, Flask, pytest) |
| `cpp` | C++ va he sinh thai (CMake, Clang, GTest) |
| `rust` | Rust va he sinh thai (Cargo, Tokio, Serde) |
| `go` | Go/Golang va he sinh thai (Gin, GORM) |
| `java` | Java va he sinh thai (Spring, Gradle, Maven) |
| `typescript` | TypeScript va he sinh thai (Node.js, Deno, Bun) |
| `ros2` | ROS2 framework (rclcpp, rclpy, nav2, MoveIt) |
| `docker` | Docker, Docker Compose, container ecosystem |
| `react` | React va he sinh thai (Next.js, Remix, Redux) |
| `pytorch` | PyTorch va he sinh thai (CUDA, torchvision) |
| `postgres` | PostgreSQL va he sinh thai (pgvector, Supabase) |
| `kotlin` | Kotlin va he sinh thai (Jetpack Compose, Coroutines) |
| `swift` | Swift va he sinh thai (SwiftUI, Xcode, SPM) |
| `android` | Android platform (SDK, ADB, Room, Retrofit) |

### 9.3 PHASES

Cac giai doan phat trien phan mem. Su dung trong `catalog.json`.

| Gia tri | Mo ta |
|---------|-------|
| `planning` | Lap ke hoach, phan tich yeu cau, xac dinh scope |
| `architecture` | Thiet ke kien truc, ADR, chon pattern |
| `development` | Viet code, implement feature, refactor |
| `testing` | Viet va chay test, QA, coverage |
| `debugging` | Tim va sua loi, root cause analysis |
| `review` | Code review, audit, danh gia chat luong |
| `deployment` | Deploy, release, CI/CD, ship |
| `monitoring` | Giam sat, logging, alerting, observability |
| `documentation` | Viet tai lieu, changelog, API docs |

### 9.4 PROJECT_TYPES

Cac loai du an. Su dung trong `catalog.json`, `Collection YAML`, va `Stack YAML`.

| Gia tri | Mo ta |
|---------|-------|
| `any` | Ap dung cho moi loai du an (dung khi khong gioi han) |
| `web-fullstack` | Du an web day du (frontend + backend) |
| `api-service` | Dich vu API / microservice |
| `mobile-android` | Ung dung Android |
| `mobile-ios` | Ung dung iOS |
| `cli-tool` | Cong cu dong lenh (CLI) |
| `ml-research` | Nghien cuu machine learning |
| `ai-agent` | Xay dung AI agent |
| `devops-pipeline` | Pipeline CI/CD, infrastructure |
| `robotics-ros2` | Du an robot su dung ROS2 |
| `content-publishing` | Xuat ban noi dung (blog, docs site, CMS) |

### 9.5 COMPLEXITY

| Gia tri | Mo ta |
|---------|-------|
| `beginner` | Nguoi moi co the su dung ngay, huong dan ro rang, it rui ro |
| `intermediate` | Can hieu biet co ban ve domain, co the can tuy chinh |
| `advanced` | Can kinh nghiem sau, cau hinh phuc tap, tac dong lon |

### 9.6 USAGE_PATTERN

| Gia tri | Mo ta |
|---------|-------|
| `prerequisite` | Can chay truoc cac entry khac (vi du: brainstorming truoc khi implement) |
| `standalone` | Dung doc lap, khong phu thuoc entry khac |
| `companion` | Nen dung kem entry khac de tang hieu qua |
| `optional` | Tuy chon, khong bat buoc trong bat ky workflow nao |

### 9.7 INVOCATION_STYLE

| Gia tri | Mo ta |
|---------|-------|
| `explicit` | Nguoi dung phai goi truc tiep (vi du: `/skill systematic-debugging`) |
| `proactive` | AI tu dong kich hoat khi phat hien nhu cau phu hop |
| `background` | Chay ngam, khong can tuong tac tu nguoi dung |

### 9.8 OUTPUT / CONSUME Artifact Types

Cac loai artifact duoc tao ra (`outputs`) hoac tieu thu (`consumes`) boi cac entry. Day la danh sach goi y, khong bat buoc phai gioi han — nhung nen uu tien su dung cac gia tri nay de dam bao tinh nhat quan.

| Gia tri | Mo ta |
|---------|-------|
| `design-doc` | Tai lieu thiet ke |
| `plan` | Ke hoach thuc hien |
| `test-suite` | Bo test (unit, integration, E2E) |
| `code-review` | Bao cao review code |
| `implementation` | Ma nguon da implement |
| `debug-report` | Bao cao debug / root cause analysis |
| `documentation` | Tai lieu (README, API docs, v.v.) |
| `config` | File cau hinh |
| `migration` | Script migration (database, schema) |
| `refactored-code` | Ma nguon da refactor |
| `api-spec` | Dac ta API (OpenAPI, GraphQL schema) |
| `deployment-script` | Script deploy / CI-CD pipeline |
| `security-report` | Bao cao bao mat |
| `architecture-diagram` | So do kien truc |
| `prototype` | Prototype / mockup |

---

## Ghi chu cho implementer

### Validation code

Khi viet validation code, nen kiem tra theo thu tu uu tien:

1. **Schema validation**: Kiem tra kieu du lieu, truong bat buoc, gia tri hop le (dung JSON Schema hoac tuong duong).
2. **Referential integrity**: Kiem tra tat ca tham chieu ID giua cac schema (catalog -> provenance, collection -> catalog, stack -> catalog, manifest -> catalog + stack).
3. **Business rules**: Kiem tra cac quy tac nghiep vu dac biet (doi xung conflicts_with, sequence lien tuc, thu tu thoi gian, v.v.).
4. **Soft warnings**: Cac kiem tra khong bat buoc nhung nen canh bao (entry bi superseded trong collection, core_skills cua stack khong co trong manifest, v.v.).

### Naming conventions

- File va folder: lowercase, dau gach ngang (kebab-case): `systematic-debugging`, `code-quality-essentials.yaml`
- ID: lowercase, dau gach ngang: `systematic-debugging`
- Schema truong: snake_case: `use_with`, `conflicts_with`, `source_project`
- Controlled vocabulary: lowercase, dau gach ngang: `web-frontend`, `ai-ml`, `mobile-android`

### Dinh dang ngay gio

Tat ca cac truong ngay gio trong moi schema deu su dung **ISO 8601** voi timezone. Nen dung UTC (`Z`) de thong nhat. Vi du: `"2026-03-30T10:00:00Z"`.
