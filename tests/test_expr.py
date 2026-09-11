from bio_logic_debugger.core.expr import parse, referenced_ids, try_evaluate


def test_simple_compare():
    ok, reason = try_evaluate("$rice_heading_days < 65", {"rice_heading_days": 60})
    assert ok and reason == ""
    ok, reason = try_evaluate("$rice_heading_days < 65", {"rice_heading_days": 80})
    assert not ok and reason == ""


def test_and_requires_both():
    expr = "$rice_plant_height > 120 AND $rice_lodging_resistance >= 7"
    ok, _ = try_evaluate(expr, {"rice_plant_height": 130, "rice_lodging_resistance": 8})
    assert ok
    ok, _ = try_evaluate(expr, {"rice_plant_height": 130, "rice_lodging_resistance": 5})
    assert not ok


def test_unbound_variable_does_not_fire():
    ok, reason = try_evaluate("$rice_plant_height > 120 AND $rice_lodging_resistance >= 7", {
        "rice_plant_height": 130,
    })
    assert not ok
    assert reason.startswith("unbound:")


def test_empty_and_bad_syntax():
    ok, reason = try_evaluate("", {})
    assert not ok and reason == "empty"
    ok, reason = try_evaluate("foo > 1", {})
    assert not ok and reason.startswith("syntax:")


def test_string_equals_and_not():
    ok, _ = try_evaluate("$drought_severity = 'severe'", {"drought_severity": "severe"})
    assert ok
    ok, _ = try_evaluate("NOT ($rice_cold_tolerance <= 3)", {"rice_cold_tolerance": 8})
    assert ok


def test_referenced_ids():
    node = parse("$a > 1 AND $b >= 2 OR $a < 0")
    assert referenced_ids(node) == ["a", "b"]


def test_negative_number():
    ok, reason = try_evaluate("$delta >= -1.5", {"delta": -1.0})
    assert ok and reason == ""
