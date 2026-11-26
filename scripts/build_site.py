"""Build site/index.html from the fetched data (run scripts/fetch_data.py first)."""

from pathlib import Path

from rp import assets, iima
from rp.site import build_html


def main() -> None:
    t = assets.table()
    out = Path("site/index.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(build_html(t, iima.release()), encoding="utf-8")
    print(f"{out} ({out.stat().st_size / 1e3:.0f} kB), {len(t)} months")


if __name__ == "__main__":
    main()
