from bio_logic_debugger.ui.pages import anti_patterns, browser, constraints, literature, validate
from bio_logic_debugger.ui.runtime import trait_label
from tests.test_engine import _engine


def test_page_render_functions_exist():
    assert callable(validate.render)
    assert callable(browser.render)
    assert callable(anti_patterns.render)
    assert callable(constraints.render)
    assert callable(literature.render)


def test_trait_label_uses_public_api():
    engine = _engine()
    label = trait_label(engine, "rice_yield_per_plant")
    assert "单株产量" in label
    assert trait_label(engine, "missing") == "missing"
