// Risk parity in the browser, mirrored from rp/weights.py and rp/backtest.py (tested through Node).
const RP = (() => {
  function cov(X) {
    const T = X.length, n = X[0].length;
    const m = Array.from({ length: n }, (_, j) => X.reduce((s, r) => s + r[j], 0) / T);
    return Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) =>
      X.reduce((s, r) => s + (r[i] - m[i]) * (r[j] - m[j]), 0) / (T - 1)));
  }
  function erc(S, tol = 1e-12, iters = 10000) {
    const n = S.length, b = 1 / n;
    const y = S.map((r, i) => 1 / Math.sqrt(r[i]));
    for (let it = 0; it < iters; it++) {
      const prev = y.slice();
      for (let i = 0; i < n; i++) {
        const a = S[i][i];
        let c = 0;
        for (let j = 0; j < n; j++) if (j !== i) c += S[i][j] * y[j];
        y[i] = (-c + Math.sqrt(c * c + 4 * a * b)) / (2 * a);
      }
      const big = Math.max(...y.map(Math.abs));
      if (Math.max(...y.map((v, i) => Math.abs(v - prev[i]))) < tol * big) break;
    }
    const s = y.reduce((u, v) => u + v, 0);
    return y.map((v) => v / s);
  }
  function riskShares(w, S) {
    const Sw = S.map((r) => r.reduce((s, v, j) => s + v * w[j], 0));
    const rc = w.map((v, i) => v * Sw[i]);
    const t = rc.reduce((u, v) => u + v, 0);
    return rc.map((v) => v / t);
  }
  // Walk-forward: weights from the previous `window` rows, held over the next row.
  function run(X, rule, window) {
    const out = [];
    for (let t = window; t < X.length; t++) {
      const w = rule(X.slice(t - window, t));
      out.push({ t, w, r: w.reduce((s, v, j) => s + v * X[t][j], 0) });
    }
    return out;
  }
  return { cov, erc, riskShares, run };
})();
if (typeof module !== "undefined") module.exports = RP;
