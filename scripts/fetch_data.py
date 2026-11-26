"""Download IIMA's factor library, RBI's month-end G-sec yields and Yahoo gold prices into data/
(none of it committed)."""

from rp import gold, iima, rbi

if __name__ == "__main__":
    print(f"IIMA release {iima.fetch()}")
    y = rbi.fetch()
    print(f"RBI yields: {y['date'].min():%b %Y}-{y['date'].max():%b %Y}")
    g = gold.fetch()
    print(f"Yahoo: {g.index.min():%b %Y}-{g.index.max():%b %Y}, {list(g.columns)}")
