"""Design tokens, risk badges/icons (never colour-only), and central CSS."""

TOKENS = {
    "background": "#F3F7FB",
    "surface": "#FFFFFF",
    "text": "#0F1C2E",
    "muted": "#4A5A6A",
    "border": "#C9D6E3",
    "primary": "#1F4E8C",
    "info": "#0B5C8A",
}

FONT_STACK = (
    '"Noto Sans Bengali","Nirmala UI","Kalpurush","SolaimanLipi",'
    '"Vrinda","Segoe UI",system-ui,sans-serif'
)

# Inline SVGs so risk is always conveyed by colour + word + icon + pattern (offline-safe).
_ICONS = {
    "Low": (
        '<svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>'
    ),
    "Medium": (
        '<svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>'
        '<line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
    ),
    "High": (
        '<svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
    ),
    "Critical": (
        '<svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
    ),
}

TIER_STYLES = {
    "Low": {
        "fg": "#1B6B3A",
        "bg": "#E6F4EA",
        "border": "#9FD4B2",
        "accent": "#1B6B3A",
        "icon": _ICONS["Low"],
    },
    "Medium": {
        "fg": "#7A5200",
        "bg": "#FFF4D6",
        "border": "#E2BE5B",
        "accent": "#7A5200",
        "icon": _ICONS["Medium"],
    },
    "High": {
        "fg": "#B3380F",
        "bg": "#FDE8E0",
        "border": "#E89D82",
        "accent": "#B3380F",
        "icon": _ICONS["High"],
    },
    "Critical": {
        "fg": "#FFFFFF",
        "bg": "#7A0C1E",
        "border": "#590816",
        "accent": "#FFFFFF",
        "icon": _ICONS["Critical"],
    },
}


def risk_badge_html(tier, label, compact=False):
    st = TIER_STYLES[tier]
    pad = "4px 10px" if compact else "6px 14px"
    fsize = "0.92rem" if compact else "1.05rem"
    return (
        f"<span class='risk-pill' style='background:{st['bg']};color:{st['fg']};"
        f"border:1.5px solid {st['border']};padding:{pad};font-size:{fsize}'>"
        f"{st['icon']}<span>{label}</span></span>"
    )


def build_css(lang):
    body_size = "17px" if lang == "bn" else "16px"
    body_lh = "1.7" if lang == "bn" else "1.6"
    return f"""<style>
html, body, [class*="css"], .stMarkdown, button, input, select, textarea {{
  font-family: {FONT_STACK};
  color: {TOKENS['text']};
}}
.stApp {{
  background: {TOKENS['background']};
  font-size: {body_size};
  line-height: {body_lh};
  overflow-x: hidden;
}}
.block-container {{
  padding-top: 1.1rem;
  padding-bottom: 2rem;
  max-width: 1180px;
}}
p, li, span, label {{
  font-size: {body_size};
  line-height: {body_lh};
}}
[data-testid="stSidebar"] {{ display: none; }}
[data-testid="collapsedControl"] {{ display: none; }}

/* Header */
.st-key-app-header {{
  background: linear-gradient(135deg, #0B2545 0%, #13518F 60%, #1F78C8 100%);
  border: none !important;
  border-radius: 10px;
  padding: 12px 18px;
  margin-bottom: 12px;
  box-shadow: 0 4px 14px rgba(11, 37, 69, 0.25);
}}
.hdr-logo {{
  display: flex;
  justify-content: center;
  margin-bottom: 6px;
}}
.hdr-logo svg {{ width: 84px; height: 84px; }}
.hdr-title {{
  text-align: center;
  color: #FFFFFF;
  margin: 0 0 2px 0;
  font-size: 1.85rem;
  font-weight: 700;
  line-height: 1.25;
}}
.hdr-sub {{
  text-align: center;
  color: #D6E6F7;
  margin: 0;
  font-size: 1rem;
  line-height: 1.55;
}}

/* Language toggle & Segmented controls */
.st-key-lang [data-baseweb="button-group"] {{
  justify-content: flex-end;
  width: 100%;
}}
.st-key-lang button,
.st-key-hz button {{
  min-height: 44px !important;
  padding: 8px 16px !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  border: 1px solid {TOKENS['border']} !important;
  color: {TOKENS['text']} !important;
  background: {TOKENS['background']} !important;
  border-radius: 8px !important;
}}
.st-key-lang button[aria-checked="true"],
.st-key-lang button[kind="segmented_controlActive"],
.st-key-hz button[aria-checked="true"],
.st-key-hz button[kind="segmented_controlActive"] {{
  background: {TOKENS['primary']} !important;
  color: #FFFFFF !important;
  border-color: {TOKENS['primary']} !important;
}}

.st-key-lang button[aria-checked="true"],
.st-key-lang button[kind="segmented_controlActive"] {{
  background: #FFB703 !important;
  color: #0B2545 !important;
  border-color: #FFB703 !important;
}}

/* Accessible focus ring & 44px touch targets */
button, [role="tab"], select, input, summary {{
  min-height: 44px;
}}
button:focus-visible, [role="tab"]:focus-visible, select:focus-visible,
input:focus-visible, summary:focus-visible, a:focus-visible {{
  outline: 3px solid {TOKENS['info']} !important;
  outline-offset: 2px !important;
}}

/* Buttons */
.stButton > button {{
  min-height: 44px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 1rem;
  border: 1.5px solid {TOKENS['primary']};
  color: {TOKENS['primary']};
  background: {TOKENS['surface']};
  padding: 8px 16px;
}}
.stButton > button:hover {{
  background: #E3EEFA;
  border-color: {TOKENS['primary']};
  color: {TOKENS['text']};
}}
.stButton > button[kind="primary"] {{
  background: {TOKENS['primary']};
  color: #FFFFFF;
  border-color: {TOKENS['primary']};
}}
.stButton > button[kind="primary"]:hover {{
  background: #163B6E;
  color: #FFFFFF;
}}

/* Step 1 card */
.st-key-step1-box {{
  background: {TOKENS['surface']};
  border: 1px solid {TOKENS['border']} !important;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(20, 33, 27, 0.05);
}}
.step-heading {{
  font-size: 1.2rem;
  font-weight: 700;
  color: {TOKENS['text']};
  margin: 0 0 8px 0;
}}
.weather-note {{
  color: {TOKENS['muted']};
  font-size: 0.96rem;
  margin-top: 6px;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
  gap: 8px;
  border-bottom: 2px solid {TOKENS['border']};
  margin-bottom: 14px;
  flex-wrap: wrap;
}}
.stTabs [data-baseweb="tab"] {{
  min-height: 44px;
  padding: 8px 18px;
  font-weight: 600;
  font-size: 1rem;
  color: {TOKENS['muted']};
  border-radius: 10px 10px 0 0;
  border: 1px solid transparent;
}}
.stTabs [aria-selected="true"] {{
  background: {TOKENS['primary']} !important;
  color: #FFFFFF !important;
  border-color: {TOKENS['primary']} !important;
}}
.stTabs [data-baseweb="tab-highlight"] {{
  display: none;
}}

/* Forecast cards */
.fc-primary {{
  border-radius: 10px;
  padding: 18px 20px;
  border: 1.5px solid {TOKENS['border']};
  box-shadow: 0 1px 4px rgba(20, 33, 27, 0.06);
  margin-bottom: 10px;
}}
.fc-meta {{
  font-size: 0.96rem;
  font-weight: 600;
  margin-bottom: 8px;
}}
.fc-risk-row {{
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1.25;
  margin: 4px 0 8px 0;
}}
.fc-risk-row svg {{
  width: 30px;
  height: 30px;
  flex-shrink: 0;
}}
.fc-sentence {{
  font-size: 1.12rem;
  font-weight: 600;
  margin: 0 0 8px 0;
}}
.fc-stats {{
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: baseline;
  margin: 6px 0;
}}
.fc-cases {{
  font-size: 1.25rem;
  font-weight: 700;
}}
.fc-range {{
  font-size: 1rem;
  font-weight: 500;
}}
.fc-note {{
  font-size: 0.96rem;
  margin: 6px 0 0 0;
  opacity: 0.95;
}}
.fc-secondary {{
  background: {TOKENS['surface']};
  border: 1px solid {TOKENS['border']};
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 6px;
}}
.fc-sec-date {{
  font-size: 0.92rem;
  color: {TOKENS['muted']};
  font-weight: 600;
  margin-bottom: 6px;
}}
.fc-sec-num {{
  font-size: 1.05rem;
  font-weight: 600;
  color: {TOKENS['text']};
  margin-top: 6px;
}}

/* Risk pill */
.risk-pill {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 8px;
  font-weight: 700;
  line-height: 1.2;
  white-space: nowrap;
}}

/* Action card */
.action-card {{
  border-radius: 10px;
  padding: 16px 20px;
  margin: 8px 0 12px 0;
  border-width: 1.5px;
  border-style: solid;
  box-shadow: 0 1px 3px rgba(20, 33, 27, 0.05);
}}
.action-card h3 {{
  margin: 0 0 8px 0;
  font-size: 1.32rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.action-card ul {{
  margin: 0;
  padding-left: 1.25rem;
}}
.action-card li {{
  margin-bottom: 6px;
}}

/* Trust & Help cards */
.trust-card {{
  background: {TOKENS['surface']};
  border: 1px solid {TOKENS['border']};
  border-top: 4px solid {TOKENS['primary']};
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 10px;
}}
.trust-lbl {{
  color: {TOKENS['muted']};
  font-size: 0.96rem;
  font-weight: 600;
  margin-bottom: 4px;
}}
.trust-val {{
  color: {TOKENS['text']};
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1.25;
}}
.takeaway-line {{
  background: {TOKENS['surface']};
  border-left: 4px solid {TOKENS['info']};
  border-radius: 0 8px 8px 0;
  padding: 8px 14px;
  margin: 6px 0 10px 0;
  font-weight: 600;
  color: {TOKENS['text']};
}}
.scenario-banner {{
  background: #FFF4D6;
  color: #7A5200;
  border: 1px solid #E2BE5B;
  border-radius: 8px;
  padding: 8px 14px;
  font-weight: 600;
  margin-bottom: 10px;
}}
.help-answer {{
  background: {TOKENS['surface']};
  border: 1.5px solid {TOKENS['info']};
  border-radius: 10px;
  padding: 14px 18px;
  margin-top: 10px;
}}

/* Priority table */
.table-scroll {{
  width: 100%;
  overflow-x: auto;
  border: 1px solid {TOKENS['border']};
  border-radius: 10px;
  background: {TOKENS['surface']};
}}
.pri-table {{
  width: 100%;
  border-collapse: collapse;
  min-width: 640px;
  font-size: 0.96rem;
}}
.pri-table th {{
  background: {TOKENS['background']};
  color: {TOKENS['text']};
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid {TOKENS['border']};
  font-weight: 700;
}}
.pri-table td {{
  padding: 10px 12px;
  border-bottom: 1px solid #E1E9F2;
  color: {TOKENS['text']};
  vertical-align: middle;
}}
.pri-table tr.top5-row {{
  background: #EEF4FB;
}}
.rank-tag {{
  display: inline-block;
  background: {TOKENS['primary']};
  color: #FFFFFF;
  font-size: 0.82rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 6px;
  margin-right: 6px;
}}

/* Footer */
.app-footer {{
  margin-top: 24px;
  padding-top: 14px;
  border-top: 1px solid {TOKENS['border']};
  color: {TOKENS['muted']};
  font-size: 0.95rem;
}}
.app-footer p {{
  margin: 0 0 4px 0;
  font-size: 0.95rem;
  color: {TOKENS['muted']};
}}

/* Mobile responsive (390px) */
@media (max-width: 640px) {{
  .block-container {{
    padding-left: 0.75rem;
    padding-right: 0.75rem;
    padding-top: 0.65rem;
  }}
  .hdr-title {{ font-size: 1.45rem; }}
  .fc-risk-row {{ font-size: 1.45rem; }}
  .st-key-lang [data-baseweb="button-group"] {{
    justify-content: flex-start;
    margin-top: 8px;
  }}
}}
</style>"""
