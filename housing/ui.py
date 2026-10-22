"""Shared presentation helpers: CSS, headline, KPIs, signed percents, metro state, data-down notice, Plotly template."""
from __future__ import annotations

import html
import re

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

D1 = "Forecasts are statistical estimates, not financial advice."
D2 = ("This is an estimate, not a loan quote or offer, and not financial advice. Nothing you enter is stored, "
      "and we collect no personal data beyond a credit band.")
D3 = ("Long-horizon projections are highly uncertain: years 2 and later extend this market's past growth. "
      "Not a prediction and not financial advice.")
ZILLOW_DOWN = ("Heads up: we can't reach Zillow's home-value data right now. "
               "Check your connection, or try again in a few minutes.")
UP, DOWN, FLAT = "#35742f", "#41629f", "#948584"  # --viz-up, --viz-down, --viz-flat
INK, TEAL, AMBER, VIOLET, GREY = "#312d2c", "#007a87", "#b7791f", "#7a5cb8", "#948584"
BAND = "rgba(49,45,44,0.12)"
FONT = '"Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif'

CSS = """<style>
:root{--positive:#35742f;--negative:#41629f;--neutral-3:#f3efef;--neutral-4:#ece6e6;--neutral-6:#d9d0cf;--neutral-9:#948584;--neutral-11:#696160;--neutral-12:#312d2c;
--accent-3:#ffebea;--accent-10:#c74248;--accent-11:#974847;--background:#fdfcfc;--surface:#faf8f8;--surface-hover:var(--neutral-3);
--surface-active:var(--neutral-4);--border-subtle:var(--neutral-6);--text:var(--neutral-12);--text-secondary:var(--neutral-11);
--accent-bg-subtle:var(--accent-3);--accent-solid:var(--accent-10);--accent-solid-hover:var(--accent-11);--accent-text:var(--accent-11);
--on-accent:#ffffff;--focus-ring:var(--accent-10);--control-border:var(--neutral-9);
--font-display:"Newsreader",Georgia,"Times New Roman",serif;--text-xs:.75rem;--text-sm:.875rem;--text-base:1rem;--text-3xl:2.25rem;
--space-1:4px;--space-2:8px;--space-3:12px;--space-4:16px;--space-6:24px;--space-8:32px;--space-12:48px;
--radius-sm:6px;--radius-md:10px;--radius-pill:999px;
--c-btn-radius:var(--radius-sm);--c-input-min-h:2.5rem;--c-btn-min-h:var(--c-input-min-h);
--c-focus-outline:2px solid var(--focus-ring);--c-focus-offset:2px;
--c-menu-bg:var(--background);--c-menu-border:var(--control-border);--c-input-radius:var(--radius-sm);
--c-menu-option-hover-bg:var(--surface-hover);--c-menu-option-highlight-bg:var(--surface-active);--c-menu-option-selected-bg:var(--accent-bg-subtle);
--c-nav-radius:var(--radius-pill);--c-nav-active-bg:var(--accent-bg-subtle);--c-nav-active-fg:var(--accent-text);--c-nav-bar:4px;
--c-roofline-color:var(--accent-solid);--c-roofline-gap:var(--space-3);--c-answer-size:var(--text-3xl);--c-answer-gap-below:var(--space-8);
--c-kpi-pad:var(--space-4);--c-kpi-radius:var(--radius-md);--c-kpi-gap:var(--space-4);
--c-disclaimer-bg:var(--surface);--c-disclaimer-border:var(--border-subtle);--c-disclaimer-fg:var(--text-secondary);
--c-callout-radius:var(--radius-md);--c-callout-pad:var(--space-4);--c-state-bar:4px;--c-motion:150ms;}
[data-testid="stMainBlockContainer"]{max-width:1120px;padding-top:var(--space-8);}
.mm-answer{margin:var(--space-2) 0 var(--c-answer-gap-below);}
.mm-answer::before{content:"";display:block;width:40px;height:10px;margin-bottom:var(--c-roofline-gap);background:var(--c-roofline-color);
clip-path:polygon(0 100%,50% 0,100% 100%,100% 140%,50% 40%,0 140%);}
.mm-answer h1{font-family:var(--font-display);font-size:var(--c-answer-size);font-weight:500;line-height:1.2;color:var(--text);margin:0;padding:0;}
.mm-answer__sub{font-size:var(--text-sm);color:var(--text-secondary);margin:var(--space-2) 0 0;}
.mm-disclaimer{background:var(--c-disclaimer-bg);border:1px solid var(--c-disclaimer-border);border-radius:var(--c-callout-radius);
padding:var(--c-callout-pad);color:var(--c-disclaimer-fg);font-size:var(--text-sm);margin:var(--space-4) 0;}
.mm-up{color:var(--positive)}.mm-down{color:var(--negative)}
.mm-readout{font-size:var(--text-base);font-weight:600;color:var(--text);}
.mm-readout small{display:block;font-size:var(--text-xs);font-weight:400;color:var(--text-secondary);}
.mm-brand{font-family:var(--font-display);font-size:1.5rem;font-weight:600;color:var(--text);}
.mm-brand small{display:block;font-family:inherit;font-size:var(--text-xs);font-weight:400;color:var(--text-secondary);}
[data-testid="stMetric"]{padding:var(--c-kpi-pad);border-radius:var(--c-kpi-radius);font-variant-numeric:tabular-nums;}
[data-testid="stMetricLabel"]{color:var(--text-secondary);font-size:var(--text-sm);}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] *{font-size:1.35rem;white-space:nowrap !important;overflow-wrap:normal !important;min-width:0;}
[data-testid="stMetricLabel"] *,[data-testid="stMetricDelta"] *{white-space:normal !important;overflow:visible !important;text-overflow:clip !important;overflow-wrap:anywhere;}
[data-testid="stHorizontalBlock"]{gap:var(--c-kpi-gap);align-items:stretch;}
[data-testid="stMetric"]{height:100%;box-sizing:border-box;min-width:0;}
[data-testid="stSliderTickBar"],[data-testid="stSliderTickBar"] *{color:var(--text-secondary) !important;opacity:1 !important;}
[data-testid="stSlider"] [data-testid="stSliderThumbValue"],[data-testid="stSlider"] [data-testid="stSliderThumbValue"] *{color:var(--text);}
[data-testid="stSidebarNavLink"]{min-height:var(--c-input-min-h);border-radius:var(--c-nav-radius);transition:background var(--c-motion) ease-out;}
[data-testid="stSidebarNavLink"]:hover{background:var(--surface-hover);}
[data-testid="stSidebarNavLink"][aria-current="page"]{background:var(--c-nav-active-bg);color:var(--c-nav-active-fg);font-weight:600;
box-shadow:inset var(--c-nav-bar) 0 0 var(--accent-solid);}
[data-testid="stSidebarUserContent"]{padding:var(--space-2) var(--space-6);}
[data-testid="stAlertContainer"]{border-left:var(--c-state-bar) solid var(--text-secondary);border-radius:var(--c-callout-radius);padding:var(--c-callout-pad);}
[data-testid^="stBaseButton-"]{min-height:var(--c-btn-min-h);border-radius:var(--c-btn-radius);font-weight:600;transition:background var(--c-motion) ease-out;}
[data-testid="stBaseButton-primary"]{background:var(--accent-solid);color:var(--on-accent);}
[data-testid="stBaseButton-primary"]:hover{background:var(--accent-solid-hover);}
[data-testid="stBaseButton-primary"]:active{background:var(--accent-solid-hover);}
[data-testid="stBaseButton-primary"]:disabled{background:var(--surface-active);color:var(--text-secondary);}
[data-testid="stBaseButton-secondary"]{background:var(--background);color:var(--text);border:1px solid var(--control-border);}
[data-testid="stBaseButton-secondary"]:hover{background:var(--surface-hover);}
[data-testid="stBaseButton-secondary"]:active{background:var(--surface-active);border-color:var(--text-secondary);}
[data-testid="stBaseButton-secondary"]:disabled{color:var(--text-secondary);border-color:var(--border-subtle);}
[data-testid="stBaseButton-tertiary"]{min-height:2rem;color:var(--accent-text);text-decoration:underline;}
[data-testid="stBaseButton-tertiary"]:hover{background:var(--surface-hover);}
[data-testid="stBaseButton-tertiary"]:active{background:var(--surface-active);}
[data-testid="stTab"]{min-height:var(--c-input-min-h);}
[data-testid="stTab"][aria-selected="true"]{color:var(--accent-text);font-weight:600;box-shadow:inset 0 calc(-1 * var(--c-state-bar)) 0 var(--accent-solid);}
[data-testid="stTab"]:hover{background:var(--surface-hover);}
[data-testid="stExpander"] summary{font-weight:600;min-height:2rem;}
[data-testid="stExpander"] summary:hover{background:var(--surface-hover);}
[data-testid="stSelectboxVirtualDropdown"]{background:var(--c-menu-bg);border:1px solid var(--c-menu-border);border-radius:var(--c-input-radius);}
[data-testid="stSelectboxVirtualDropdown"] [role="option"]{color:var(--text);}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-hovered]{background:var(--c-menu-option-hover-bg);}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][data-focused]{background:var(--c-menu-option-highlight-bg);outline:var(--c-focus-outline);outline-offset:-2px;}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"]{background:var(--c-menu-option-selected-bg);font-weight:600;}
[data-testid="stAppViewContainer"] :focus-visible,[data-testid^="stBaseButton-"]:focus-visible,[data-testid="stSidebarNavLink"]:focus-visible,
[data-testid="stTab"]:focus-visible,[data-testid="stExpander"] summary:focus-visible,[data-testid="stSelectbox"] :focus-visible,[data-testid="stSelectbox"] div:has(> input:focus-visible),[data-testid="stSelectbox"] [role="combobox"]:focus-within,
[data-testid="stMultiSelect"] :focus-visible,input:focus-visible{outline:var(--c-focus-outline);outline-offset:var(--c-focus-offset);}
[data-testid="stSlider"] div:has(> input[type="range"]:focus-visible){outline:var(--c-focus-outline);outline-offset:var(--c-focus-offset);}
@media (prefers-reduced-motion:reduce){*{transition:none !important;animation:none !important;}}
</style>"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def color_deltas(escaped: str) -> str:
    """Wrap '▲ +4.2%' / '▼ −1.8%' in green / slate-blue spans. Input must already be HTML-escaped."""
    return re.sub(r"([▲▼]) [+−][\d.,]+%", lambda m: f'<span class="{"mm-up" if m[1] == "▲" else "mm-down"}">{m[0]}</span>', escaped)


def headline(text: str, sub: str | None = None) -> None:
    s = f'<p class="mm-answer__sub">{html.escape(sub)}</p>' if sub else ""
    st.markdown(f'<div class="mm-answer"><h1>{color_deltas(html.escape(text))}</h1>{s}</div>', unsafe_allow_html=True)


def disclaimer(text: str = D1) -> None:
    st.markdown(f'<div class="mm-disclaimer" role="note">{html.escape(text)}</div>', unsafe_allow_html=True)


def signed(v: float, digits: int = 1) -> str:
    """'+1.3%' / '−2.1%' (U+2212) from a fraction; 'n/a' when missing."""
    if v is None or pd.isna(v):
        return "n/a"
    p = round(v * 100, digits)
    return f"{'+' if p > 0 else '−' if p < 0 else ''}{abs(p):.{digits}f}%"


def fmt_pct(v: float, digits: int = 1) -> str:
    """'▲ +4.2%' / '▼ −1.8%' from a fraction; '0.0%' for zero; 'n/a' when missing."""
    if v is None or pd.isna(v):
        return "n/a"
    p = round(v * 100, digits)
    return (f"▲ {signed(v, digits)}" if p > 0 else f"▼ {signed(v, digits)}" if p < 0 else f"{abs(p):.{digits}f}%")


def kpi(col, label: str, value: str, delta: str | None = None, help: str | None = None) -> None:
    """Bordered equal-height metric. '+x' delta gets ▲ green, '−x' gets ▼ slate blue, any other text is a gray note."""
    c, d = "gray", delta
    if d is not None:
        d = str(d).replace("$", "\\$")
        if d.startswith("+"):
            d, c = "▲ " + d, "green"
        elif d.startswith(("−", "-")):
            d, c = "▼ " + d, "violet"
    col.metric(label, value, d, delta_color=c, delta_arrow="off", help=help, border=True, height="stretch")


def go_to(page_key: str, label: str, primary: bool = False, key: str | None = None) -> None:
    """Button that navigates to a page registered in st.session_state['_nav'] by app.py."""
    if st.button(label, type="primary" if primary else "secondary", key=key or f"go_{page_key}_{label}"):
        st.switch_page(st.session_state["_nav"][page_key])


def retry_button(key: str = "retry") -> None:
    """'Try again': clear cached loads and the cached model, then rerun."""
    if st.button("Try again", key=key):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()


def data_down(text: str = ZILLOW_DOWN) -> None:
    st.warning(text)
    retry_button()


# ---- shared metro -------------------------------------------------------------------------------------------------
def sync_metro(regions: list[str] | None) -> None:
    """Resolve st.session_state['metro'] from state or ?metro=, validate against regions, mirror to the URL.

    regions=None means the metro list is unavailable: keep state as is, do not validate or wipe it.
    """
    metro = st.session_state.get("metro")
    if not metro and st.query_params.get("metro"):
        metro, st.session_state["metro_src"] = st.query_params["metro"], "url"
    if metro and regions is not None and metro not in regions:
        st.info(f"We couldn't find '{metro}'. Choose a metro.")
        metro = None
    st.session_state["metro"] = metro
    if metro:
        st.query_params["metro"] = metro
    elif "metro" in st.query_params:
        del st.query_params["metro"]


def metro_picker(regions: list[str] | None, key: str, label: str = "Metro", placeholder: str = "Choose a metro") -> str | None:
    """Selectbox bound to the shared metro. Returns the current shared metro."""
    pk = f"metro_pick_{key}"
    if st.session_state.get(pk) != st.session_state.get("metro"):
        st.session_state[pk] = st.session_state.get("metro")

    def _set() -> None:
        st.session_state["metro"] = st.session_state[pk]
        st.session_state["metro_src"] = key
        if st.session_state[pk]:
            st.query_params["metro"] = st.session_state[pk]
        elif "metro" in st.query_params:
            del st.query_params["metro"]

    st.selectbox(label, regions or [], index=None, key=pk, on_change=_set, disabled=regions is None,
                 placeholder=placeholder if regions is not None else "Metro list unavailable")
    return st.session_state.get("metro")


def sidebar(regions: list[str] | None) -> None:
    sb = st.sidebar
    sb.markdown('<div class="mm-brand">MarketMachine<small>US housing market analytics and forecasts</small></div>',
                unsafe_allow_html=True)
    metro = st.session_state.get("metro")
    sb.markdown(f'<div class="mm-readout"><small>Selected metro</small>{html.escape(metro) if metro else "No metro selected"}</div>',
                unsafe_allow_html=True)
    if sb.button("Change" if metro else "Choose a metro", type="tertiary", key="metro_change"):
        st.session_state["show_picker"] = not st.session_state.get("show_picker", False)
    if st.session_state.get("show_picker"):
        with sb:
            metro_picker(regions, "sidebar")
    sb.caption(D1)


# ---- Plotly -------------------------------------------------------------------------------------------------------
def _template() -> go.layout.Template:
    ax = dict(tickfont=dict(size=12, color="#696160"), title=dict(font=dict(size=14, color="#696160"), standoff=12),
              ticks="", zeroline=False, automargin=True)
    return go.layout.Template(layout=go.Layout(
        font=dict(family=FONT, size=14, color=INK), paper_bgcolor="#fdfcfc", plot_bgcolor="#fdfcfc",
        xaxis=dict(showgrid=False, showline=True, linecolor="#cbc1c0", **ax),
        yaxis=dict(showgrid=True, gridcolor="#ece6e6", gridwidth=1, showline=False, **ax),
        legend=dict(orientation="h", y=1.08, x=0, entrywidth=0.3, entrywidthmode="fraction", font=dict(size=14, color=INK)),
        hoverlabel=dict(bgcolor="#fdfcfc", bordercolor=GREY, font=dict(family=FONT, size=14, color=INK)),
        hovermode="x unified", margin=dict(l=48, r=24, t=32, b=40), height=360,
        colorway=[INK, TEAL, AMBER, VIOLET], transition=dict(duration=0),
    ))


pio.templates["marketmachine"] = _template()
pio.templates.default = "marketmachine"


def show(fig: go.Figure, height: int | None = None) -> None:
    fig.update_layout(paper_bgcolor="#fdfcfc", plot_bgcolor="#fdfcfc")
    if height:
        fig.update_layout(height=height)
    st.plotly_chart(fig, theme=None, width="stretch", config={"displayModeBar": False})


def zero_line(fig: go.Figure, **kw) -> None:
    fig.add_hline(y=0, line_width=1, line_color=GREY, **kw)


def signed_axis(fig: go.Figure, lo: float, hi: float, axis: str = "y", **kw) -> None:
    """Signed percent ticks (true minus, unsigned 0%) for data in percent units spanning lo..hi."""
    step = next((t for t in (1, 2, 5, 10, 20, 50, 100) if (hi - lo) / t <= 8), 100)
    vals = [v for v in range(int(lo // step) * step, int(hi // step + 1) * step + 1, step)]
    text = ["0%" if v == 0 else f"{'+' if v > 0 else '−'}{abs(v)}%" for v in vals]
    getattr(fig, f"update_{axis}axes")(tickvals=vals, ticktext=text, **kw)


def end_range(fig: go.Figure, first, last) -> None:
    """Shared x-axis rule: end 2 months after the last data or forecast point."""
    fig.update_xaxes(range=[first, last + pd.DateOffset(months=2)])


def history_band(hist: pd.Series, pred: float | None, lo: float | None, hi: float | None, name: str, months: int = 12,
                 years: int | None = None) -> go.Figure:
    """Solid history, dashed projection `months` out, 80% range band. hist is date-indexed values; pred/lo/hi fractions.
    years limits the visible window (the full series is still plotted)."""
    full = hist
    if years:
        hist = hist[hist.index >= hist.index[-1] - pd.DateOffset(years=years)]
    hist = hist if len(hist) else full
    fig = go.Figure(go.Scatter(x=hist.index, y=hist.values, name=name, line=dict(color=INK, width=2.5),
                               hovertemplate="%{y:$,.0f}"))
    ys = [float(hist.min()), float(hist.max())]
    if pred is not None and pd.notna(pred):
        x0, v0 = hist.index[-1], float(hist.iloc[-1])
        x1 = x0 + pd.DateOffset(months=months)
        ys += [v0 * (1 + lo), v0 * (1 + hi)]
        # ponytail: thin grey outline on the band so its legend swatch is visible; DESIGN.md says no outline
        fig.add_trace(go.Scatter(x=[x0, x1, x1, x0], y=[v0, v0 * (1 + lo), v0 * (1 + hi), v0], fill="toself", mode="lines",
                                 line=dict(color="#cbc1c0", width=1), fillcolor=BAND, name="80% range", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[x0, x1], y=[v0, v0 * (1 + pred)], name="Forecast", line=dict(color=INK, width=2.5, dash="dash"),
                                 hovertemplate=f"{fmt_pct(pred)} (80% range {signed(lo)} to {signed(hi)})"))
        fig.add_annotation(x=x1, y=v0 * (1 + pred), text=fmt_pct(pred), showarrow=False, xanchor="left", xshift=6,
                           font=dict(size=14, color=INK))
        fig.add_vline(x=x0, line_width=1, line_color="#cbc1c0", annotation_text="Today", annotation_font=dict(size=12, color="#696160"))
    end_range(fig, hist.index[0], x1 if pred is not None and pd.notna(pred) else hist.index[-1] - pd.DateOffset(months=2))
    pad = (max(ys) - min(ys)) * 0.05
    fig.update_yaxes(tickformat="$,.0f", title="Typical value ($)", range=[min(ys) - pad, max(ys) + pad])
    fig.update_layout(margin=dict(r=90))
    return fig
