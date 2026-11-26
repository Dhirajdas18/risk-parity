# Risk Parity

[![CI](https://github.com/Dhirajdas18/risk-parity/actions/workflows/ci.yml/badge.svg)](https://github.com/Dhirajdas18/risk-parity/actions/workflows/ci.yml)
[![Risk parity lab](https://github.com/Dhirajdas18/risk-parity/actions/workflows/pages.yml/badge.svg)](https://dhirajdas18.github.io/risk-parity/)

Risk parity across Indian stocks, government bonds and gold, January 2004 to December 2025: stocks
and cash from IIM Ahmedabad's factor library, gilt returns built from RBI's month-end yields, and
gold in rupees from Yahoo Finance. Equal risk contribution against 60/40, leverage, estimation and
rebalancing out of sample, crises, minimum variance and maximum Sharpe, and a verdict.

**Live risk parity lab: [dhirajdas18.github.io/risk-parity](https://dhirajdas18.github.io/risk-parity/)**,
pick the assets, the years and the estimation window, and see risk parity's weights, each asset's
share of risk and growth against 60/40 and equal weight, computed month by month in your browser.

## Features

- [x] What risk parity does: equal risk contribution against 60/40, equal weight and inverse volatility
- [ ] Leverage: unlevered risk parity, borrowing at Indian rates, and a volatility target
- [ ] Estimation window, EWMA and rebalancing frequency, after costs, out of sample
- [ ] Crises: 2008, the 2013 taper, 2020 and 2022
- [ ] Risk parity against minimum variance and maximum Sharpe, out of sample
- [ ] Which assets: a short gilt, and how much gold's measurement matters
- [ ] Verdict: a portfolio-construction rule for the reference model beyond stocks

## Findings

### 1. In 60/40, stocks carried 96% of the risk; risk parity spread it evenly

<a href="docs/img/basics.png"><picture><source media="(prefers-reduced-motion: reduce)" srcset="docs/img/basics.png"><img src="docs/img/basics.gif" alt="Each asset's share of portfolio risk under equal weight, 60/40, inverse volatility and risk parity, and walk-forward growth of one rupee in each, 2007-2025" width="720"></picture></a>

Monthly returns in rupees, January 2004 to December 2025 (264 months): stocks are IIMA's broad
market including dividends; the 10-year gilt is a par bond bought at each month-end at RBI's yield
and repriced a month later at the yield for its shorter life, plus a month's coupon; gold is COMEX
gold futures times the rupee rate, which leaves out India's import duty (it tracked the GOLDBEES ETF
with a monthly correlation of 0.87 and 11.9% against 11.7% a year from 2009); cash is IIMA's
risk-free rate. An asset's risk contribution is its weight times its covariance with the portfolio;
equal risk contribution (ERC) weights make those contributions equal. Full-sample weights describe
the period with hindsight; the walk-forward sets each month's weights from the previous 36 months
only and holds them for the month (January 2007 to December 2025), with no costs.

- **The three assets barely moved together.** Monthly correlations were −0.01 (stocks and gilt),
  −0.05 (stocks and gold) and −0.09 (gilt and gold). Stocks compounded 14.9% a year with 21.7%
  volatility, gold 14.7% with 16.7%, the 10-year gilt 7.1% with 6.9%, cash 6.3%.
- **60/40 was a stock portfolio.** With 60% in stocks and 40% in the gilt, stocks carried 96% of the
  risk; an equal split still left them 61%.
- **Risk parity put most of the money in the calmest asset.** Its full-sample weights were 18%
  stocks, 58% gilt and 24% gold, each carrying a third of the risk; with correlations near zero,
  inverse volatility gave almost the same weights.
- **Walk-forward, risk parity matched 60/40's return with half the volatility.** It compounded
  11.6% a year against 11.3%, with volatility of 6.4% against 13.0%, a Sharpe ratio above cash of
  0.77 against 0.41 and a worst fall of −8% against −39%. Equal weight compounded 12.7% (Sharpe
  0.70, worst fall −18%).

## Quick start

```bash
uv sync
uv run python scripts/fetch_data.py   # IIMA, RBI yields and Yahoo gold -> data/
uv run rp report basics               # topics: basics
uv run python scripts/build_site.py   # risk parity lab -> site/index.html
uv run pytest
```

The data files are downloaded, not committed.

## Design

- `src/rp/iima.py`: IIM Ahmedabad's factor library (stocks and the risk-free rate).
- `src/rp/rbi.py`: RBI's month-end SGL yields by maturity from the Handbook editions.
- `src/rp/gold.py`: gold in rupees (COMEX gold times the rupee rate) and GOLDBEES from Yahoo, with
  retries.
- `src/rp/assets.py`: the monthly asset table; gilt returns by repricing a par bond.
- `src/rp/weights.py`: risk contributions, inverse volatility, equal risk contribution (cyclical
  coordinate descent), minimum variance and maximum Sharpe (SLSQP).
- `src/rp/backtest.py`: walk-forward portfolios from past months only, with turnover and costs, and
  summary statistics.
- `src/rp/rp.js`: the lab's browser copy of the covariance, ERC weights and walk-forward, tested
  against Python through Node.
- `src/rp/site.py`: the risk parity lab, one static Plotly page carrying the monthly returns.
- `src/rp/reports.py`: README findings, reproducible with `rp report <topic>`.
- Conventions: monthly simple returns in rupees; volatility √12 times monthly; growth compounded over
  calendar time; Sharpe ratios above IIMA's risk-free rate.
- Data: IIM Ahmedabad's Indian Fama-French-momentum data library (Agarwalla, Jacob and Varma, 2013,
  Four factor model in Indian equities market, IIMA Working Paper 2013-09-05); Reserve Bank of India,
  Handbook of Statistics on Indian Economy (month-end SGL yields); Yahoo Finance (GC=F, USDINR=X,
  GOLDBEES.NS).
- Charts: one validated palette; README charts are animated GIFs with a static fallback for
  reduced-motion users.

Research only, not investment advice. MIT licence.
