import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rp import backtest as B
from rp import weights as W

JS = Path(__file__).parents[1] / "src" / "rp" / "rp.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def test_js_erc_and_walk_forward_match_python():
    rng = np.random.default_rng(6)
    X = rng.normal(0.008, [0.06, 0.02, 0.045], (80, 3)) + rng.normal(0, 0.01, (80, 1))
    code = (f"const RP = require({json.dumps(str(JS))}); const X = {json.dumps(X.tolist())};"
            "const S = RP.cov(X); const w = RP.erc(S);"
            "const wf = RP.run(X, (p) => RP.erc(RP.cov(p)), 36);"
            "console.log(JSON.stringify({w, rs: RP.riskShares(w, S), r: wf.map((o) => o.r)}));")
    js = json.loads(subprocess.run(["node", "-e", code], capture_output=True, text=True,
                                   check=True).stdout)
    S = np.cov(X, rowvar=False)
    assert np.allclose(js["w"], W.erc(S), atol=1e-10)
    assert np.allclose(js["rs"], 1 / 3, atol=1e-8)
    idx = pd.date_range("2000-01-31", periods=80, freq="ME")
    py = B.run(pd.DataFrame(X, index=idx), lambda p: W.erc(np.cov(p, rowvar=False)), 36)
    assert np.allclose(js["r"], py["gross"], atol=1e-12)
