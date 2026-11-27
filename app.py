import html as html_lib
import json
import os
import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import auth
from logo import LOGO_SVG
from operations import S as OPS_TEXT, render_operations_page
from command import C as CMD_TEXT, render_beds_page, render_dispatch_page, render_resources_page, render_whatif_page
import streamlit.components.v1 as components

from i18n import (
    TIER_ACTIONS,
    TIER_PLAN,
    city_label,
    driver_label,
    fmt_date,
    fmt_num,
    t,
    tier_name,
    to_bn_digits,
    ward_label,
)
from styles import TIER_STYLES, TOKENS, build_css, risk_badge_html
from src.preprocess import (
    FEATURE_COLS,
    classify_risk_tier,
    derive_features,
    load_and_engineer_features,
    local_driver_effects,
    predict_interval,
)
from src.train import HORIZONS, TIERS, train_and_evaluate

st.set_page_config(
    page_title="ডেঙ্গু আগাম সতর্কতা | Dengue Early Warning",
    page_icon="🦟",
    layout="wide",
)

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}
DATA = "data/hackathon_preli_dataset.xlsx"
WEEK = pd.Timedelta(weeks=1)


def _active_lang():
    return "en" if st.session_state.get("lang") == "English" else "bn"


def _keep_lang():
    if st.session_state.get("lang") in ("বাংলা", "English"):
        st.session_state["_last_lang"] = st.session_state["lang"]
    else:
        st.session_state["lang"] = st.session_state.get("_last_lang", "বাংলা")


def _keep_horizon():
    if st.session_state.get("hz") in HORIZONS:
        st.session_state["_last_hz"] = st.session_state["hz"]
    else:
        st.session_state["hz"] = st.session_state.get("_last_hz", 2)


def _select_horizon(h):
    st.session_state["hz"] = h
    st.session_state["_last_hz"] = h


def _set_help(topic):
    st.session_state["help_topic"] = topic


def _reset_weather(sk, defaults):
    for prefix in defaults:
        st.session_state.pop(prefix + sk, None)


def speak_button(text, lang_code, play_label, stop_label, no_voice, widget_id="tts"):
    """Offline-safe browser Web Speech API playback with Play/Stop and fallback."""
    safe_play = html_lib.escape(play_label)
    safe_stop = html_lib.escape(stop_label)
    html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:2px 0;overflow:hidden;font-family:"Noto Sans Bengali","Nirmala UI","Segoe UI",sans-serif;background:transparent}}
.wrap{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
button{{min-height:44px;padding:8px 18px;border-radius:10px;border:1.5px solid #1F4E8C;background:#1F4E8C;color:#FFFFFF;font-size:16px;font-weight:600;cursor:pointer}}
button.playing{{background:#FFFFFF;color:#1F4E8C}}
button:focus-visible{{outline:3px solid #0B5C8A;outline-offset:2px}}
.msg{{color:#7A5200;font-size:14px;font-weight:600}}
</style></head><body>
<div class="wrap">
  <button id="btn_{widget_id}" type="button" aria-pressed="false">&#9654; {safe_play}</button>
  <span id="msg_{widget_id}" class="msg" role="status" aria-live="polite"></span>
</div>
<script>
const text={json.dumps(text)}, lang={json.dumps(lang_code)},
      playLbl={json.dumps(play_label)}, stopLbl={json.dumps(stop_label)},
      nov={json.dumps(no_voice)};
const btn=document.getElementById("btn_{widget_id}"), msg=document.getElementById("msg_{widget_id}");
let speaking=false;
function findVoice(){{
  const s=window.speechSynthesis;
  if(!s) return null;
  const prefix=lang.slice(0,2).toLowerCase();
  return s.getVoices().find(v=>v.lang.toLowerCase().replace("_","-").startsWith(prefix)) || null;
}}
function setIdle(){{
  speaking=false;
  btn.classList.remove("playing");
  btn.setAttribute("aria-pressed","false");
  btn.innerHTML="&#9654; " + playLbl;
}}
btn.onclick=()=>{{
  const s=window.speechSynthesis;
  if(!s){{ msg.textContent=nov; return; }}
  if(speaking){{ s.cancel(); setIdle(); return; }}
  s.cancel();
  const u=new SpeechSynthesisUtterance(text);
  u.lang=lang;
  const v=findVoice();
  if(v){{ u.voice=v; msg.textContent=""; }}
  else {{ msg.textContent=nov; }}
  u.onend=setIdle;
  u.onerror=setIdle;
  speaking=true;
  btn.classList.add("playing");
  btn.setAttribute("aria-pressed","true");
  btn.innerHTML="&#9632; " + stopLbl;
  s.speak(u);
}};
if(window.speechSynthesis && window.speechSynthesis.onvoiceschanged !== undefined){{
  window.speechSynthesis.onvoiceschanged = ()=>{{ if(findVoice() && !speaking) msg.textContent=""; }};
}}
</script></body></html>"""
    if hasattr(st, "iframe"):
        st.iframe(html_doc, height=58)
    else:
        components.html(html_doc, height=58)


@st.cache_resource
def get_model_artifact():
    if os.path.exists("models/dengue_model.joblib"):
        try:
            art = joblib.load("models/dengue_model.joblib")
            if "models" in art:
                return art
        except Exception:
            pass
    train_and_evaluate(DATA)
    return joblib.load("models/dengue_model.joblib")


@st.cache_data
def get_processed_data():
    return load_and_engineer_features(DATA, cache_path="models/processed_features_v2.pkl")


@st.cache_data
def get_validation_data():
    if not os.path.exists("models/validation_results.csv"):
        train_and_evaluate(DATA)
    d = pd.read_csv("models/validation_results.csv")
    d["date"] = pd.to_datetime(d["date"])
    return d


def render_header():
    with st.container(border=True, key="app-header"):
        hdr_left, hdr_right = st.columns([3.3, 1.3], vertical_alignment="center")
        with hdr_right:
            lang_choice = st.segmented_control(
                "ভাষা / Language",
                ["বাংলা", "English"],
                default="বাংলা",
                key="lang",
                on_change=_keep_lang,
                label_visibility="collapsed",
            )
        if lang_choice not in ("বাংলা", "English"):
            lang_choice = st.session_state.get("_last_lang", "বাংলা")
        else:
            st.session_state["_last_lang"] = lang_choice
        lang = "en" if lang_choice == "English" else "bn"
        with hdr_left:
            auth.role_chip(lang)
        # Full-width block (outside the columns) so the logo is truly centred.
        st.markdown(
            f"<div class='hdr-logo'>{LOGO_SVG}</div>"
            f"<h1 class='hdr-title'>{t('title', lang)}</h1>"
            f"<p class='hdr-sub'>{t('subtitle', lang)}</p>",
            unsafe_allow_html=True,
        )
    return lang


def render_step1(df, lang):
    with st.container(border=True, key="step1-box"):
        st.markdown(f"<div class='step-heading'>{t('step1', lang)}</div>", unsafe_allow_html=True)
        c_city, c_ward, c_hz = st.columns([1.05, 1.25, 1.45], vertical_alignment="bottom")
        cities = sorted(df["city"].unique())
        selected_city = c_city.selectbox(
            t("city", lang),
            cities,
            key="city",
            format_func=lambda c: city_label(c, lang),
        )
        city_wards = sorted(df[df["city"] == selected_city]["ward_id"].unique())
        selected_ward = c_ward.selectbox(
            t("ward", lang),
            city_wards,
            key="ward",
            format_func=lambda w: ward_label(w, lang),
        )
        horizon = c_hz.segmented_control(
            t("horizon", lang),
            list(HORIZONS),
            default=2,
            key="hz",
            on_change=_keep_horizon,
            format_func=lambda h: t("hz_opt", lang, h=h),
        )
        if horizon not in HORIZONS:
            horizon = st.session_state.get("_last_hz", 2)
        else:
            st.session_state["_last_hz"] = horizon

        ward_df = df[df["ward_id"] == selected_ward].dropna(subset=FEATURE_COLS).sort_values("date")
        if ward_df.empty:
            return selected_city, selected_ward, horizon, ward_df, None

        issue_dates = (ward_df["date"] - 2 * WEEK).dt.strftime("%Y-%m-%d").tolist()
        if "issue" in st.session_state and st.session_state["issue"] not in issue_dates:
            del st.session_state["issue"]

        active_issue = st.session_state.get("issue", issue_dates[-1])
        st.markdown(
            f"<div class='weather-note'>{t('weather_note', lang, date=active_issue)}</div>",
            unsafe_allow_html=True,
        )
        with st.expander(t("other_week_exp", lang), expanded=False):
            issue_str = st.selectbox(
                t("issue", lang),
                issue_dates,
                index=len(issue_dates) - 1,
                key="issue",
                format_func=lambda d: fmt_date(d, lang),
            )
    return selected_city, selected_ward, horizon, ward_df, issue_str


def compute_city_rank(artifact, df, selected_city, selected_ward, issue_date, horizon, current_mu):
    city_slice = df[(df["city"] == selected_city) & (df["date"] == issue_date + 2 * WEEK)].dropna(subset=FEATURE_COLS)
    if city_slice.empty:
        return 1, 1
    preds = np.clip(artifact["models"][horizon].predict(city_slice[FEATURE_COLS]), 0, None)
    rank_df = pd.DataFrame({"ward_id": city_slice["ward_id"].values, "pred": preds})
    rank_df.loc[rank_df["ward_id"] == selected_ward, "pred"] = current_mu
    rank_df = rank_df.sort_values("pred", ascending=False).reset_index(drop=True)
    matches = rank_df.index[rank_df["ward_id"] == selected_ward].tolist()
    rank = (matches[0] + 1) if matches else 1
    return rank, len(rank_df)


def build_driver_chart(eff, lang):
    rows = []
    for raw_k, val in eff.items():
        rows.append(
            {
                "Driver": driver_label(raw_k, lang),
                "Effect": float(val),
                "Direction": "up" if val >= 0 else "down",
            }
        )
    eff_df = pd.DataFrame(rows).sort_values("Effect")

    fig = go.Figure()
    for direction, label_key, color, pattern in (
        ("up", "drv_up", "#D55E00", "/"),
        ("down", "drv_down", "#0072B2", "."),
    ):
        sub = eff_df[eff_df["Direction"] == direction]
        fig.add_trace(
            go.Bar(
                x=sub["Effect"],
                y=sub["Driver"],
                orientation="h",
                name=t(label_key, lang),
                marker=dict(color=color, pattern=dict(shape=pattern, solidity=0.65)),
                hovertemplate="%{y}: %{x:+.1f}<extra>" + t(label_key, lang) + "</extra>",
            )
        )
    fig.add_vline(x=0, line_width=1.5, line_color=TOKENS["border"])
    fig.update_layout(
        title=dict(text=t("drv_title", lang), font=dict(size=16, color=TOKENS["text"])),
        barmode="relative",
        height=360,
        margin=dict(l=10, r=16, t=54, b=40),
        xaxis=dict(title=t("drv_x", lang), tickfont=dict(size=13)),
        yaxis=dict(title=None, tickfont=dict(size=13), categoryorder="array", categoryarray=eff_df["Driver"].tolist()),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=13)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(size=13, color=TOKENS["text"]),
    )
    return fig, eff_df


def build_history_chart(recent, lang):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        row_heights=[0.42, 0.58],
    )
    fig.add_trace(
        go.Bar(
            x=recent["date"],
            y=recent["rainfall_sum_2_4w"],
            name=t("hist_rain", lang),
            marker_color="#0072B2",
            hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra>" + t("hist_rain", lang) + "</extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=recent["date"],
            y=recent["dengue_cases"],
            name=t("hist_cases", lang),
            mode="lines",
            line=dict(color="#D55E00", width=2.8),
            fill="tozeroy",
            fillcolor="rgba(213, 94, 0, 0.12)",
            hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra>" + t("hist_cases", lang) + "</extra>",
        ),
        row=2,
        col=1,
    )
    fig.update_yaxes(title_text=t("hist_rain", lang), tickfont=dict(size=12), row=1, col=1)
    fig.update_yaxes(title_text=t("hist_cases", lang), tickfont=dict(size=12), row=2, col=1)
    fig.update_xaxes(tickfont=dict(size=12), row=2, col=1)
    fig.update_layout(
        title=dict(text=t("hist_title", lang), font=dict(size=16, color=TOKENS["text"])),
        height=430,
        margin=dict(l=12, r=16, t=64, b=36),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=13)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(size=13, color=TOKENS["text"]),
    )
    return fig


def render_forecast_tab(
    artifact, df, ward_df, selected_city, selected_ward, issue_date, issue_str, horizon,
    base_row, row, forecasts, defaults, sk, is_scenario, baselines, lang,
):
    pred_cases, ci_low, ci_high, risk_tier = forecasts[horizon]
    tdate = (issue_date + horizon * WEEK).date()
    ts = TIER_STYLES[risk_tier]
    w_name = ward_label(selected_ward, lang)
    c_name = city_label(selected_city, lang)

    if is_scenario:
        st.markdown(f"<div class='scenario-banner'>{t('scenario_badge', lang)}</div>", unsafe_allow_html=True)

    main_col, side_col = st.columns([2.25, 1.0], gap="medium")
    with main_col:
        actual = df[(df["ward_id"] == selected_ward) & (df["date"] == issue_date + horizon * WEEK)]["dengue_cases"]
        if len(actual) and pd.notna(actual.iloc[0]):
            obs_txt = t("actual_past", lang, n=int(actual.iloc[0]))
        else:
            obs_txt = t("future_week", lang)

        rank, total = compute_city_rank(artifact, df, selected_city, selected_ward, issue_date, horizon, pred_cases)
        if pred_cases < 0.5 or rank > max(1, total // 2):
            ctx_txt = t("city_ctx_low", lang, city=c_name, rank=rank, total=total)
        else:
            ctx_txt = t("city_ctx_high", lang, city=c_name, rank=rank, total=total)

        few_html = f"<div class='fc-note'>{t('very_few', lang)}</div>" if pred_cases < 0.5 else ""
        st.markdown(
            f"<div class='fc-primary' style='background:{ts['bg']};color:{ts['fg']};border-color:{ts['border']}'>"
            f"<div class='fc-meta'>{t('fc_for_week', lang, d=tdate, h=horizon)} · {w_name}</div>"
            f"<div class='fc-risk-row'>{ts['icon']}<span>{tier_name(risk_tier, lang)}</span></div>"
            f"<p class='fc-sentence'>{t('main_sentence', lang, ward=w_name, d=tdate, risk=tier_name(risk_tier, lang))}</p>"
            f"<div class='fc-stats'>"
            f"<span class='fc-cases'>{t('expected_cases', lang, n=f'{pred_cases:.1f}')}</span>"
            f"<span class='fc-range'>{t('range_line', lang, a=f'{ci_low:.1f}', b=f'{ci_high:.1f}')}</span>"
            f"</div>"
            f"{few_html}"
            f"<div class='fc-note'>{t('uncertainty', lang)}</div>"
            f"<div class='fc-note'>{obs_txt} · {ctx_txt}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        with st.expander(t("learn_more", lang), expanded=False):
            st.write(t("learn_more_body", lang))

    with side_col:
        st.markdown(f"**{t('other_horizons', lang)}**")
        for h in HORIZONS:
            if h == horizon:
                continue
            mu_s, _, _, tier_s = forecasts[h]
            dt_s = (issue_date + h * WEEK).date()
            badge_s = risk_badge_html(tier_s, tier_name(tier_s, lang), compact=True)
            st.markdown(
                f"<div class='fc-secondary'>"
                f"<div class='fc-sec-date'>{t('fc_for_week', lang, d=dt_s, h=h)}</div>"
                f"{badge_s}"
                f"<div class='fc-sec-num'>{fmt_num(mu_s, lang, 1)} {t('unit_cases_week', lang)}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.button(
                t("select_horizon_btn", lang, h=h),
                key=f"pick_hz_{h}",
                on_click=_select_horizon,
                args=(h,),
                width="stretch",
            )

    # Prominent "What to do now" card directly under main forecast
    resident_bullets = TIER_PLAN[risk_tier]["public"][lang][:3]
    officer_bullets = TIER_PLAN[risk_tier]["officers"][lang][:3]
    bullets_html = "".join(f"<li>{html_lib.escape(b)}</li>" for b in resident_bullets)
    st.markdown(
        f"<div class='action-card' style='background:{ts['bg']};color:{ts['fg']};border-color:{ts['border']}'>"
        f"<h3>{ts['icon']}<span>{t('action_title', lang)} — {tier_name(risk_tier, lang)}</span></h3>"
        f"<ul>{bullets_html}</ul>"
        f"</div>",
        unsafe_allow_html=True,
    )

    speech_text = t(
        "say",
        lang,
        w=w_name,
        d=tdate,
        risk=tier_name(risk_tier, lang),
        n=f"{pred_cases:.1f}",
        acts=" ".join(resident_bullets),
    )
    speak_button(
        speech_text,
        "en-US" if lang == "en" else "bn-BD",
        t("listen", lang),
        t("stop", lang),
        t("novoice", lang),
        widget_id="main",
    )

    with st.expander(t("full_plan", lang), expanded=False):
        p_res, p_off = st.tabs([t("tab_residents", lang), t("tab_officers", lang)])
        with p_res:
            st.markdown("\n".join(f"- {b}" for b in resident_bullets))
        with p_off:
            st.markdown("\n".join(f"- {b}" for b in officer_bullets))
        st.caption(t("plan_note", lang))

    if not auth.is_admin():
        return None
    with st.expander(t("exp_scenario", lang), expanded=False):
        st.caption(t("scen_cap", lang))
        sc1, sc2 = st.columns(2)
        sc1.slider(t("r1", lang), 0.0, 300.0, defaults["r1"], key="r1" + sk)
        sc1.slider(t("r2", lang), 0.0, 300.0, defaults["r2"], key="r2" + sk)
        sc1.slider(t("r3", lang), 0.0, 300.0, defaults["r3"], key="r3" + sk)
        sc2.slider(t("temp", lang), 15.0, 38.0, defaults["tp"], key="tp" + sk)
        sc2.slider(t("hum", lang), 40.0, 100.0, defaults["hu"], key="hu" + sk)
        st.button(
            t("reset_weather", lang),
            key="reset_" + sk,
            on_click=_reset_weather,
            args=(sk, defaults),
        )

    return None


def render_drivers_page(artifact, ward_df, issue_date, eff, lang):
    st.subheader(t("exp_why", lang))
    fig_drv, eff_df = build_driver_chart(eff, lang)
    top_pos = eff_df.sort_values("Effect", ascending=False).iloc[0]
    top_neg = eff_df.sort_values("Effect", ascending=True).iloc[0]
    if top_pos["Effect"] > 0.05:
        drv_takeaway = t("drv_takeaway_up", lang, top=top_pos["Driver"])
    elif top_neg["Effect"] < -0.05:
        drv_takeaway = t("drv_takeaway_down", lang, top=top_neg["Driver"])
    else:
        drv_takeaway = t("drv_takeaway_flat", lang)
    st.markdown(f"<div class='takeaway-line'>{drv_takeaway}</div>", unsafe_allow_html=True)
    st.plotly_chart(fig_drv, width="stretch", config=PLOTLY_CONFIG)

    st.subheader(t("exp_history", lang))
    recent = ward_df[ward_df["date"] <= issue_date + 2 * WEEK].tail(52)
    if not recent.empty:
        max_idx = recent["dengue_cases"].idxmax()
        max_c = int(round(recent.loc[max_idx, "dengue_cases"])) if pd.notna(max_idx) else 0
        max_c_date = recent.loc[max_idx, "date"].strftime("%Y-%m-%d") if pd.notna(max_idx) else str(issue_date.date())
        max_r = f"{recent['rainfall_sum_2_4w'].max():.1f}"
        st.markdown(
            f"<div class='takeaway-line'>{t('hist_takeaway', lang, max_c=max_c, max_c_date=max_c_date, max_r=max_r)}</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(build_history_chart(recent, lang), width="stretch", config=PLOTLY_CONFIG)


def render_all_wards_tab(artifact, df, selected_city, issue_date, horizon, lang):
    st.subheader(t("hm_title", lang, city=city_label(selected_city, lang), h=horizon))
    start = issue_date + 2 * WEEK - 11 * WEEK
    cs = df[
        (df["city"] == selected_city) & (df["date"] >= start) & (df["date"] <= issue_date + 2 * WEEK)
    ].dropna(subset=FEATURE_COLS).copy()
    if cs.empty:
        st.info(t("no_data", lang))
        return

    mdl, disp = artifact["models"][horizon], artifact["dispersion"][horizon]
    cs["Predicted_Cases"] = np.clip(mdl.predict(cs[FEATURE_COLS]), 0, None)
    cs["Target_Week"] = (cs["date"] + (horizon - 2) * WEEK).dt.strftime("%Y-%m-%d")

    latest = cs[cs["date"] == issue_date + 2 * WEEK].copy()
    latest["CI_Low"], latest["CI_High"] = predict_interval(latest["Predicted_Cases"], disp)
    latest["Risk_Tier"] = latest["Predicted_Cases"].apply(classify_risk_tier)
    latest = latest.sort_values("Predicted_Cases", ascending=False).reset_index(drop=True)
    latest["Priority_Rank"] = np.arange(1, len(latest) + 1)

    top_ward_name = ward_label(latest.iloc[0]["ward_id"], lang)
    st.markdown(
        f"<div class='takeaway-line'>{t('hm_takeaway', lang, top_ward=top_ward_name)}</div>",
        unsafe_allow_html=True,
    )

    piv = cs.pivot(index="ward_id", columns="Target_Week", values="Predicted_Cases")
    piv = piv.loc[piv.iloc[:, -1].sort_values(ascending=False).index]
    friendly_y = [ward_label(w, lang) for w in piv.index]
    piv_display = piv.copy()
    piv_display.index = friendly_y

    colorscale = [[0.0, "#F3F6F4"], [0.25, "#F6D55C"], [0.6, "#D95F02"], [1.0, "#7A0C1E"]]
    fig_hm = px.imshow(
        piv_display,
        aspect="auto",
        color_continuous_scale=colorscale,
        labels=dict(x=t("hm_x", lang), y=t("hm_y", lang), color=t("hm_c", lang)),
    )
    fig_hm.update_traces(
        hovertemplate="%{y}<br>%{x}: %{z:.1f} " + t("hm_c", lang) + "<extra></extra>"
    )
    fig_hm.update_layout(
        height=max(360, 26 * len(piv_display.index)),
        margin=dict(l=12, r=12, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13, color=TOKENS["text"]),
    )
    fig_hm.update_xaxes(tickfont=dict(size=12))
    fig_hm.update_yaxes(tickfont=dict(size=12))
    st.plotly_chart(fig_hm, width="stretch", config=PLOTLY_CONFIG)

    st.markdown(f"**{t('pri_title', lang, d=(issue_date + horizon * WEEK).date())}**")
    sort_options = ["risk", "ward", "rain", "wl"]
    sort_labels = {
        "risk": t("sort_risk", lang),
        "ward": t("sort_ward", lang),
        "rain": t("sort_rain", lang),
        "wl": t("sort_wl", lang),
    }
    sort_by = st.selectbox(
        t("sort_label", lang),
        sort_options,
        key="ward_sort",
        format_func=lambda k: sort_labels[k],
    )
    if sort_by == "ward":
        latest_view = latest.sort_values("ward_id", ascending=True)
    elif sort_by == "rain":
        latest_view = latest.sort_values("rainfall_sum_2_4w", ascending=False)
    elif sort_by == "wl":
        latest_view = latest.sort_values("water_logging_risk_index", ascending=False)
    else:
        latest_view = latest

    headers = [t(k, lang) for k in ("c_ward", "c_risk", "c_pred", "c_range", "c_rain", "c_wl", "c_pop")]
    th_html = "".join(f"<th>{html_lib.escape(h_txt)}</th>" for h_txt in headers)
    rows_html = []
    for _, r in latest_view.iterrows():
        rank = int(r["Priority_Rank"])
        is_top5 = rank <= 5
        row_cls = " class='top5-row'" if is_top5 else ""
        rank_badge = f"<span class='rank-tag'>{t('top5_tag', lang, n=rank)}</span>" if is_top5 else ""
        w_txt = html_lib.escape(ward_label(r["ward_id"], lang))
        badge = risk_badge_html(r["Risk_Tier"], tier_name(r["Risk_Tier"], lang), compact=True)
        pred_txt = fmt_num(r["Predicted_Cases"], lang, 1)
        rng_txt = f"{fmt_num(r['CI_Low'], lang, 1)} – {fmt_num(r['CI_High'], lang, 1)}"
        rain_txt = fmt_num(r["rainfall_sum_2_4w"], lang, 1)
        wl_txt = fmt_num(r["water_logging_risk_index"], lang, 2)
        pop_txt = fmt_num(round(r["population_density_sqkm"]), lang, 0)
        rows_html.append(
            f"<tr{row_cls}>"
            f"<td>{rank_badge}<strong>{w_txt}</strong></td>"
            f"<td>{badge}</td>"
            f"<td>{pred_txt}</td>"
            f"<td>{rng_txt}</td>"
            f"<td>{rain_txt}</td>"
            f"<td>{wl_txt}</td>"
            f"<td>{pop_txt}</td>"
            f"</tr>"
        )
    st.markdown(
        f"<div class='table-scroll'><table class='pri-table'>"
        f"<thead><tr>{th_html}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        f"</table></div>",
        unsafe_allow_html=True,
    )
    st.caption(t("hm_cap", lang))


def render_accuracy_tab(artifact, df_val, selected_ward, horizon, lang):
    st.subheader(t("acc_title", lang))
    vh = st.selectbox(
        t("acc_sel", lang),
        list(HORIZONS),
        index=list(HORIZONS).index(horizon),
        key="vh",
        format_func=lambda h: t("hz_opt", lang, h=h),
    )

    tr = artifact["tier_report"][vh]
    test_mae_all = artifact["test_mae"][vh]

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        f"<div class='trust-card'><div class='trust-lbl'>{t('acc_card_err', lang)}</div>"
        f"<div class='trust-val'>{t('acc_card_err_val', lang, x=f'{test_mae_all:.2f}')}</div></div>",
        unsafe_allow_html=True,
    )
    c2.markdown(
        f"<div class='trust-card'><div class='trust-lbl'>{t('acc_card_caught', lang)}</div>"
        f"<div class='trust-val'>{fmt_num(tr['alert_recall'], lang, 1)}%</div></div>",
        unsafe_allow_html=True,
    )
    c3.markdown(
        f"<div class='trust-card'><div class='trust-lbl'>{t('acc_card_prec', lang)}</div>"
        f"<div class='trust-val'>{fmt_num(tr['alert_precision'], lang, 1)}%</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"<div class='takeaway-line'>{t('acc_caveat', lang)}</div>", unsafe_allow_html=True)
    st.caption(
        t(
            "acc_cov",
            lang,
            tr=artifact["train_range"][vh].replace(" to ", t("to", lang)),
            te=artifact["test_range"][vh].replace(" to ", t("to", lang)),
            c1=artifact["ci_coverage"][vh][1],
            c0=artifact["ci_coverage"][vh][0],
        )
    )

    with st.expander(t("acc_expert", lang), expanded=False):
        st.markdown(f"**{t('acc_bm_title', lang)}**")
        bm = pd.DataFrame(artifact["benchmarks"][vh]).T.reset_index()
        bm["index"] = bm["index"].map(lambda n: t("m_ridge", lang) if n.startswith("Ridge") else t("m_hgb", lang))
        bm = bm.rename(
            columns={
                "index": t("model", lang),
                "MAE": t("col_mae", lang),
                "RMSE": t("col_rmse", lang),
                "R2": t("col_r2", lang),
                "Tier_Accuracy_Pct": t("col_acc", lang),
            }
        )
        if lang == "bn":
            for col in bm.columns[1:]:
                bm[col] = bm[col].map(lambda v: to_bn_digits(f"{v:.4g}" if v < 10 else f"{v:.2f}"))
        st.dataframe(bm, width="stretch", hide_index=True)

        vw = df_val[(df_val["ward_id"] == selected_ward) & (df_val["horizon_weeks"] == vh)].sort_values("date")
        if not vw.empty:
            err = vw["dengue_cases"] - vw["predicted_cases"]
            gap = abs(artifact["test_mae"][vh] - artifact["train_mae"][vh])
            m1, m2, m3 = st.columns(3)
            m1.metric(
                t("ward_mae", lang, w=ward_label(selected_ward, lang)),
                f"{fmt_num(np.mean(np.abs(err)), lang, 2)} {t('unit_cases_week', lang)}",
            )
            m2.metric(
                t("ward_rmse", lang, w=ward_label(selected_ward, lang)),
                f"{fmt_num(np.sqrt(np.mean(err ** 2)), lang, 2)} {t('unit_cases_week', lang)}",
            )
            m3.metric(t("gap_lbl", lang), fmt_num(gap, lang, 3))
            m3.caption(t("lowof", lang) if gap < 0.15 else t("chkof", lang))

        names = [tier_name(x, lang, short=True) for x in tr["labels"]]
        cm_col, rec_col = st.columns([3, 2])
        with cm_col:
            fig_cm = px.imshow(
                tr["cm"],
                x=names,
                y=names,
                text_auto=True,
                color_continuous_scale="Greens",
                labels=dict(x=t("cm_x", lang), y=t("cm_y", lang), color=t("cm_c", lang)),
                title=t("cm_t", lang),
            )
            fig_cm.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=13, color=TOKENS["text"]),
                margin=dict(l=10, r=10, t=44, b=30),
            )
            st.plotly_chart(fig_cm, width="stretch", config=PLOTLY_CONFIG)
        with rec_col:
            st.markdown(f"**{t('rec_h', lang)}**")
            rec_df = pd.DataFrame(
                {
                    t("c_risk", lang): names,
                    t("rec_a", lang): [fmt_num(tr["recall"][x], lang, 1) for x in TIERS],
                    t("rec_b", lang): [fmt_num(tr["actual_share"][x], lang, 1) for x in TIERS],
                }
            )
            st.dataframe(rec_df, width="stretch", hide_index=True)

        if not vw.empty:
            fig_v = go.Figure()
            fig_v.add_trace(go.Scatter(x=vw["date"], y=vw["ci_high"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig_v.add_trace(
                go.Scatter(
                    x=vw["date"],
                    y=vw["ci_low"],
                    mode="lines",
                    line=dict(width=0),
                    fill="tonexty",
                    fillcolor="rgba(213, 94, 0, 0.16)",
                    name=t("av_int", lang),
                    hoverinfo="skip",
                )
            )
            fig_v.add_trace(
                go.Scatter(
                    x=vw["date"],
                    y=vw["dengue_cases"],
                    name=t("av_a", lang),
                    line=dict(color="#0072B2", width=2.2),
                    hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra>" + t("av_a", lang) + "</extra>",
                )
            )
            fig_v.add_trace(
                go.Scatter(
                    x=vw["date"],
                    y=vw["predicted_cases"],
                    name=t("av_p", lang),
                    line=dict(color="#D55E00", width=2.2, dash="dash"),
                    hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra>" + t("av_p", lang) + "</extra>",
                )
            )
            fig_v.update_layout(
                title=dict(
                    text=t("av_t", lang, h=vh, w=ward_label(selected_ward, lang)),
                    font=dict(size=15, color=TOKENS["text"]),
                ),
                height=420,
                xaxis_title=t("av_x", lang),
                yaxis_title=t("av_y", lang),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=13)),
                margin=dict(l=12, r=12, t=64, b=36),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#FFFFFF",
                font=dict(size=13, color=TOKENS["text"]),
            )
            st.plotly_chart(fig_v, width="stretch", config=PLOTLY_CONFIG)


def render_help_guide(selected_ward, issue_date, issue_str, horizon, forecasts, eff, lang):
    st.markdown(f"### {t('help_title', lang)}")
    b1, b2, b3 = st.columns(3)
    b1.button(t("help_q1", lang), key="help_btn_1", on_click=_set_help, args=("q1",), width="stretch")
    b2.button(t("help_q2", lang), key="help_btn_2", on_click=_set_help, args=("q2",), width="stretch")
    b3.button(t("help_q3", lang), key="help_btn_3", on_click=_set_help, args=("q3",), width="stretch")

    topic = st.session_state.get("help_topic")
    if not topic or forecasts is None:
        return

    pred_cases, ci_low, ci_high, risk_tier = forecasts[horizon]
    tdate = (issue_date + horizon * WEEK).date()
    w_name = ward_label(selected_ward, lang)
    r_name = tier_name(risk_tier, lang)
    bullets = TIER_PLAN[risk_tier]["public"][lang]

    if topic == "q1":
        ans = t("help_a1", lang, ward=w_name, d=tdate, risk=r_name, n=f"{pred_cases:.1f}", a=f"{ci_low:.1f}", b=f"{ci_high:.1f}")
    elif topic == "q2":
        ans = t("help_a2", lang, risk=r_name, p1=bullets[0], p2=bullets[1], p3=bullets[2])
    else:
        top_raw = max(eff.items(), key=lambda kv: abs(kv[1]))[0]
        ans = t("help_a3", lang, issue_d=issue_str, top_drv=driver_label(top_raw, lang))

    ans_plain = ans.replace("**", "")
    st.markdown(f"<div class='help-answer'>{ans}</div>", unsafe_allow_html=True)
    speak_button(
        ans_plain,
        "en-US" if lang == "en" else "bn-BD",
        t("listen", lang),
        t("stop", lang),
        t("novoice", lang),
        widget_id="help",
    )


def render_footer(lang, latest_date):
    st.markdown(
        f"<div class='app-footer'>"
        f"<p><strong>{t('disclaimer', lang)}</strong></p>"
        f"<p>{t('footer_meta', lang, date=fmt_date(latest_date, lang))}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )


def main():
    lang_initial = _active_lang()
    st.markdown(build_css(lang_initial), unsafe_allow_html=True)
    lang = render_header()
    if lang != lang_initial:
        st.markdown(build_css(lang), unsafe_allow_html=True)

    try:
        with st.spinner(t("loading", lang)):
            artifact = get_model_artifact()
            df = get_processed_data()
            df_val = get_validation_data()
            baselines = df[FEATURE_COLS].median()
    except Exception:
        st.error(t("error", lang))
        return

    selected_city, selected_ward, horizon, ward_df, issue_str = render_step1(df, lang)
    latest_date = str(df["date"].max().date()) if not df.empty else "2025-12-29"

    if ward_df.empty or issue_str is None:
        st.warning(t("no_data", lang))
        render_footer(lang, latest_date)
        return

    issue_date = pd.Timestamp(issue_str)
    base_matches = ward_df[ward_df["date"] == issue_date + 2 * WEEK]
    if base_matches.empty:
        st.warning(t("no_data", lang))
        render_footer(lang, latest_date)
        return
    base_row = base_matches.iloc[0].copy()

    sk = f"{selected_ward}_{issue_str}"
    defaults = {
        "r1": float(round(base_row["rainfall_lag_2w"], 1)),
        "r2": float(round(base_row["rainfall_lag_3w"], 1)),
        "r3": float(round(base_row["rainfall_lag_4w"], 1)),
        "tp": float(round(base_row["temp_mean_2_4w"], 1)),
        "hu": float(round(base_row["humidity_mean_2_4w"], 1)),
    }
    sim_r1 = st.session_state.get("r1" + sk, defaults["r1"])
    sim_r2 = st.session_state.get("r2" + sk, defaults["r2"])
    sim_r3 = st.session_state.get("r3" + sk, defaults["r3"])
    sim_tp = st.session_state.get("tp" + sk, defaults["tp"])
    sim_hu = st.session_state.get("hu" + sk, defaults["hu"])
    is_scenario = any(
        abs(val - defaults[k]) > 1e-6
        for k, val in (("r1", sim_r1), ("r2", sim_r2), ("r3", sim_r3), ("tp", sim_tp), ("hu", sim_hu))
    )

    row = {c: float(base_row[c]) for c in FEATURE_COLS}
    row.update(
        rainfall_lag_2w=sim_r1,
        rainfall_lag_3w=sim_r2,
        rainfall_lag_4w=sim_r3,
        temp_lag_2w=sim_tp,
        temp_lag_3w=sim_tp,
        temp_lag_4w=sim_tp,
        humidity_lag_2w=sim_hu,
        humidity_lag_3w=sim_hu,
        humidity_lag_4w=sim_hu,
    )
    row = derive_features(row)
    X_input = pd.DataFrame([row])[FEATURE_COLS].astype("float32")

    forecasts = {}
    for h in HORIZONS:
        mu = float(np.clip(artifact["models"][h].predict(X_input)[0], 0, None))
        lo, hi = (float(v[0]) for v in predict_interval([mu], artifact["dispersion"][h]))
        forecasts[h] = (mu, lo, hi, classify_risk_tier(mu))

    eff = local_driver_effects(artifact["models"][horizon], row, baselines)

    def page_forecast():
        render_forecast_tab(
            artifact, df, ward_df, selected_city, selected_ward, issue_date, issue_str,
            horizon, base_row, row, forecasts, defaults, sk, is_scenario, baselines, lang,
        )

    def page_drivers():
        render_drivers_page(artifact, ward_df, issue_date, eff, lang)

    def page_wards():
        render_all_wards_tab(artifact, df, selected_city, issue_date, horizon, lang)

    def page_ops():
        render_operations_page(artifact, df, selected_city, issue_date, horizon, lang)

    def page_login():
        auth.login_page(lang)

    def page_resources():
        render_resources_page(artifact, df, issue_date, horizon, lang)

    def page_beds():
        render_beds_page(artifact, df, issue_date, horizon, lang)

    def page_whatif():
        render_whatif_page(artifact, df, issue_date, horizon, lang)

    def page_dispatch():
        render_dispatch_page(artifact, df, issue_date, horizon, lang)

    def page_accuracy():
        render_accuracy_tab(artifact, df_val, selected_ward, horizon, lang)

    pages = [
        st.Page(page_forecast, title=t("tab_forecast", lang), icon="📈", url_path="forecast", default=True),
        st.Page(page_drivers,  title=t("exp_why", lang),      icon="🌧️", url_path="drivers"),
        st.Page(page_wards,    title=t("tab_wards", lang),    icon="🗺️", url_path="wards"),
        st.Page(page_resources, title=CMD_TEXT["t_res"][lang],  icon="📦", url_path="resources"),
        st.Page(page_beds,      title=CMD_TEXT["t_beds"][lang], icon="🛏️", url_path="beds"),
        st.Page(page_whatif,    title=CMD_TEXT["t_sim"][lang],  icon="🧪", url_path="whatif"),
        st.Page(page_dispatch,  title=CMD_TEXT["t_disp"][lang], icon="📨", url_path="dispatch"),
        st.Page(page_ops,      title=OPS_TEXT["page_title"][lang], icon="🚨", url_path="actions"),
        st.Page(page_accuracy, title=t("tab_accuracy", lang), icon="📊", url_path="accuracy"),
    ]
    if not auth.is_admin():
        pages.append(st.Page(page_login, title=auth.T["title"][lang], icon="🔐", url_path="admin"))
    st.navigation(pages, position="top").run()

    render_help_guide(selected_ward, issue_date, issue_str, horizon, forecasts, eff, lang)
    render_footer(lang, latest_date)


if __name__ == "__main__":
    main()
