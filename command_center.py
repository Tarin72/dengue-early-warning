"""Resource Command Centre (onsite phase): one page, three modules, fully offline.

1. Constrained resource allocation (saline / kits / beds / spraying crews) with scarcity sliders
2. Hospital surge + intra-city overflow routing
3. What-if vector-control simulator ranked by ROI (cases prevented per crew)

Everything is driven by the SAME cached model forecast as the rest of the dashboard
(+2/+3/+4 weeks). No external API, no LLM: deterministic and reviewable.
"""
import json
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from i18n import city_label, fmt_num, tier_name, ward_label
from src.allocation import allocate
from src.overflow import route_overflow, suggest_beds, ward_capacity
from src.preprocess import FEATURE_COLS, classify_risk_tier, read_data
from src.simulator import DENSITY_PER_CREW, MAX_EFFECT, RAMP, optimise_crews, simulate
from src.train import HORIZONS

WEEK = pd.Timedelta(weeks=1)
SUPPLY_XLSX = "data/bangladesh_dengue_large_dataset_onsite.xlsx"
SUPPLY_JSON = "models/supply_meta.json"
FALLBACK_RATIOS = {"saline_bags_needed": 2.378, "diagnostic_kits_needed": 1.147,
                   "hospital_beds_required": 0.289}
PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}

C = {
    "page_title": {"bn": "সম্পদ ও জরুরি সমন্বয় কেন্দ্র", "en": "Resource command centre"},
    "intro": {
        "bn": "পূর্বাভাসকে স্যালাইন, কিট, শয্যা ও স্প্রে দলের হিসাবে রূপান্তর করা হয়েছে। ভিত্তি: {a}–{b} সপ্তাহ পরের পূর্বাভাস (শেষ আবহাওয়া-সপ্তাহ {d})। সব হিসাব এই কম্পিউটারেই হয়, ইন্টারনেট লাগে না।",
        "en": "The forecast is converted into saline, kits, beds and spraying crews. Basis: the +{a} to +{b} week forecast (last weather week {d}). Everything runs locally, no internet needed.",
    },
    "week": {"bn": "পূর্বাভাসের সপ্তাহ (ডিফল্ট: ড্যাশবোর্ডের সপ্তাহ)", "en": "Forecast week (default: dashboard week)"},
    "offseason": {"bn": "এটি কম-ঝুঁকির মৌসুম, তাই চাহিদা খুব কম। জুলাই–সেপ্টেম্বরের কোনো সপ্তাহ বেছে নিলে বণ্টন ও ঘাটতি স্পষ্ট দেখা যাবে।",
                  "en": "This is off-season, so demand is very low. Pick a July-September week to see allocation and deficits clearly."},
    "severity": {"bn": "প্রাদুর্ভাবের তীব্রতা (চাপ-পরীক্ষা)", "en": "Outbreak severity (stress test)"},
    "severity_help": {"bn": "১.০ = মডেলের পূর্বাভাস। বেশি দিলে ধরে নেওয়া হয় কেস আরও বেশি হবে।",
                      "en": "1.0 = model forecast. Higher assumes more cases than predicted."},
    "tab1": {"bn": "১. সম্পদ বণ্টন", "en": "1. Resource allocation"},
    "tab2": {"bn": "২. হাসপাতাল ওভারফ্লো", "en": "2. Hospital overflow"},
    "tab3": {"bn": "৩. স্প্রে সিমুলেটর", "en": "3. Spraying simulator"},
    "stock": {"bn": "আঞ্চলিক মজুত (%)", "en": "Available regional stock (%)"},
    "crews": {"bn": "মোট স্প্রে দল", "en": "Total spraying crews"},
    "crit_def": {"bn": "গুরুতর সরবরাহ ঘাটতি: {n}টি উচ্চ ঝুঁকির ওয়ার্ডে চাহিদার ৬০%-এর কম পূরণ হচ্ছে।",
                 "en": "CRITICAL SUPPLY DEFICIT in {n} high-risk ward(s): less than 60% of demand can be met."},
    "def": {"bn": "{n}টি ওয়ার্ডে ঘাটতি আছে।", "en": "Deficit in {n} ward(s)."},
    "all_ok": {"bn": "সব ওয়ার্ডের চাহিদা পুরোপুরি পূরণ হচ্ছে।", "en": "All ward demand is fully met."},
    "saline": {"bn": "স্যালাইন ব্যাগ", "en": "Saline bags"},
    "kits": {"bn": "ডায়াগনস্টিক কিট", "en": "Diagnostic kits"},
    "beds": {"bn": "হাসপাতাল শয্যা", "en": "Hospital beds"},
    "crews_m": {"bn": "দল বরাদ্দ / প্রয়োজন", "en": "Crews assigned / needed"},
    "short": {"bn": "{n} ঘাটতি", "en": "{n} deficit"},
    "met": {"bn": "পূর্ণ", "en": "met"},
    "chart1": {"bn": "অগ্রাধিকারে শীর্ষ ১৫ ওয়ার্ড: স্যালাইনের চাহিদা বনাম বরাদ্দ", "en": "Top 15 priority wards: saline required vs allocated"},
    "required": {"bn": "প্রয়োজন", "en": "Required"},
    "allocated": {"bn": "বরাদ্দ", "en": "Allocated"},
    "prio_cap": {"bn": "অগ্রাধিকার = পূর্বাভাসিত কেস × ঝুঁকির মাত্রার ওজন × জনঘনত্ব। মজুত কম হলে সবচেয়ে বেশি অগ্রাধিকারের ওয়ার্ড আগে পূরণ হয়।",
                 "en": "Priority = predicted cases x risk-tier weight x population density. When stock is short, the highest-priority wards are served first."},
    "dl": {"bn": "বরাদ্দ CSV ডাউনলোড", "en": "Download allocation CSV"},
    "c_ward": {"bn": "ওয়ার্ড", "en": "Ward"}, "c_city": {"bn": "শহর", "en": "City"},
    "c_tier": {"bn": "ঝুঁকি", "en": "Risk"}, "c_dens": {"bn": "জনঘনত্ব/বর্গকিমি", "en": "Density/sq km"},
    "c_cases": {"bn": "পূর্বাভাসিত কেস (৩ সপ্তাহ)", "en": "Predicted cases (3 wk)"},
    "c_rs": {"bn": "স্যালাইন প্রয়োজন", "en": "Saline req."}, "c_as": {"bn": "স্যালাইন বরাদ্দ", "en": "Saline alloc."},
    "c_rk": {"bn": "কিট প্রয়োজন", "en": "Kits req."}, "c_ak": {"bn": "কিট বরাদ্দ", "en": "Kits alloc."},
    "c_rb": {"bn": "শয্যা প্রয়োজন", "en": "Beds req."}, "c_ab": {"bn": "শয্যা বরাদ্দ", "en": "Beds alloc."},
    "c_cn": {"bn": "দল প্রয়োজন", "en": "Crews needed"}, "c_ca": {"bn": "দল বরাদ্দ", "en": "Crews assigned"},
    "c_ful": {"bn": "পূরণ %", "en": "Fulfilled %"}, "c_stat": {"bn": "অবস্থা", "en": "Status"},
    "st_OK": {"bn": "পূর্ণ", "en": "OK"}, "st_DEFICIT": {"bn": "ঘাটতি", "en": "DEFICIT"},
    "st_CRITICAL DEFICIT": {"bn": "গুরুতর ঘাটতি", "en": "CRITICAL DEFICIT"},
    "cap_pct": {"bn": "ওয়ার্ডের শয্যা ধারণক্ষমতা (ঐতিহাসিক সর্বোচ্চ চাহিদার %)", "en": "Ward bed capacity (% of historical peak demand)"},
    "cap_note": {"bn": "ডেটাসেটে শয্যার ধারণক্ষমতা নেই, তাই এটি একটি ধারণা। data/bed_capacity.csv দিলে সেটাই ব্যবহার হবে।",
                 "en": "The dataset has no bed capacity, so this is an assumption. Provide data/bed_capacity.csv to override it."},
    "city_over": {"bn": "{n}টি শহরের মোট শয্যা ছাড়িয়ে গেছে: সামলানো যায়নি এমন রোগী থেকে যাচ্ছে।", "en": "{n} city pool(s) exceed total bed capacity: some patients cannot be placed."},
    "city_ok": {"bn": "ওভারফ্লো রোগী প্রতিটি শহরের ভেতরেই সামলানো যাচ্ছে।", "en": "All overflow patients can be absorbed inside their own city."},
    "city_tbl": {"bn": "শহরভিত্তিক শয্যা ব্যবহার", "en": "City-wide bed utilisation"},
    "cc_cap": {"bn": "মোট শয্যা", "en": "Total beds"}, "cc_dem": {"bn": "পূর্বাভাসিত চাহিদা", "en": "Projected demand"},
    "cc_util": {"bn": "ব্যবহার %", "en": "Utilisation %"}, "cc_def": {"bn": "নিট ঘাটতি", "en": "Net deficit"},
    "cc_head": {"bn": "ফাঁকা শয্যা (রুটিংয়ের পর)", "en": "Free beds after routing"}, "cc_stat": {"bn": "অবস্থা", "en": "Status"},
    "cs_OK": {"bn": "স্বাভাবিক", "en": "OK"}, "cs_TIGHT": {"bn": "চাপে", "en": "TIGHT"},
    "cs_CITY OVER CAPACITY": {"bn": "ধারণক্ষমতা ছাড়িয়েছে", "en": "OVER CAPACITY"},
    "tr_title": {"bn": "রোগী স্থানান্তর (শুধু একই শহরের ভেতরে)", "en": "Patient transfers (within the same city only)"},
    "tr_none": {"bn": "কোনো স্থানান্তর দরকার নেই।", "en": "No transfers needed."},
    "t_from": {"bn": "যে ওয়ার্ড থেকে", "en": "From ward"}, "t_to": {"bn": "যে ওয়ার্ডে", "en": "To ward"},
    "t_pat": {"bn": "রোগী", "en": "Patients"},
    "t_steps": {"bn": "দূরত্ব (ওয়ার্ড নম্বরের ব্যবধান)", "en": "Distance (ward-number gap)"},
    "bf_title": {"bn": "শয্যা খুঁজুন: নিজের এলাকায় না থাকলে কাছের কোথায় আছে", "en": "Bed finder: where to go if your own ward is full"},
    "bf_pick": {"bn": "রোগী কোন ওয়ার্ডের?", "en": "Patient's ward"},
    "bf_own": {"bn": "এই ওয়ার্ডেই {n}টি শয্যা ফাঁকা আছে। এখানেই ভর্তি করা যাবে।", "en": "This ward has {n} free bed(s). Admit here."},
    "bf_near": {"bn": "এই ওয়ার্ডে শয্যা ফাঁকা নেই। সবচেয়ে কাছের শয্যাসহ ওয়ার্ড: {w} ({n}টি ফাঁকা, দূরত্ব {s})।", "en": "No free bed in this ward. Nearest ward with beds: {w} ({n} free, distance {s})."},
    "bf_none": {"bn": "এই শহরের কোনো ওয়ার্ডে এখন শয্যা ফাঁকা নেই। অন্য শহর বা জরুরি ব্যবস্থার সাথে যোগাযোগ করুন।", "en": "No ward in this city has a free bed. Contact another city or emergency services."},
    "bf_free": {"bn": "ফাঁকা শয্যা", "en": "Free beds"},
    "near_title": {"bn": "শয্যা ভরে যাওয়া ওয়ার্ডের কাছাকাছি ওয়ার্ডে ফাঁকা শয্যা", "en": "Free beds in the nearest wards of every full ward"},
    "near_none": {"bn": "কোনো ওয়ার্ডের শয্যা ভরেনি।", "en": "No ward has run out of beds."},
    "near_cap": {"bn": "ডেটাসেটে ঠিকানা বা মানচিত্রের স্থানাঙ্ক নেই, তাই 'কাছের' মানে একই শহরের কাছাকাছি ওয়ার্ড নম্বর (ধারণা)। স্থানাঙ্কসহ ওয়ার্ড-তালিকা পেলে দূরত্ব বদলে ফেলা যায়।",
                 "en": "The dataset has no addresses or coordinates, so 'nearest' means the closest ward number in the same city (assumption). With a ward coordinate list the distance can be swapped in."},
    "n_full": {"bn": "ভরে যাওয়া ওয়ার্ড", "en": "Full ward"}, "n_near": {"bn": "কাছের ওয়ার্ড", "en": "Nearby ward"},
    "n_cap": {"bn": "শয্যা (মোট)", "en": "Beds (total)"}, "n_fb": {"bn": "ফাঁকা (আগে)", "en": "Free (before)"},
    "n_fa": {"bn": "ফাঁকা (স্থানান্তরের পর)", "en": "Free (after transfers)"},
    "w_title": {"bn": "ওয়ার্ডভিত্তিক শয্যা অবস্থা", "en": "Ward bed status"},
    "w_dem": {"bn": "চাহিদা", "en": "Demand"}, "w_cap": {"bn": "ধারণক্ষমতা", "en": "Capacity"},
    "w_recv": {"bn": "গৃহীত রোগী", "en": "Received"}, "w_u0": {"bn": "আগের ব্যবহার %", "en": "Before %"},
    "w_u1": {"bn": "পরের ব্যবহার %", "en": "After %"},
    "chart2": {"bn": "শহরভিত্তিক শয্যা ব্যবহার (%)", "en": "City bed utilisation (%)"},
    "sim_n": {"bn": "মোতায়েনের দল সংখ্যা", "en": "Crews to deploy"},
    "sim_mode": {"bn": "মোতায়েন পদ্ধতি", "en": "Deployment mode"},
    "sim_auto": {"bn": "স্বয়ংক্রিয় (সর্বোচ্চ ROI)", "en": "Auto (maximise ROI)"}, "sim_man": {"bn": "ম্যানুয়াল", "en": "Manual"},
    "sim_pick": {"bn": "ওয়ার্ড বাছুন", "en": "Select wards"}, "sim_per": {"bn": "প্রতি ওয়ার্ডে দল", "en": "Crews per ward"},
    "m_prev": {"bn": "প্রতিরোধযোগ্য কেস", "en": "Cases prevented"}, "m_beds": {"bn": "শয্যার সর্বোচ্চ চাপ কমা", "en": "Peak beds saved"},
    "m_sal": {"bn": "স্যালাইন সাশ্রয়", "en": "Saline saved"}, "m_roi": {"bn": "গড় ROI (কেস/দল)", "en": "Avg ROI (cases/crew)"},
    "chart3": {"bn": "পূর্বাভাসিত কেস: স্প্রের আগে ও পরে", "en": "Predicted cases: baseline vs with spraying"},
    "base": {"bn": "স্প্রে ছাড়া", "en": "Baseline"}, "after": {"bn": "স্প্রে সহ", "en": "With spraying"},
    "wk": {"bn": "+{h} সপ্তাহ", "en": "+{h} wk"},
    "roi_title": {"bn": "ROI অনুযায়ী ওয়ার্ড র‍্যাঙ্কিং (প্রতি দলে প্রতিরোধযোগ্য কেস)", "en": "Wards ranked by intervention ROI (cases prevented per crew)"},
    "r_crews": {"bn": "দল", "en": "Crews"}, "r_base": {"bn": "স্প্রে ছাড়া কেস", "en": "Baseline cases"},
    "r_after": {"bn": "স্প্রে সহ কেস", "en": "Cases with spraying"}, "r_prev": {"bn": "প্রতিরোধযোগ্য", "en": "Prevented"},
    "r_roi": {"bn": "ROI (কেস/দল)", "en": "ROI (cases/crew)"}, "r_beds": {"bn": "শয্যা সাশ্রয়", "en": "Beds saved"},
    "r_sal": {"bn": "স্যালাইন সাশ্রয়", "en": "Saline saved"},
    "sim_cap": {"bn": "ধারণা (সম্পাদনাযোগ্য, src/simulator.py): পূর্ণ আবরণে সর্বোচ্চ {m}% কেস কমে; প্রভাব +২ সপ্তাহে {r2}%, +৩ সপ্তাহে {r3}%, +৪ সপ্তাহে {r4}% (ডিম থেকে মশা হওয়ার সময় অনুযায়ী)। একটি দল প্রায় {d} জনঘনত্ব পর্যন্ত ওয়ার্ড পূর্ণ আবৃত করে। হস্তক্ষেপের আসল ডেটা না থাকায় এগুলো ধারণা।",
                "en": "Assumptions (editable in src/simulator.py): full coverage removes at most {m}% of cases; the effect builds to {r2}% at +2 wk, {r3}% at +3 wk and {r4}% at +4 wk (breeding clock). One crew fully covers about {d} people/sq km. No intervention data exists, so these are assumptions."},
    "no_data": {"bn": "এই সপ্তাহের জন্য পূর্বাভাসের ডেটা নেই।", "en": "No forecast data for this week."},
}


def c(key, lang, **kw):
    text = C[key][lang]
    return text.format(**kw) if kw else text


@st.cache_data(show_spinner=False)
def load_supply_meta(_df):
    """Supply ratios (per predicted case) and each ward's historical peak bed demand.
    Read once from the onsite dataset, then cached in models/supply_meta.json."""
    if os.path.exists(SUPPLY_JSON):
        try:
            return json.load(open(SUPPLY_JSON))
        except Exception:
            pass
    try:
        raw = read_data(SUPPLY_XLSX)
        total = float(raw["dengue_cases"].sum())
        ratios = {k: float(raw[k].sum() / total) for k in FALLBACK_RATIOS}
        peak = raw.groupby("ward_id")["hospital_beds_required"].max().astype(float).to_dict()
    except Exception:  # onsite file missing: derive from cases with fallback ratios
        ratios = dict(FALLBACK_RATIOS)
        peak = (_df.groupby("ward_id")["dengue_cases"].max() * ratios["hospital_beds_required"]).to_dict()
    meta = {"ratios": ratios, "peak_beds": peak}
    try:
        os.makedirs("models", exist_ok=True)
        json.dump(meta, open(SUPPLY_JSON, "w"))
    except Exception:
        pass
    return meta


@st.cache_data(show_spinner=False)
def ward_forecast(issue_str, _artifact, _df):
    """One batched prediction for all 60 wards at every horizon (+2/+3/+4 weeks)."""
    issue_date = pd.Timestamp(issue_str)
    snap = _df[_df["date"] == issue_date + 2 * WEEK].dropna(subset=FEATURE_COLS)
    out = snap[["ward_id", "city", "population_density_sqkm"]].reset_index(drop=True)
    for h in HORIZONS:
        out[f"pred_h{h}"] = np.clip(_artifact["models"][h].predict(snap[FEATURE_COLS]), 0, None)
    return out


def _with_totals(fc, severity):
    fc = fc.copy()
    for h in HORIZONS:
        fc[f"pred_h{h}"] = fc[f"pred_h{h}"] * severity
    cols = [f"pred_h{h}" for h in HORIZONS]
    fc["pred_total"] = fc[cols].sum(axis=1)
    fc["pred_peak_week"] = fc[cols].max(axis=1)
    fc["risk_tier"] = fc["pred_peak_week"].apply(classify_risk_tier)
    return fc


def _csv(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def _tab_allocation(fc, ratios, lang):
    c1, c2 = st.columns(2)
    stock = c1.slider(c("stock", lang), 30, 100, 70, key="cc_stock")
    crews = c2.slider(c("crews", lang), 0, 60, 20, key="cc_crews")
    alloc, sm = allocate(fc, ratios, stock, crews)

    if sm["wards_critical_deficit"]:
        st.error(c("crit_def", lang, n=fmt_num(sm["wards_critical_deficit"], lang, 0)))
    elif sm["wards_deficit"]:
        st.warning(c("def", lang, n=fmt_num(sm["wards_deficit"], lang, 0)))
    else:
        st.success(c("all_ok", lang))

    cols = st.columns(4)
    for col, key, label in zip(cols[:3], ["saline_bags_needed", "diagnostic_kits_needed", "hospital_beds_required"],
                               ["saline", "kits", "beds"]):
        r = sm[key]
        col.metric(c(label, lang), f"{fmt_num(r['allocated'], lang, 0)} / {fmt_num(r['required'], lang, 0)}",
                   ("-" + c("short", lang, n=fmt_num(r["deficit"], lang, 0)) if r["deficit"] else c("met", lang)),
                   delta_color="inverse" if r["deficit"] else "off")
    cols[3].metric(c("crews_m", lang),
                   f"{fmt_num(sm['crews_assigned_total'], lang, 0)} / {fmt_num(sm['crews_needed_total'], lang, 0)}")

    top = alloc.head(15)
    fig = go.Figure()
    labels = [ward_label(w, lang) for w in top["ward_id"]]
    fig.add_bar(x=labels, y=top["req_saline_bags_needed"], name=c("required", lang), marker_color="#C9CFCB")
    fig.add_bar(x=labels, y=top["alloc_saline_bags_needed"], name=c("allocated", lang), marker_color="#0B5D45")
    fig.update_layout(barmode="group", height=330, margin=dict(l=8, r=8, t=36, b=8),
                      title=c("chart1", lang), paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.35))
    st.plotly_chart(fig, config=PLOTLY_CONFIG, width="stretch")
    st.caption(c("prio_cap", lang))

    show = pd.DataFrame({
        c("c_ward", lang): [ward_label(w, lang) for w in alloc["ward_id"]],
        c("c_city", lang): [city_label(x, lang) for x in alloc["city"]],
        c("c_tier", lang): [tier_name(x, lang, short=True) for x in alloc["risk_tier"]],
        c("c_dens", lang): alloc["population_density_sqkm"].astype(int),
        c("c_cases", lang): alloc["cases"].round(1),
        c("c_rs", lang): alloc["req_saline_bags_needed"], c("c_as", lang): alloc["alloc_saline_bags_needed"],
        c("c_rk", lang): alloc["req_diagnostic_kits_needed"], c("c_ak", lang): alloc["alloc_diagnostic_kits_needed"],
        c("c_rb", lang): alloc["req_hospital_beds_required"], c("c_ab", lang): alloc["alloc_hospital_beds_required"],
        c("c_cn", lang): alloc["crews_needed"], c("c_ca", lang): alloc["crews_assigned"],
        c("c_ful", lang): alloc["fulfilment_pct"],
        c("c_stat", lang): [c(f"st_{x}", lang) for x in alloc["status"]],
    })
    st.dataframe(show, width="stretch", hide_index=True)
    st.download_button(c("dl", lang), _csv(alloc.drop(columns=["priority"])), "allocation.csv", "text/csv")


def _tab_overflow(fc, ratios, peak_beds, lang):
    pct = st.slider(c("cap_pct", lang), 20, 80, 40, step=5, key="cc_cap_pct")
    st.caption(c("cap_note", lang))
    cap = ward_capacity(peak_beds, pct)
    wards, transfers, city_tbl, nearby = route_overflow(fc, ratios, cap)

    over = int((city_tbl["net_deficit"] > 0).sum())
    (st.error if over else st.success)(c("city_over", lang, n=fmt_num(over, lang, 0)) if over else c("city_ok", lang))

    st.subheader(c("bf_title", lang))
    full = list(wards.sort_values(["free_now", "ward_id"])["ward_id"])      # full wards first
    pick = st.selectbox(c("bf_pick", lang), full, format_func=lambda w: ward_label(w, lang), key="cc_bf")
    kind, n_own, sug = suggest_beds(wards, pick)
    if kind == "own":
        st.success(c("bf_own", lang, n=fmt_num(n_own, lang, 0)))
    elif kind == "none":
        st.error(c("bf_none", lang))
    else:
        top = sug.iloc[0]
        st.warning(c("bf_near", lang, w=ward_label(top["ward_id"], lang), n=fmt_num(top["free_now"], lang, 0),
                     s=fmt_num(top["steps"], lang, 0)))
        st.dataframe(pd.DataFrame({
            c("n_near", lang): [ward_label(x, lang) for x in sug["ward_id"]],
            c("t_steps", lang): sug["steps"], c("n_cap", lang): sug["capacity"], c("bf_free", lang): sug["free_now"],
        }), width="stretch", hide_index=True)

    st.subheader(c("city_tbl", lang))
    ct = pd.DataFrame({
        c("c_city", lang): [city_label(x, lang) for x in city_tbl["city"]],
        c("cc_cap", lang): city_tbl["capacity"], c("cc_dem", lang): city_tbl["demand"],
        c("cc_util", lang): city_tbl["utilisation_pct"], c("cc_def", lang): city_tbl["net_deficit"],
        c("cc_head", lang): city_tbl["headroom_after_routing"],
        c("cc_stat", lang): [c(f"cs_{x}", lang) for x in city_tbl["status"]],
    })
    st.dataframe(ct, width="stretch", hide_index=True)

    fig = go.Figure(go.Bar(x=[city_label(x, lang) for x in city_tbl["city"]], y=city_tbl["utilisation_pct"],
                           marker_color=["#B3261E" if v > 100 else "#D95F02" if v > 85 else "#0B5D45"
                                         for v in city_tbl["utilisation_pct"]]))
    fig.add_hline(y=100, line_dash="dash", line_color="#7A0C1E")
    fig.update_layout(height=280, margin=dict(l=8, r=8, t=36, b=8), title=c("chart2", lang),
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, config=PLOTLY_CONFIG, width="stretch")

    st.subheader(c("tr_title", lang))
    if transfers.empty:
        st.info(c("tr_none", lang))
    else:
        tt = pd.DataFrame({
            c("c_city", lang): [city_label(x, lang) for x in transfers["city"]],
            c("t_from", lang): [ward_label(x, lang) for x in transfers["from_ward"]],
            c("t_to", lang): [ward_label(x, lang) for x in transfers["to_ward"]],
            c("t_pat", lang): transfers["patients"], c("t_steps", lang): transfers["steps"],
        })
        st.dataframe(tt, width="stretch", hide_index=True)
        st.download_button(c("dl", lang), _csv(transfers), "overflow_transfers.csv", "text/csv", key="dl_tr")

    st.subheader(c("near_title", lang))
    if nearby.empty:
        st.info(c("near_none", lang))
    else:
        nt = pd.DataFrame({
            c("n_full", lang): [ward_label(x, lang) for x in nearby["ward"]],
            c("n_near", lang): [ward_label(x, lang) for x in nearby["nearby_ward"]],
            c("t_steps", lang): nearby["steps"], c("n_cap", lang): nearby["capacity"],
            c("n_fb", lang): nearby["free_before"], c("n_fa", lang): nearby["free_after"],
        })
        st.dataframe(nt, width="stretch", hide_index=True)
    st.caption(c("near_cap", lang))

    st.subheader(c("w_title", lang))
    wt = pd.DataFrame({
        c("c_ward", lang): [ward_label(x, lang) for x in wards["ward_id"]],
        c("c_city", lang): [city_label(x, lang) for x in wards["city"]],
        c("w_dem", lang): wards["beds_demand"], c("w_cap", lang): wards["capacity"],
        c("w_recv", lang): wards["received"], c("cc_def", lang): wards["net_deficit"],
        c("w_u0", lang): wards["initial_util_pct"], c("w_u1", lang): wards["final_util_pct"],
    })
    st.dataframe(wt, width="stretch", hide_index=True)


def _tab_simulator(fc, ratios, lang):
    c1, c2 = st.columns(2)
    n = c1.slider(c("sim_n", lang), 0, 40, 12, key="cc_sim_n")
    mode = c2.radio(c("sim_mode", lang), ["auto", "manual"], horizontal=True, key="cc_sim_mode",
                    format_func=lambda m: c("sim_auto" if m == "auto" else "sim_man", lang))
    if mode == "auto":
        deploy = optimise_crews(fc, n)
    else:
        picks = st.multiselect(c("sim_pick", lang), list(fc.sort_values("pred_total", ascending=False)["ward_id"]),
                               format_func=lambda w: ward_label(w, lang), key="cc_sim_pick")
        per = st.number_input(c("sim_per", lang), 1, 6, 2, key="cc_sim_per")
        deploy = {w: int(per) for w in picks}

    sim = simulate(fc, deploy, ratios)
    used = int(sim["crews"].sum())
    m = st.columns(4)
    m[0].metric(c("m_prev", lang), fmt_num(sim["cases_prevented"].sum(), lang, 1))
    m[1].metric(c("m_beds", lang), fmt_num(sim["beds_saved"].sum(), lang, 1))
    m[2].metric(c("m_sal", lang), fmt_num(sim["saline_saved"].sum(), lang, 0))
    m[3].metric(c("m_roi", lang), fmt_num(sim["cases_prevented"].sum() / max(1, used), lang, 2))

    xs = [c("wk", lang, h=fmt_num(h, lang, 0)) for h in HORIZONS]
    fig = go.Figure()
    fig.add_scatter(x=xs, y=[sim[f"base_h{h}"].sum() for h in HORIZONS], name=c("base", lang),
                    mode="lines+markers", line=dict(color="#7A0C1E"))
    fig.add_scatter(x=xs, y=[sim[f"after_h{h}"].sum() for h in HORIZONS], name=c("after", lang),
                    mode="lines+markers", line=dict(color="#0B5D45"))
    fig.update_layout(height=300, margin=dict(l=8, r=8, t=36, b=8), title=c("chart3", lang),
                      paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig, config=PLOTLY_CONFIG, width="stretch")

    st.subheader(c("roi_title", lang))
    dep = sim[sim["crews"] > 0]
    if dep.empty:
        st.info(c("no_data", lang) if mode == "auto" else c("sim_pick", lang))
    else:
        rt = pd.DataFrame({
            c("c_ward", lang): [ward_label(w, lang) for w in dep["ward_id"]],
            c("c_city", lang): [city_label(x, lang) for x in dep["city"]],
            c("c_tier", lang): [tier_name(x, lang, short=True) for x in dep["risk_tier"]],
            c("r_crews", lang): dep["crews"], c("r_base", lang): dep["cases_base"].round(1),
            c("r_after", lang): dep["cases_after"].round(1), c("r_prev", lang): dep["cases_prevented"].round(1),
            c("r_roi", lang): dep["roi_cases_per_crew"].round(2),
            c("r_beds", lang): dep["beds_saved"].round(2), c("r_sal", lang): dep["saline_saved"].round(1),
        })
        st.dataframe(rt, width="stretch", hide_index=True)
        st.download_button(c("dl", lang), _csv(dep), "intervention_roi.csv", "text/csv", key="dl_roi")
    st.caption(c("sim_cap", lang, m=int(MAX_EFFECT * 100), r2=int(MAX_EFFECT * RAMP[2] * 100),
                 r3=int(MAX_EFFECT * RAMP[3] * 100), r4=int(MAX_EFFECT * RAMP[4] * 100), d=f"{DENSITY_PER_CREW:,}"))


def render_command_center_page(artifact, df, issue_date, lang):
    st.subheader(c("page_title", lang))
    weeks = sorted(df.dropna(subset=FEATURE_COLS)["date"].unique())
    options = [str((pd.Timestamp(d) - 2 * WEEK).date()) for d in weeks]
    default = str(issue_date.date())
    idx = options.index(default) if default in options else len(options) - 1
    c1, c2 = st.columns([1.3, 1])
    issue_str = c1.selectbox(c("week", lang), options, index=idx, key=f"cc_week_{default}")
    severity = c2.slider(c("severity", lang), 0.5, 2.0, 1.0, 0.1, help=c("severity_help", lang), key="cc_sev")
    st.caption(c("intro", lang, a=fmt_num(HORIZONS[0], lang, 0), b=fmt_num(HORIZONS[-1], lang, 0),
                 d=fmt_num(issue_str, lang, None)))
    fc = ward_forecast(issue_str, artifact, df)
    if fc.empty:
        st.info(c("no_data", lang))
        return
    meta = load_supply_meta(df)
    fc = _with_totals(fc, severity)
    if fc["pred_total"].sum() < 60:
        st.info(c("offseason", lang))

    t1, t2, t3 = st.tabs([c("tab1", lang), c("tab2", lang), c("tab3", lang)])
    with t1:
        _tab_allocation(fc, meta["ratios"], lang)
    with t2:
        _tab_overflow(fc, meta["ratios"], meta["peak_beds"], lang)
    with t3:
        _tab_simulator(fc, meta["ratios"], lang)
