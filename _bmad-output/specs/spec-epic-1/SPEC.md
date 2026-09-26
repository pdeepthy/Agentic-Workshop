---
id: SPEC-epic-1
companions: [../../../TRIAGE_POLICY.md, ../../../mcp/triage_server.py]
sources: [../../../INTENT.md]
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Epic 1: triage data and schema

## Why

The workshop's triage agent (Epic 2) and its eval (Epic 3) both need two things that don't exist yet: a fixed shape for a triage decision, so output can be checked, and a local database of tickets and customers for `mcp/triage_server.py` to read. Epic 1 builds that foundation, with no model, network or API key involved, so attendees start from data and a contract they can trust.

## Capabilities

- **CAP-1**
  - **intent:** A triage decision has one strict shape, and anything that doesn't fit it is refused.
  - **success:** A JSON object with `category` in {billing, bug, access, performance, how-to}, `priority` in {P1, P2, P3, P4}, `route` in {billing-team, bug-team, access-team, performance-team, how-to-team} and a `rationale` of exactly one sentence is accepted, provided the route is the one `TRIAGE_POLICY.md` pairs with the category (billing → billing-team, bug → bug-team, access → access-team, performance → performance-team, how-to → how-to-team). A missing field, a value outside its set, a wrong type, a route that doesn't match its category, or a rationale that is empty or longer than one sentence is rejected with an error that names the offending field.

- **CAP-2**
  - **intent:** One command puts the seed data into a local SQLite database.
  - **success:** `uv run python load_seed.py` creates `app.db` with tables `tickets` and `customers`, whose columns match the headers of `seed/tickets.csv` and `seed/customers.csv`, holding 24 and 20 rows respectively.

- **CAP-3**
  - **intent:** Loading is repeatable.
  - **success:** Running `load_seed.py` a second time succeeds and leaves the same tables, columns and rows: no duplicates, no error.

## Constraints

- Python 3.12 or newer, managed with uv.
- Everything in `seed/` is read-only; the loader only reads it.
- No network calls and no API keys in this epic.
- `mcp/triage_server.py` already reads `app.db` (`tickets`: ticket_id, customer_id, created_at, text; `customers`: customer_id, name, plan, open_tickets). Those table and column names must keep working.

## Non-goals

- The agent, the MCP tools, evals and any user interface.

## Success signal

After `uv run python load_seed.py` (run twice), `get_ticket("T-1042")` from `mcp/triage_server.py` returns T-1042 with customer C-77. A decision such as `{"category": "billing", "priority": "P2", "route": "billing-team", "rationale": "..."}` validates, while the same object with `priority: "P5"`, with `route: "bug-team"`, or with a two-sentence rationale is rejected with a clear error.

## Open Questions

- Should `open_tickets` be stored as an INTEGER (the Enterprise rule compares it to 3) or as the CSV's text?
