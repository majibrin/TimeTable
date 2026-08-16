# TimeTable System — Design Understanding (v2)

**Status:** Design/understanding phase — nothing in this document has been coded yet.
**Purpose:** Single reference capturing everything confirmed so far, what's still open, and what it means for the existing code and thesis.

---

## 1. What triggered this redesign

A handover document from a meeting with **Dr. Lamido Yahaya (Timetable Officer II)** — the officer actually interviewed, distinct from Dr. Adamu Abubakar (Timetable Officer I, who co-signs documents but was not interviewed — see 100L/200L PDF signatures) — revealed that several assumptions baked into the original system (and thesis) don't match how timetabling actually works at the Faculty. Two verified source documents were reviewed directly (not just described secondhand):

- `100_Level_General_Groupings_Second_Semester_2025-2026.pdf`
- `200_Level_Second_Semester_Grouping_2025-2026.pdf`

Both signed by Dr. Adamu Abubakar (TTO I) and Dr. Yahaya Lamido (TTO II), Second Semester 2025/2026 session.

---

## 2. Confirmed: RBAC v2 — the new role model

| Role | Login? | Responsibilities |
|---|---|---|
| **Super Admin** | Yes | Creates all accounts (Officer, Department, Student) — same as today |
| **Timetable Officer** | Yes | Reviews and approves/rejects department-submitted courses and venues; attaches a grouping scheme to a course **after** approval (separate step); triggers timetable generation; publishes |
| **Department** *(NEW)* | Yes | Submits and manages **own** courses and venues (status starts Pending); can **view** other departments' courses/venues read-only, but can only **edit their own**; views own department's generated/published timetable |
| **Student** | Yes | Unchanged — views published timetable for their cohort |
| **Lecturer** | ❌ **Removed entirely** | No login, no dashboard, no data field anywhere in the system |

### Removed entirely (confirmed)
- Lecturer role/login/dashboard
- `Course.lecturer` field — **not kept even as plain data**. Lecturer assignment happens completely outside this system (handled by departments independently); the system stores nothing about it.
- Adjustment Request feature — model, endpoints, both dashboard tabs (Officer's REQUESTS tab, Lecturer's REQUEST tab) — the entire feature existed to let lecturers request schedule changes, so it goes with the role.

### Significant consequence
The **"lecturer clash" hard constraint**, currently documented in Ch 2.3, Ch 4.3.6, and Ch 4.4.3 as one of the system's enforced hard constraints, becomes **impossible to check** — there is no lecturer data anywhere to compare. This claim needs to be removed from the documentation, not softened or reworded. This is a case of the original claim being wrong, not the code lagging behind a correct claim.

---

## 3. Confirmed: Course/Venue submission & approval workflow

1. **Department** submits a course (title, code, unit, which cohorts offer it — no lecturer) or venue (name, capacity) → status **Pending**.
2. **Department** can view all departments' submissions, but can only edit their own.
3. **Officer** reviews Pending submissions:
   - **Approve** → becomes usable in timetable generation.
   - **Reject with a note** → Department sees the reason, can edit, and resubmit (returns to Pending).
4. Once **Approved**, the Officer separately attaches a grouping scheme (General / Course-Specific / Practical) if one applies to that course — this is the Officer's decision alone, made after approval, not something the Department selects at submission time.
5. **Officer** triggers generation — only Approved courses/venues are used.
6. **Officer** publishes.
7. **Department** and **Student** view results (Department: own department's slice; Student: own cohort's published slice).

### Still open — not yet answered
- Can a Department edit a course/venue **after** it's been Approved (e.g. fixing a typo), or does any change force it back through a fresh Pending → Approve cycle?

---

## 4. Confirmed: Timetable generation stays combined, viewing needs to split

- **Generation stays as one single SA run** across all levels and departments — not split per level. No change needed to the core generation trigger's scope.
- **Viewing/display currently has no level separation** — the Officer Dashboard's timetable grid shows every level mixed together in one grid. This is a real, confirmed gap: `SessionSlot → cohort → level` already exists in the data, it's just never used to filter what's displayed.
- **Fix needed:** add level-based filtering/tabs to the timetable view (Officer, and by extension Department once its dashboard exists) — a display-layer change, not a data-model change.

---

## 5. Confirmed: Grouping system (verified directly from source PDFs)

### 100 Level (document dated 26 July 2026)

| Scheme | Groups | Scope |
|---|---|---|
| **General Grouping** | A – J (10 groups) | Default — broad department bundling used by most 100L courses unless a course has its own scheme below |
| **COS 102** (course-specific) | 1 – 4 | Only for COS 102 |
| **GSU-MTH 104** (course-specific) | 1 – 2 | Only for GSU-MTH 104 |
| **STA 112** (course-specific) | 1 – 2 | Only for STA 112 |
| **Practical Grouping** | 1 – 6 | General-purpose — used for whichever course has a lab/practical component, not tied to one specific course |

### 200 Level (document dated 19 July 2026)

**No general A–J scheme appears in this document at all.** Every listed course has its own **independent** Group A/B table — the label "Group A" is not shared or reused between courses, even within the same subject:

- CHM 210 — own A/B (different departments than CHM 212)
- CHM 212 — own A/B
- BIO 202 — own A/B
- BIO 208 / GSU-BIO 208 — own A/B
- MTH 202 — own A/B
- MTH 210 — own A/B
- STA 202 — own A/B

**Still open — not yet confirmed:** whether 200L genuinely has no default/general scheme at all, or whether one exists in a document not yet reviewed. Not to be assumed either way.

### Design implication for the data model (proposed, not yet built)

Because "Group A" means something different per course under the Course-Specific scheme, group identity cannot be a stable, reusable label like `(level, scheme, name)` uniquely — a course-specific group is only meaningful in the context of the specific course it was defined for. The General scheme and Practical scheme, by contrast, genuinely are shared/reusable across many courses. This asymmetry needs to be reflected in whatever model gets built — not yet designed in code.

---

## 6. Other confirmed points from earlier in the redesign (pre-RBAC-v2)

- **Venue capacity** should likely move from **hard** to **soft** constraint — only outright double-booking of a venue is hard; capacity being tight/insufficient is a quality issue, not a feasibility blocker. *(Raised, not yet implemented in `engine.py`.)*
- **Lecture-hours** and **faculty-break** hard constraints in `engine.py` are currently unreachable/dead code — they're enforced by construction (excluded from the random generation space entirely) rather than by penalty scoring in `calculate_energy()`. Needs either a documentation wording fix (describe as "enforced by construction") or an engine change (make them genuinely scoreable) — not yet decided.
- **`idle_gaps`** constraint has a weight defined in `engine.py`'s defaults but no corresponding logic in `calculate_energy()` — dead weight, undecided whether to implement or drop.
- Multi-campus venue separation and an optional ICT review step before publishing were mentioned in the original handover document but not yet discussed in depth here — still pending a focused conversation.

---

## 7. Already-shipped code (needs reconciliation with RBAC v2)

These were built and tested **before** the RBAC v2 conversation happened, and will need revisiting:

| Change | Status | RBAC v2 impact |
|---|---|---|
| Fixed `/dashboard` → `/` navigation bug | ✅ Shipped, tested | No impact — stays valid |
| PDF timetable export (Officer/Lecturer/Student) | ✅ Shipped, tested | **Lecturer's export button needs removal** once the Lecturer dashboard itself is removed |
| 36 automated tests in `tests.py` | ✅ Shipped, all passing | **`AdjustmentRequestTests` (5 tests) will need removal**; any test touching `Course.lecturer` or `User.role=LECTURER` will need rewriting once those are dropped from the model |

---

## 8. Documentation implications building up (not yet actioned)

- Django version claim ("6.0") — still unverified against actual installed version.
- Ch 1.3 objective "export timetable reports" — now genuinely true, drafted text ready to insert (not yet done).
- Ch 4.7 testing chapter — now genuinely backed by 36 automated tests, drafted text ready to insert (not yet done) — **but will need updating again once Adjustment Request tests are removed under RBAC v2**.
- Ch 3.4/3.5 `[PENDING VERIFICATION]` flag on Faculty Timetable Officer's requirements-elicitation role — ready to resolve now that the handover document exists, not yet done.
- **Large sections of Chapter 4 will need substantial rewriting**, not just tweaking, once RBAC v2 is built: 4.3.2 (User entity — currently lists 4 roles including Lecturer), 4.3.6 (Course entity — currently says lecturer assignment prevents clashes), 4.5.6/4.5.7 (Adjustment Request interface, Lecturer Dashboard), 4.6.1 (Authentication module — four roles), 4.6.8 (Adjustment Request module), 4.7.7 (Adjustment Request testing).
- Ch 2.3 / 4.3.6 / 4.4.3 — hard constraint list needs updating: remove lecturer clash entirely; possibly move venue capacity to soft; clarify lecture-hours/break enforcement mechanism.
- New Department role, course/venue approval workflow, and the grouping system all need new documentation written from scratch once the design is finalized and built — none of this exists in any chapter yet.

---

## 9. Open questions log (not yet answered — do not assume)

1. Can a Department edit a course/venue after it's Approved, or does any edit require re-approval?
2. Does 200 Level genuinely have no general/default grouping scheme, or does one exist elsewhere?
3. Multi-campus venue separation — not yet discussed in depth.
4. Optional ICT review step before publishing — not yet discussed in depth.

---

*This document reflects understanding only. No corresponding code changes have been made for anything in sections 2–6. Sections 7–8 describe existing shipped code and pending documentation work respectively.*
