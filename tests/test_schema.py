import json
from typing import get_args

import pytest
from pydantic import ValidationError

from triage.schema import ROUTE_FOR_CATEGORY, Category, Route, TriageDecision, validate_decision

VALID = {
    "category": "billing",
    "priority": "P2",
    "route": "billing-team",
    "rationale": "A double charge puts money at stake, so the policy sets P2.",
}


def reject(changes: dict | None = None, drop: str | None = None) -> ValidationError:
    data = {**VALID, **(changes or {})}
    if drop:
        del data[drop]
    with pytest.raises(ValidationError) as err:
        validate_decision(data)
    return err.value


def bad_fields(err: ValidationError) -> set[str]:
    return {str(e["loc"][0]) for e in err.errors()}


def test_valid_decision_is_accepted():
    decision = validate_decision(VALID)
    assert decision.model_dump() == VALID


def test_json_string_is_accepted():
    assert validate_decision(json.dumps(VALID)).priority == "P2"


@pytest.mark.parametrize("category, route", ROUTE_FOR_CATEGORY.items())
def test_every_category_with_its_route_is_accepted(category, route):
    assert validate_decision({**VALID, "category": category, "route": route}).route == route


@pytest.mark.parametrize("priority", ["P1", "P2", "P3", "P4"])
def test_every_priority_is_accepted(priority):
    assert validate_decision({**VALID, "priority": priority}).priority == priority


@pytest.mark.parametrize("field", ["category", "priority", "route", "rationale"])
def test_missing_field_is_rejected(field):
    assert field in bad_fields(reject(drop=field))


@pytest.mark.parametrize(
    "field, value",
    [("category", "sales"), ("priority", "P5"), ("priority", "p2"), ("route", "sales-team")],
)
def test_value_outside_its_set_is_rejected(field, value):
    assert field in bad_fields(reject({field: value}))


@pytest.mark.parametrize("field, value", [("priority", 2), ("rationale", None), ("rationale", 5), ("category", ["billing"])])
def test_wrong_type_is_rejected(field, value):
    assert field in bad_fields(reject({field: value}))


def test_route_that_does_not_match_category_is_rejected():
    err = reject({"route": "bug-team"})
    assert bad_fields(err) == {"route"}
    assert "billing-team" in str(err)


def test_extra_field_is_rejected():
    assert "escalate" in bad_fields(reject({"escalate": True}))


@pytest.mark.parametrize("rationale", ["", "   "])
def test_empty_rationale_is_rejected(rationale):
    assert bad_fields(reject({"rationale": rationale})) == {"rationale"}


@pytest.mark.parametrize(
    "rationale",
    [
        "Money is at stake. The policy sets P2.",
        "Is this billing? Yes, it is.",
        "Double charge, so P2",
        "Money.Two sentences here.",
        "Line one\n\nline two.",
        '".',
    ],
)
def test_rationale_that_is_not_one_sentence_is_rejected(rationale):
    assert bad_fields(reject({"rationale": rationale})) == {"rationale"}


@pytest.mark.parametrize(
    "rationale",
    ['The customer wrote "charged twice."', "Refund is due (billing rule, P2.)", "A $1.5k double charge means P2!"],
)
def test_one_sentence_with_closers_or_decimals_is_accepted(rationale):
    assert validate_decision({**VALID, "rationale": rationale}).rationale == rationale


def test_route_table_covers_every_category_and_route():
    assert set(ROUTE_FOR_CATEGORY) == set(get_args(Category))
    assert set(ROUTE_FOR_CATEGORY.values()) == set(get_args(Route))


def test_malformed_json_is_rejected():
    with pytest.raises(ValidationError):
        validate_decision("not json")


def test_invalid_field_in_json_string_is_named():
    with pytest.raises(ValidationError) as err:
        validate_decision(json.dumps({**VALID, "priority": "P5"}))
    assert bad_fields(err.value) == {"priority"}


def test_rules_are_described_for_structured_output():
    props = TriageDecision.model_json_schema()["properties"]
    assert "category" in props["route"]["description"]
    assert "one sentence" in props["rationale"]["description"]


def test_rationale_whitespace_is_trimmed():
    assert validate_decision({**VALID, "rationale": "  One sentence.  "}).rationale == "One sentence."


def test_model_is_usable_directly():
    assert TriageDecision(**VALID).category == "billing"
