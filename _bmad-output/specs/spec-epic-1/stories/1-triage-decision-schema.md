---
title: 'Triage-decision schema'
type: 'feature'
created: '2026-09-26'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/specs/spec-epic-1/SPEC.md', '{project-root}/TRIAGE_POLICY.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing defines what a triage decision looks like, so Epic 2's structured output and Epic 3's `valid_schema` scorer have nothing to validate against (SPEC-epic-1 CAP-1).

**Approach:** A local, dependency-free (beyond pydantic) schema for a decision: `category`, `priority`, `route` and `rationale`, each restricted to its allowed values. The route must be the one `TRIAGE_POLICY.md` pairs with the category, and the rationale must be exactly one sentence. Anything else is rejected with an error that names the offending field.

</frozen-after-approval>

## Implementation Notes

- Layout matches the workshop's `stage-2` reference: package `triage/` with `triage/schema.py`, tests in `tests/test_schema.py`.
- Single-sentence rule (agent's choice, not user-visible beyond the spec): after stripping whitespace, the rationale is non-empty, ends with `.`, `!` or `?`, and contains no sentence terminator followed by whitespace and more text. Abbreviations like "e.g." inside a rationale therefore count as a sentence break; accepted trade-off for a strict rule.
- Extra fields are rejected (strict shape).
- Files: `triage/__init__.py`, `triage/schema.py` (`TriageDecision`, `ROUTE_FOR_CATEGORY`, `validate_decision` for a dict or JSON string), `tests/conftest.py` (puts the repo root on `sys.path`, as `origin/stage-2` does), `tests/test_schema.py` (42 tests, `uv run pytest` green).
- After review, the single-sentence rule also rejects newlines and a sentence end followed directly by a capital ("Money.Two"), requires at least one letter or digit, and allows a closing quote or bracket after the final mark. Accepted false rejections: abbreviations ("e.g. the"), and ellipses followed by more text.
- `route` and `rationale` carry `Field` descriptions so Epic 2's structured output tells the model the pairing and one-sentence rules.
- Not enforced here: TRIAGE_POLICY.md's "names the rule you applied". That's judged by Epic 3's rationale judge, not by the schema.
- When `category` is invalid, only `category` is reported; the route check needs a valid category to compare against.

## Review Triage Log

- Two sentences without a space or split by newlines accepted — medium, reproduced; patched.
- Real single sentences ending in a closing quote/bracket rejected — low, reproduced; patched. Ellipsis case rejected as accepted trade-off (arguably two clauses; fix would complicate the rule).
- Route check depends on field order — low, real but only on a future reorder; rejected (fix adds a model validator for little gain); a comment now guards the order.
- Allowed sets written twice, dict typed `dict[str, str]` — low; patched (typed `dict[Category, Route]`, test that table covers both Literals).
- No rejection tests for JSON-string input — medium (Epic 3's scorer path); patched with malformed-JSON and bad-field-in-JSON tests. Top-level-array/`null` naming no field: false, pydantic reports a clear model-type error, which is acceptable for non-object input.
- No field descriptions for structured output — medium (Epic 2 would fail validation it can't predict); patched.
- Policy's "names the rule applied" not mentioned — low; noted above.
- conftest.py instead of `pythonpath` in pyproject — false; matches the `origin/stage-2` layout and avoids editing shared config.
- Story file incomplete (no AC/verification, status, stage-2 unverifiable) — false: oneshot route omits those sections by design, status is set at finalize, and `origin/stage-2` exists.
- Missing type/edge tests — low; int-rationale and punctuation-only cases added; `"2"` priority and instance-passing rejected as negligible.
