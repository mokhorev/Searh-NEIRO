from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

try:
    from neirosearch.statistics_view import render_statistics_page
except ImportError:
    src_root = Path(__file__).resolve().parents[1]
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    from neirosearch.statistics_view import render_statistics_page


def main() -> None:
    st.set_page_config(page_title="Searh-NEIRO - Статистика", layout="wide")
    render_statistics_page(title="Статистика массовой проверки")


if __name__ == "__main__":
    main()
