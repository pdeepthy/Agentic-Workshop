---
title: 'Seed loader'
type: 'feature'
created: '2026-09-26'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/specs/spec-epic-1/SPEC.md', '{project-root}/mcp/triage_server.py']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing creates `app.db`, so `mcp/triage_server.py` can't answer and the Epic 2 agent can't run (SPEC-epic-1 CAP-2, CAP-3).

**Approach:** Add `load_seed.py`, which reads `seed/tickets.csv` and `seed/customers.csv` and rebuilds the `tickets` and `customers` tables in `app.db`, one column per CSV header (24 and 20 rows). Running it again gives the same database: no duplicates and no error.

</frozen-after-approval>

## Implementation Notes

- Layout matches the workshop's `origin/stage-2` reference: `load_seed.py` at the repo root, tests in `tests/test_load_seed.py`.
- Epic 1 SPEC's open question (`open_tickets` INTEGER or text) is settled as INTEGER, following `origin/stage-2`. `TRIAGE_POLICY.md`'s Enterprise rule compares the value to 3, so storing it as text would compare strings, not numbers. The SPEC itself is unchanged; that change goes through `/bmad-spec`.
- Repeatable (CAP-3): each run drops and recreates both tables in one explicit transaction. Every CSV is read and checked first, so a bad file leaves `app.db` as it was, and a failure partway through the load rolls back.
- CSVs are opened as `utf-8-sig`, so a file saved with a byte-order mark (Excel does this) still loads. A row with the wrong number of fields, or a non-number `open_tickets`, is refused with the file name and line.
- Files: `load_seed.py` (`TABLES`, `load(db_path, seed_dir)`), `tests/test_load_seed.py` (13 tests; `uv run pytest` passes with 55 tests). Checked by hand: `uv run python load_seed.py` run twice prints 24/20 rows both times.
- CAP-2 → `test_load_creates_both_tables_with_seed_columns_and_counts`; CAP-3 → `test_second_run_gives_the_same_database`; SPEC success signal → `test_triage_server_reads_the_loaded_database`.

## Review Triage Log

- Short row crashes with a raw TypeError: medium, real (`DictReader` fills missing fields with None). Patched, along with the next item.
- Row width never checked (short rows load as NULL, extra fields are dropped): low, real. Patched: any row with the wrong number of fields is refused, naming the line.
- Non-number error doesn't name the column or value: low. Patched.
- BOM header refused with a confusing message: low, real. Patched (`utf-8-sig`).
- Duplicate or blank keys not checked before loading: low, real. A duplicate raises an `IntegrityError` and the load rolls back, and the seed files are read-only. Rejected: rare, and the fix adds a validation layer.
- No foreign key from tickets to customers: low; every ticket's customer exists in the read-only seed. Rejected.
- Rollback path untested: medium (it's the CAP-3 safety net). Patched with a test that loads a duplicate primary key.
- No tests for bad row shapes: low. Patched (short and long rows, BOM).
- Non-number test doesn't check the database is left untouched: low. Rejected, since the header test already covers failing before the transaction.
- CLI test doesn't check the last line or set `cwd`: low. Patched (runs from a different directory and checks the whole output).
- Server test changes `sys.path` by hand: low. Patched (`monkeypatch.syspath_prepend`).
- Implementation Notes empty, status still in-progress: false. The workflow fills both in at finalize.
- No doc points to `load_seed.py`: false. `AGENTS.md` Commands already lists `uv run python load_seed.py`.
