import numpy as np
import pandas as pd

from rp import site


def test_page_builds_with_data_and_format_parts():
    idx = pd.date_range("2004-01-31", periods=60, freq="ME")
    cols = ["equity", "gilt10", "gilt5", "gold", "cash"]
    t = pd.DataFrame(np.random.default_rng(0).normal(0.01, 0.03, (60, 5)), index=idx, columns=cols)
    html = site.build_html(t, "2025-12")
    assert "$" + "data" not in html and "$" + "js" not in html and "$" + "colors" not in html
    assert "Updated " in html and "Data: stocks and cash" in html and "Research only" in html
    assert '"months":["2004-01-31"' in html and "How to read it:" in html
