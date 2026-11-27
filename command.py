"""Phase 2 command-centre pages (Streamlit). Logic lives in resource_engine.py.

Pages: Resources (allocation + scarcity), Beds (overflow routing), What-if (vector control
simulator), Dispatch (SMS/WhatsApp notices, printable briefs, /exports).
All of it runs locally: the only 'model' call is the saved Phase 1 model.
"""
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import auth
import resource_engine as eng
import settings_store as store
from i18n import city_label, fmt_num, tier_name, to_bn_digits, ward_label
from operations import sms_segments, wa_link

WEEK = pd.Timedelta(weeks=1)
DEFAULT_STOCK, DEFAULT_CREWS, DEFAULT_CAP_PCT = 70, 12, int(eng.BED_CAPACITY_FACTOR * 100)
EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")

C = {
    "t_res": {"bn": "সম্পদ বরাদ্দ", "en": "Resources"},
    "t_beds": {"bn": "বেড ও ওভারফ্লো", "en": "Beds & overflow"},
    "t_sim": {"bn": "কী হলে কী (সিমুলেটর)", "en": "What-if simulator"},
    "t_disp": {"bn": "ডিসপ্যাচ ও ব্রিফ", "en": "Dispatch & briefs"},
    "offline": {
        "bn": "পুরোপুরি অফলাইন: পূর্বাভাস, বরাদ্দ, রাউটিং, সিমুলেশন ও বার্তা সবই এই কম্পিউটারে হয়। কোনো ইন্টারনেট বা এআই API লাগে না।",
        "en": "Fully offline: forecast, allocation, routing, simulation and notices all run on this machine. No internet or AI API needed.",
    },
    "no_data": {"bn": "এই সপ্তাহের জন্য ডেটা নেই।", "en": "No data for this week."},
    "based": {"bn": "ভিত্তি: {h} সপ্তাহ পরের পূর্বাভাস ({wk})।", "en": "Based on the {h}-week forecast ({wk})."},
    # resources
    "stock": {"bn": "আঞ্চলিক স্টক (চাহিদার %)", "en": "Available regional stock (% of demand)"},
    "crews": {"bn": "মোট স্প্রে দল", "en": "Total spraying crews"},
    "m_sal": {"bn": "স্যালাইন (বরাদ্দ / প্রয়োজন)", "en": "Saline (allocated / required)"},
    "m_kit": {"bn": "কিট (বরাদ্দ / প্রয়োজন)", "en": "Kits (allocated / required)"},
    "m_crew": {"bn": "দল (নিযুক্ত / প্রয়োজন)", "en": "Crews (assigned / needed)"},
    "m_def": {"bn": "ঘাটতিযুক্ত ওয়ার্ড", "en": "Wards in deficit"},
    "ok_all": {"bn": "সব ওয়ার্ডের চাহিদা ১০০% মেটানো গেছে।", "en": "Demand is fully met in every ward."},
    "deficit": {
        "bn": "গুরুতর সরবরাহ ঘাটতি: {n}টি ওয়ার্ডে চাহিদা পুরো মেটেনি, তার মধ্যে {k}টিতে অর্ধেকের কম। স্টক বাড়ান বা অগ্রাধিকার ওয়ার্ডে আগে পাঠান।",
        "en": "Critical supply deficit: {n} ward(s) cannot be fully supplied, {k} of them below 50%. Raise stock or ship to priority wards first.",
    },
    "how": {
        "bn": "অগ্রাধিকার = ঝুঁকির ওজন × পূর্বাভাসিত রোগী × (জনঘনত্ব ÷ গড় ঘনত্ব)। স্টক এই ক্রমে ভরা হয়, তাই উচ্চ ঝুঁকি ও ঘন ওয়ার্ড আগে পায়।",
        "en": "Priority = tier weight x predicted cases x (density / mean density). Stock is filled in that order, so high-risk, dense wards are served first.",
    },
    "c_rank": {"bn": "ক্রম", "en": "Rank"}, "c_ward": {"bn": "ওয়ার্ড", "en": "Ward"},
    "c_city": {"bn": "শহর", "en": "City"}, "c_risk": {"bn": "ঝুঁকি", "en": "Risk"},
    "c_cases": {"bn": "রোগী/সপ্তাহ", "en": "Cases/wk"}, "c_dens": {"bn": "ঘনত্ব/বর্গকিমি", "en": "Density/km²"},
    "c_sal": {"bn": "স্যালাইন বরাদ্দ/প্রয়োজন", "en": "Saline alloc/req"},
    "c_kit": {"bn": "কিট বরাদ্দ/প্রয়োজন", "en": "Kits alloc/req"},
    "c_bed": {"bn": "বেড প্রয়োজন", "en": "Beds req"}, "c_crew": {"bn": "দল", "en": "Crews"},
    "c_stat": {"bn": "অবস্থা", "en": "Status"},
    "s_ok": {"bn": "ঠিক আছে", "en": "OK"}, "s_def": {"bn": "⚠ ঘাটতি", "en": "⚠ Deficit"},
    "s_crit": {"bn": "⛔ গুরুতর ঘাটতি", "en": "⛔ Critical deficit"},
    # beds
    "cap_pct": {"bn": "বেড ধারণক্ষমতা ধরা হয়েছে (ওয়ার্ডের ঐতিহাসিক সর্বোচ্চ চাহিদার %)", "en": "Assumed bed capacity (% of each ward's historical peak demand)"},
    "cap_note": {
        "bn": "ডেটাসেটে বেডের ধারণক্ষমতা নেই, তাই এটি অনুমান। প্রকৃত ক্ষমতা পেলে বদলে দিন।",
        "en": "The dataset has no bed capacity, so this is an assumption. Replace it with real capacity data.",
    },
    "city_tbl": {"bn": "শহরভিত্তিক বেড পরিস্থিতি", "en": "City-wide bed situation"},
    "c_req": {"bn": "চাহিদা", "en": "Required"}, "c_cap": {"bn": "ক্ষমতা", "en": "Capacity"},
    "c_ub": {"bn": "ব্যবহার (আগে)", "en": "Utilisation before"}, "c_ua": {"bn": "ব্যবহার (পরে)", "en": "Utilisation after"},
    "c_ov": {"bn": "ওভারফ্লো", "en": "Overflow"}, "c_rt": {"bn": "স্থানান্তরিত", "en": "Routed"},
    "c_un": {"bn": "বেডহীন রোগী", "en": "Unplaced patients"}, "c_hr": {"bn": "বাকি জায়গা", "en": "Headroom left"},
    "c_sent": {"bn": "পাঠানো", "en": "Sent out"}, "c_recv": {"bn": "গ্রহণ", "en": "Received"},
    "c_load": {"bn": "চূড়ান্ত লোড", "en": "Final load"}, "c_net": {"bn": "নিট ঘাটতি", "en": "Net deficit"},
    "moves": {"bn": "রোগী স্থানান্তরের তালিকা", "en": "Patient transfers"},
    "c_from": {"bn": "থেকে", "en": "From"}, "c_to": {"bn": "যেখানে", "en": "To"}, "c_pat": {"bn": "রোগী", "en": "Patients"},
    "no_moves": {"bn": "এই শহরে স্থানান্তরের দরকার নেই।", "en": "No transfers needed in this city."},
    "city_short": {
        "bn": "{c}: {n} জন রোগীর জন্য বেড নেই। পুরো শহরের সব ওয়ার্ড ভরে গেছে।",
        "en": "{c}: {n} patient(s) have no bed. Every ward in the city is full.",
    },
    "beds_ok": {"bn": "কোনো শহরে বেডের সংকট নেই।", "en": "No city has a bed shortage."},
    "route_how": {
        "bn": "ওভারফ্লো শুধু একই শহরের ভেতরে যায়, সবচেয়ে বেশি খালি বেডওয়ালা ওয়ার্ডে আগে।",
        "en": "Overflow moves only inside the same city, to the ward with the most free beds first.",
    },
    # sim
    "sim_crews": {"bn": "মোতায়েন করার দল", "en": "Crews to deploy"},
    "sim_pick": {"bn": "ওয়ার্ড বাছুন (খালি রাখলে মডেল সেরা ওয়ার্ড বাছবে)", "en": "Choose wards (leave empty to let the model pick the best)"},
    "sim_total": {"bn": "২-৪ সপ্তাহে প্রতিরোধ করা রোগী", "en": "Cases prevented (weeks +2 to +4)"},
    "sim_beds": {"bn": "বেড কমবে (সর্বোচ্চ সপ্তাহে)", "en": "Beds saved (peak week)"},
    "sim_sal": {"bn": "স্যালাইন বাঁচবে", "en": "Saline saved"},
    "sim_how": {
        "bn": "প্রতিটি দল ওয়ার্ডের মশার প্রজনন-স্থানের ২৫% কমায় (ক্রমহ্রাসমান হারে, সর্বোচ্চ ৭৫%)। কমানো সূচক মডেলে দিয়ে ২, ৩ ও ৪ সপ্তাহের পূর্বাভাস আবার হিসাব করা হয়। ধরে নেওয়া হারটি বাস্তব মাঠ-তথ্য দিয়ে যাচাই করা নয়।",
        "en": "Each crew removes 25% of the ward's breeding habitat (diminishing returns, max 75%). The reduced index is fed back into the model and the +2/+3/+4-week forecasts are recomputed. The 25% rate is an assumption, not field-validated.",
    },
    "sim_flat": {
        "bn": "সতর্কতা: মডেল হস্তক্ষেপে সাড়া দেয়নি (কোনো রোগী কমেনি)। `src/preprocess.derive_features` জলাবদ্ধতা সূচক থেকে বৈশিষ্ট্য হিসাব করে কিনা দেখুন।",
        "en": "Warning: the model did not respond to the intervention (no cases prevented). Check that `src/preprocess.derive_features` rebuilds its features from the water-logging index.",
    },
    "sim_factors": {
        "bn": "যা বদলায়: শুধু নির্বাচিত ওয়ার্ডের জলাবদ্ধতা সূচক (মশার প্রজনন-স্থানের মাপ)। যা স্থির থাকে: বৃষ্টি, তাপমাত্রা, আর্দ্রতা, জনঘনত্ব, স্যানিটেশন। প্রতিটি ওয়ার্ডে সর্বোচ্চ ৪টি দল।",
        "en": "What changes: only the selected wards' water-logging index (the breeding-habitat measure). What stays fixed: rainfall, temperature, humidity, density, sanitation. At most 4 crews per ward.",
    },
    "sim_low": {
        "bn": "এই সপ্তাহে পুরো অঞ্চলে পূর্বাভাস খুবই কম (মোট {t} রোগী/সপ্তাহ ধরে ২-৪ সপ্তাহের যোগফল), তাই দল বাড়ালেও প্রতিরোধ করা রোগী কয়েক শতাংশ এককের বেশি বদলায় না। ডেমোর জন্য বর্ষার সপ্তাহ বাছুন।",
        "en": "Forecast cases are very low for this week (regional total {t} over weeks +2 to +4), so extra crews change prevented cases only by hundredths. For a demo, pick a rainy-season week.",
    },
    "sim_pct": {"bn": "মোতায়েন করা ওয়ার্ডগুলোর পূর্বাভাসের {p}% কমে", "en": "{p}% of the deployed wards' forecast"},
    "curve_title": {"bn": "দল বাড়ালে প্রতিরোধ করা রোগী কেমন বদলায়", "en": "How prevented cases change with more crews"},
    "c_ncrews": {"bn": "মোট দল", "en": "Total crews"},
    "roi_title": {"bn": "হস্তক্ষেপের ROI ক্রম (১টি দলে প্রতিরোধ করা রোগী)", "en": "Intervention ROI ranking (cases prevented per crew)"},
    "plan_title": {"bn": "মোতায়েন পরিকল্পনা ও ফল", "en": "Deployment plan and outcome"},
    "c_roi": {"bn": "ROI (রোগী/দল)", "en": "ROI (cases/crew)"}, "c_prev": {"bn": "প্রতিরোধ", "en": "Prevented"},
    "c_base": {"bn": "আগে", "en": "Baseline"}, "c_after": {"bn": "পরে", "en": "After"},
    "wk": {"bn": "{h} সপ্তাহ", "en": "+{h} wk"},
    "c_bsv": {"bn": "বেড কমে", "en": "Beds saved"}, "c_ssv": {"bn": "স্যালাইন বাঁচে", "en": "Saline saved"},
    "chart_title": {"bn": "মোতায়েনের আগে ও পরে সাপ্তাহিক রোগী (নির্বাচিত ওয়ার্ডগুলোর যোগফল)", "en": "Weekly cases before and after deployment (sum of deployed wards)"},
    # dispatch
    "msg_lang": {"bn": "বার্তার ভাষা", "en": "Message language"},
    "pick_city": {"bn": "শহর", "en": "City"}, "pick_ward": {"bn": "ওয়ার্ড", "en": "Ward"},
    "sms": {"bn": "এসএমএস", "en": "SMS"}, "wa": {"bn": "হোয়াটসঅ্যাপ", "en": "WhatsApp"},
    "chars": {"bn": "{c} অক্ষর, {s}টি এসএমএস", "en": "{c} characters, {s} SMS"},
    "open_wa": {"bn": "হোয়াটসঅ্যাপে খুলুন", "en": "Open in WhatsApp"},
    "brief_title": {"bn": "কমিশনারের ছাপার উপযোগী ব্রিফ", "en": "Printable commissioner brief"},
    "dl_brief": {"bn": "ব্রিফ ডাউনলোড (HTML)", "en": "Download brief (HTML)"},
    "save_ex": {"bn": "নমুনা এক্সপোর্ট /exports ফোল্ডারে সেভ করুন", "en": "Save sample exports to /exports"},
    "saved": {"bn": "{n}টি ফাইল সেভ হয়েছে: {p}", "en": "Saved {n} files to {p}"},
    "viewer": {
        "bn": "আপনি শুধু দেখতে পারবেন। এই সেটিং অ্যাডমিন ঠিক করেন: {what}। (সর্বশেষ বদল: {t})",
        "en": "View-only. These settings are controlled by the admin: {what}. (Last changed: {t})",
    },
    "settings_from": {"bn": "সেটিং: স্টক {s}%, দল {c} (সম্পদ বরাদ্দ পেজ থেকে)।", "en": "Settings: stock {s}%, crews {c} (from the Resources page)."},
}


def c(key, lang, **kw):
    text = C[key][lang]
    return text.format(**kw) if kw else text


def _n(v, lang, d=0):
    return fmt_num(v, lang, d)


# ----------------------------------------------------------------------------
# Shared context (cached: one model batch per city-week, not per click)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _context(_artifact, _df, issue_key, horizon):
    from src.preprocess import FEATURE_COLS, classify_risk_tier

    issue = pd.Timestamp(issue_key)
    cs = _df[_df["date"] == issue + 2 * WEEK].dropna(subset=FEATURE_COLS)
    if cs.empty:
        return None
    mu = np.clip(_artifact["models"][horizon].predict(cs[FEATURE_COLS]), 0, None)
    frame = pd.DataFrame({
        "ward_id": cs["ward_id"].values, "city": cs["city"].values, "predicted": mu,
        "tier": [classify_risk_tier(v) for v in mu], "density": cs["population_density_sqkm"].values,
    })
    rows = {}
    for _, r in cs.iterrows():
        d = {col: float(r[col]) for col in FEATURE_COLS}
        d.setdefault("water_logging_risk_index", float(r["water_logging_risk_index"]))
        rows[r["ward_id"]] = d
    return {"frame": frame, "rows": rows}


@st.cache_data(show_spinner=False)
def _capacity(_df, factor):
    return eng.bed_capacity_map(_df, factor=factor)


@st.cache_data(show_spinner=False)
def _cached_gain_table(_artifact, _rows, issue_key, horizon_key):
    from src.preprocess import FEATURE_COLS, derive_features

    models = _artifact["models"]

    def predict_batch(ids, reductions):
        built = []
        for w, red in zip(ids, reductions):
            row = dict(_rows[w])
            row["water_logging_risk_index"] = row["water_logging_risk_index"] * (1.0 - red)
            built.append(derive_features(row))
        X = pd.DataFrame(built)[FEATURE_COLS].astype("float32")
        return {h: np.clip(models[h].predict(X), 0, None) for h in eng.HORIZONS}

    return eng._gain_table(list(_rows.keys()), predict_batch)


def _show_html(html, height):
    """st.iframe on new Streamlit (components.html is being removed), fallback otherwise."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:
        components.html(html, height=height, scrolling=True)


def _settings():
    cfg = store.load()
    return int(cfg["stock"]), int(cfg["crews"]), int(cfg["cap_pct"])


def _viewer_note(lang, what):
    cfg = store.load()
    st.info(c("viewer", lang, what=what, t=cfg["updated_at"] or "-"))


def _header(lang, title, horizon, issue_date):
    st.subheader(title)
    wk = (issue_date + horizon * WEEK).date()
    st.caption(c("based", lang, h=_n(horizon, lang), wk=to_bn_digits(str(wk)) if lang == "bn" else str(wk)))
    st.caption(c("offline", lang))


def _tier_txt(tier, lang):
    return tier_name(tier, lang, short=True)


# ----------------------------------------------------------------------------
# Page 1: Resources
# ----------------------------------------------------------------------------
def render_resources_page(artifact, df, issue_date, horizon, lang):
    _header(lang, c("t_res", lang), horizon, issue_date)
    ctx = _context(artifact, df, str(issue_date.date()), horizon)
    if ctx is None:
        st.info(c("no_data", lang))
        return
    cfg = store.load()
    if auth.is_admin():
        with st.container(border=True):
            a, b = st.columns(2)
            stock = a.slider(c("stock", lang), 30, 100, int(cfg["stock"]), 5, key="cmd_stock_w")
            crews = int(b.number_input(c("crews", lang), 0, 500, int(cfg["crews"]), key="cmd_crews_w"))
        if (stock, crews) != (int(cfg["stock"]), int(cfg["crews"])):
            store.save({"stock": stock, "crews": crews})
    else:
        stock, crews = int(cfg["stock"]), int(cfg["crews"])
        _viewer_note(lang, f"{c('stock', lang)}: {_n(stock, lang)}%, {c('crews', lang)}: {_n(crews, lang)}")

    f = eng.allocate(ctx["frame"], stock, crews)
    s = eng.supply_summary(f, stock)
    m = st.columns(4)
    m[0].metric(c("m_sal", lang), f"{_n(s['saline_allocated'], lang)} / {_n(s['saline_required'], lang)}")
    m[1].metric(c("m_kit", lang), f"{_n(s['kits_allocated'], lang)} / {_n(s['kits_required'], lang)}")
    m[2].metric(c("m_crew", lang), f"{_n(s['crews_assigned'], lang)} / {_n(s['crews_needed'], lang)}")
    m[3].metric(c("m_def", lang), _n(s["wards_deficit"], lang))
    if s["wards_deficit"]:
        st.error(c("deficit", lang, n=_n(s["wards_deficit"], lang), k=_n(s["wards_critical"], lang)))
    else:
        st.success(c("ok_all", lang))
    st.caption(c("how", lang))

    stat = {"ok": c("s_ok", lang), "deficit": c("s_def", lang), "critical": c("s_crit", lang)}
    show = pd.DataFrame({
        c("c_rank", lang): f["priority_rank"],
        c("c_ward", lang): f["ward_id"].map(lambda w: ward_label(w, lang)),
        c("c_city", lang): f["city"].map(lambda x: city_label(x, lang)),
        c("c_risk", lang): f["tier"].map(lambda x: _tier_txt(x, lang)),
        c("c_cases", lang): f["predicted"].round(1),
        c("c_dens", lang): f["density"],
        c("c_sal", lang): f["saline_allocated"].astype(str) + " / " + f["saline_required"].astype(str),
        c("c_kit", lang): f["kits_allocated"].astype(str) + " / " + f["kits_required"].astype(str),
        c("c_bed", lang): f["beds_required"],
        c("c_crew", lang): f["crews_assigned"].astype(str) + " / " + f["crews_needed"].astype(str),
        c("c_stat", lang): f["supply_status"].map(stat),
    })
    st.dataframe(show, hide_index=True, width="stretch", height=520)


# ----------------------------------------------------------------------------
# Page 2: Beds & overflow
# ----------------------------------------------------------------------------
def render_beds_page(artifact, df, issue_date, horizon, lang):
    _header(lang, c("t_beds", lang), horizon, issue_date)
    ctx = _context(artifact, df, str(issue_date.date()), horizon)
    if ctx is None:
        st.info(c("no_data", lang))
        return
    cfg = store.load()
    if auth.is_admin():
        with st.container(border=True):
            cap_pct = st.slider(c("cap_pct", lang), 20, 120, int(cfg["cap_pct"]), 5, key="cmd_cap_w")
            st.caption(c("cap_note", lang))
        if cap_pct != int(cfg["cap_pct"]):
            store.save({"cap_pct": cap_pct})
    else:
        cap_pct = int(cfg["cap_pct"])
        _viewer_note(lang, f"{c('cap_pct', lang)}: {_n(cap_pct, lang)}%")
        st.caption(c("cap_note", lang))

    stock, crews, _ = _settings()
    f = eng.allocate(ctx["frame"], stock, crews)
    w, t, city = eng.route_overflow(f, _capacity(df, cap_pct / 100.0))
    st.caption(c("route_how", lang))

    short = city[city["unrouted"] > 0]
    if short.empty:
        st.success(c("beds_ok", lang))
    for r in short.itertuples():
        st.error(c("city_short", lang, c=city_label(r.city, lang), n=_n(r.unrouted, lang)))

    st.markdown(f"**{c('city_tbl', lang)}**")
    ct = pd.DataFrame({
        c("c_city", lang): city["city"].map(lambda x: city_label(x, lang)),
        c("c_req", lang): city["beds_required"], c("c_cap", lang): city["capacity"],
        c("c_ub", lang): (100 * city["util_before"]).round(0).astype(int).astype(str) + "%",
        c("c_ov", lang): city["overflow"], c("c_rt", lang): city["routed"],
        c("c_un", lang): city["unrouted"],
        c("c_ua", lang): (100 * city["util_after"]).round(0).astype(int).astype(str) + "%",
        c("c_hr", lang): city["headroom_left"],
    })
    st.dataframe(ct, hide_index=True, width="stretch")

    tabs = st.tabs([city_label(x, lang) for x in city["city"]])
    for tab, cname in zip(tabs, city["city"]):
        with tab:
            wc = w[w["city"] == cname].sort_values(["net_deficit", "overflow"], ascending=False)
            st.dataframe(pd.DataFrame({
                c("c_ward", lang): wc["ward_id"].map(lambda x: ward_label(x, lang)),
                c("c_req", lang): wc["beds_required"], c("c_cap", lang): wc["capacity"],
                c("c_sent", lang): wc["sent"], c("c_recv", lang): wc["received"],
                c("c_load", lang): wc["final_load"], c("c_net", lang): wc["net_deficit"],
                c("c_hr", lang): wc["headroom_left"],
            }), hide_index=True, width="stretch")
            tc = t[t["city"] == cname]
            st.markdown(f"**{c('moves', lang)}**")
            if tc.empty:
                st.caption(c("no_moves", lang))
            else:
                st.dataframe(pd.DataFrame({
                    c("c_from", lang): tc["from_ward"].map(lambda x: ward_label(x, lang)),
                    c("c_to", lang): tc["to_ward"].map(lambda x: ward_label(x, lang)),
                    c("c_pat", lang): tc["patients"],
                }), hide_index=True, width="stretch")


# ----------------------------------------------------------------------------
# Page 3: What-if simulator
# ----------------------------------------------------------------------------
def render_whatif_page(artifact, df, issue_date, horizon, lang):
    _header(lang, c("t_sim", lang), horizon, issue_date)
    ctx = _context(artifact, df, str(issue_date.date()), horizon)
    if ctx is None:
        st.info(c("no_data", lang))
        return
    frame = ctx["frame"]
    cfg = store.load()
    options = list(frame.sort_values("predicted", ascending=False)["ward_id"])
    saved_wards = [w for w in cfg["sim_wards"] if w in options]
    if auth.is_admin():
        with st.container(border=True):
            a, b = st.columns([1, 2])
            n_crews = a.number_input(c("sim_crews", lang), 0, 100, int(cfg["sim_crews"]), key="sim_crews")
            picked = b.multiselect(c("sim_pick", lang), options, default=saved_wards,
                                   format_func=lambda x: ward_label(x, lang), key="sim_pick")
        if (int(n_crews), list(picked)) != (int(cfg["sim_crews"]), saved_wards):
            store.save({"sim_crews": int(n_crews), "sim_wards": list(picked)})
    else:
        n_crews, picked = int(cfg["sim_crews"]), saved_wards
        who = ", ".join(ward_label(w, lang) for w in picked) if picked else ("মডেল বাছাই" if lang == "bn" else "model's best wards")
        _viewer_note(lang, f"{c('sim_crews', lang)}: {_n(n_crews, lang)}; {who}")
    st.caption(c("sim_how", lang))
    st.caption(c("sim_factors", lang))

    table = _cached_gain_table(artifact, ctx["rows"], str(issue_date.date()), "h234")
    res, roi, _ = eng.simulate(list(ctx["rows"].keys()), None, int(n_crews), selected=picked or None, table=table)

    region_total = float(sum(table[1][h][:, 0].sum() for h in eng.HORIZONS))
    if region_total < 15:
        st.info(c("sim_low", lang, t=_n(region_total, lang, 1)))
    if float(roi["roi"].max()) <= 1e-9:
        st.warning(c("sim_flat", lang))
    if res.empty:
        return
    base_dep = float(sum(res[f"base_{h}w"].sum() for h in eng.HORIZONS))
    pct = 100.0 * float(res["prevented_total"].sum()) / base_dep if base_dep > 0 else 0.0
    m = st.columns(3)
    m[0].metric(c("sim_total", lang), _n(res["prevented_total"].sum(), lang, 2),
                delta=c("sim_pct", lang, p=_n(pct, lang, 0)), delta_color="off")
    m[1].metric(c("sim_beds", lang), _n(res["beds_saved_peak"].sum(), lang))
    m[2].metric(c("sim_sal", lang), _n(res["saline_saved_total"].sum(), lang))

    fig = go.Figure()
    xs = [c("wk", lang, h=_n(h, lang)) for h in eng.HORIZONS]
    fig.add_bar(name=c("c_base", lang), x=xs, y=[res[f"base_{h}w"].sum() for h in eng.HORIZONS], marker_color="#D55E00")
    fig.add_bar(name=c("c_after", lang), x=xs, y=[res[f"after_{h}w"].sum() for h in eng.HORIZONS], marker_color="#0072B2")
    fig.update_layout(barmode="group", height=320, title=c("chart_title", lang), margin=dict(l=10, r=10, t=50, b=10),
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.markdown(f"**{c('plan_title', lang)}**")
    plan = pd.DataFrame({
        c("c_rank", lang): res["roi_rank"], c("c_ward", lang): res["ward_id"].map(lambda x: ward_label(x, lang)),
        c("c_crew", lang): res["crews"],
        **{f"{c('c_base', lang)} {c('wk', lang, h=h)}": res[f"base_{h}w"].round(1) for h in eng.HORIZONS},
        **{f"{c('c_after', lang)} {c('wk', lang, h=h)}": res[f"after_{h}w"].round(1) for h in eng.HORIZONS},
        c("c_prev", lang): res["prevented_total"].round(1), c("c_roi", lang): res["roi"].round(2),
        c("c_bsv", lang): res["beds_saved_peak"], c("c_ssv", lang): res["saline_saved_total"],
    })
    st.dataframe(plan, hide_index=True, width="stretch")

    ids_all = list(ctx["rows"].keys())
    curve = []
    for k in (1, 2, 4, 8, 12, 16, 24):
        r_k, _, _ = eng.simulate(ids_all, None, k, selected=picked or None, table=table)
        curve.append((k, float(r_k["prevented_total"].sum()) if not r_k.empty else 0.0))
    st.markdown(f"**{c('curve_title', lang)}**")
    st.dataframe(pd.DataFrame({c("c_ncrews", lang): [k for k, _ in curve],
                               c("c_prev", lang): [round(v, 3) for _, v in curve]}),
                 hide_index=True, width="stretch")

    st.markdown(f"**{c('roi_title', lang)}**")
    top = roi.head(15)
    st.dataframe(pd.DataFrame({
        c("c_rank", lang): top["roi_rank"], c("c_ward", lang): top["ward_id"].map(lambda x: ward_label(x, lang)),
        c("c_roi", lang): top["roi"].round(2),
    }), hide_index=True, width="stretch")


# ----------------------------------------------------------------------------
# Page 4: Dispatch & briefs
# ----------------------------------------------------------------------------
def _all_outputs(ctx, df, stock, crews, cap_pct):
    f = eng.allocate(ctx["frame"], stock, crews)
    w, t, city = eng.route_overflow(f, _capacity(df, cap_pct / 100.0))
    return f, w, t


def render_dispatch_page(artifact, df, issue_date, horizon, lang):
    _header(lang, c("t_disp", lang), horizon, issue_date)
    ctx = _context(artifact, df, str(issue_date.date()), horizon)
    if ctx is None:
        st.info(c("no_data", lang))
        return
    stock, crews, cap_pct = _settings()
    st.caption(c("settings_from", lang, s=_n(stock, lang), c=_n(crews, lang)))
    f, w, t = _all_outputs(ctx, df, stock, crews, cap_pct)
    wk = str((issue_date + horizon * WEEK).date())

    r1, r2, r3 = st.columns([1, 2, 1])
    mlang = r3.radio(c("msg_lang", lang), ["bn", "en"], horizontal=True, key="cmd_msg_lang",
                     format_func=lambda k: "বাংলা" if k == "bn" else "English")
    cities = sorted(f["city"].unique())
    city = r1.selectbox(c("pick_city", lang), cities, key="cmd_city", format_func=lambda x: city_label(x, lang))
    fc = f[f["city"] == city]
    ward_id = r2.selectbox(c("pick_ward", lang), list(fc["ward_id"]), key="cmd_ward",
                           format_func=lambda x: f"#{_n(int(fc.loc[fc.ward_id == x, 'priority_rank'].iloc[0]), lang)}  {ward_label(x, lang)}")
    row = next(fc[fc["ward_id"] == ward_id].itertuples())
    notice = eng.compose_notice(row, w.set_index("ward_id").loc[ward_id], t, wk, mlang)
    kb = f"{ward_id}_{mlang}_{wk}_{stock}_{crews}_{cap_pct}"

    s1, s2 = st.columns(2)
    with s1:
        st.markdown(f"**{c('sms', lang)}**")
        sms = st.text_area(c("sms", lang), notice["sms"], height=150, key=f"sms_{kb}", label_visibility="collapsed",
                           disabled=not auth.is_admin())
        st.caption(c("chars", lang, c=_n(len(sms), lang), s=_n(sms_segments(sms), lang)))
    with s2:
        st.markdown(f"**{c('wa', lang)}**")
        wa = st.text_area(c("wa", lang), notice["whatsapp"], height=300, key=f"wa_{kb}", label_visibility="collapsed",
                          disabled=not auth.is_admin())
        if auth.is_admin():
            st.link_button(c("open_wa", lang), wa_link(wa))

    st.markdown(f"### {c('brief_title', lang)}")
    cm = f[f["city"] == city]
    wcity, tcity = w[w["city"] == city], t[t["city"] == city] if not t.empty else t
    html = eng.build_brief_html(city, cm, wcity, tcity, eng.supply_summary(cm, stock), wk, stock, mlang)
    _show_html(html, 640)
    st.download_button(c("dl_brief", lang), html.encode("utf-8"), file_name=f"brief_{city.replace(' ', '_')}_{wk}.html",
                       mime="text/html", key=f"dlb_{kb}")

    if auth.is_admin() and st.button(c("save_ex", lang), key="save_exports"):
        notices, briefs = {}, {}
        wi = w.set_index("ward_id")
        for cname in cities:
            fcity = f[f["city"] == cname]
            top = next(fcity.itertuples())
            for lg in ("bn", "en"):
                nt = eng.compose_notice(top, wi.loc[top.ward_id], t, wk, lg)
                notices[f"sample_sms_{cname.replace(' ', '_')}_{lg}.txt"] = nt["sms"]
                notices[f"sample_whatsapp_{cname.replace(' ', '_')}_{lg}.txt"] = nt["whatsapp"]
                briefs[f"brief_{cname.replace(' ', '_')}_{lg}.html"] = eng.build_brief_html(
                    cname, fcity, w[w["city"] == cname], t[t["city"] == cname] if not t.empty else t,
                    eng.supply_summary(fcity, stock), wk, stock, lg)
        paths = eng.write_exports(EXPORT_DIR, notices, briefs)
        st.success(c("saved", lang, n=_n(len(paths), lang), p=EXPORT_DIR))
