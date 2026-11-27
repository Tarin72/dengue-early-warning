"""Phase 2 engine: demand -> constrained allocation -> overflow routing -> what-if -> dispatch.

Everything here is deterministic, local and offline (no network, no LLM). The only
model-dependent step is the counterfactual simulator, which receives a `predict_batch`
callable built from the saved Phase 1 model (see command.py).

Assumptions are collected in the constants below so they can be defended in Q&A:
* SUPPLY_PER_CASE: fitted on the onsite dataset. round(cases * k) reproduces
  saline_bags_needed, diagnostic_kits_needed and hospital_beds_required on all 31,320 rows.
* Bed capacity is NOT in the dataset. We assume each ward's capacity is 50% of the
  largest weekly bed demand it saw in 2016-2025 (min 2 beds). Replace with real
  capacity data when available: pass your own {ward_id: beds} dict.
* Crew need per tier and the effect of one crew are operational assumptions.
"""
import html as html_lib
import math
import os

import numpy as np
import pandas as pd

from i18n import city_label, fmt_num, tier_name, to_bn_digits, ward_label

HORIZONS = (2, 3, 4)

SUPPLY_PER_CASE = {
    "saline_bags_needed": 2.385,
    "diagnostic_kits_needed": 1.164,
    "hospital_beds_required": 0.298,
}
TIER_WEIGHT = {"Low": 1.0, "Medium": 1.5, "High": 2.0, "Critical": 3.0}
CREWS_NEEDED = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
BED_CAPACITY_FACTOR = 0.5
MIN_WARD_BEDS = 2
CREW_EFFECT_PER_CREW = 0.25   # each crew removes 25% of remaining breeding habitat
MAX_REDUCTION = 0.75
MAX_CREWS_PER_WARD = 4


# ----------------------------------------------------------------------------
# Demand
# ----------------------------------------------------------------------------
def _round_half_up(x):
    return np.floor(np.asarray(x, dtype=float) + 0.5).astype(int)


def demand_from_cases(cases):
    """Predicted weekly cases -> (saline, kits, beds) using the dataset-fitted ratios."""
    c = np.clip(np.asarray(cases, dtype=float), 0, None)
    return {k: _round_half_up(c * v) for k, v in SUPPLY_PER_CASE.items()}


def bed_capacity_map(history, factor=BED_CAPACITY_FACTOR):
    """history: frame with ward_id + dengue_cases (all weeks). Returns {ward_id: beds}."""
    case_col = "dengue_cases" if "dengue_cases" in history.columns else next(
        c for c in history.columns if "case" in c.lower())
    peak_cases = history.groupby("ward_id")[case_col].max()
    peak_beds = _round_half_up(peak_cases.values * SUPPLY_PER_CASE["hospital_beds_required"])
    cap = np.maximum(MIN_WARD_BEDS, np.ceil(factor * peak_beds)).astype(int)
    return dict(zip(peak_cases.index, cap))


# ----------------------------------------------------------------------------
# 1. Constrained allocation
# ----------------------------------------------------------------------------
def _fill(required, pool):
    """Greedy fill in the given (already priority-sorted) order."""
    required = np.asarray(required, dtype=int)
    before = np.cumsum(required) - required
    return np.minimum(required, np.maximum(pool - before, 0)).astype(int)


def allocate(frame, stock_pct, total_crews):
    """frame: ward_id, city, predicted, tier, density. Returns priority-sorted frame.

    priority = tier_weight x predicted_cases x (density / mean density)
    Stock pool = stock_pct% of total regional demand (saline and kits separately), filled
    in priority order, so high-risk, dense wards are served first and the tail gets deficits.
    Crews: need by tier (Critical 3, High 2, Medium 1), assigned in priority order.
    """
    f = frame.copy()
    dem = demand_from_cases(f["predicted"])
    f["saline_required"] = dem["saline_bags_needed"]
    f["kits_required"] = dem["diagnostic_kits_needed"]
    f["beds_required"] = dem["hospital_beds_required"]
    mean_density = max(float(f["density"].mean()), 1.0)
    f["priority"] = f["tier"].map(TIER_WEIGHT) * f["predicted"] * (f["density"] / mean_density)
    f = f.sort_values(["priority", "predicted"], ascending=False).reset_index(drop=True)
    f["priority_rank"] = np.arange(1, len(f) + 1)

    frac = float(stock_pct) / 100.0
    for key, req in (("saline", "saline_required"), ("kits", "kits_required")):
        pool = int(_round_half_up(frac * f[req].sum()))
        f[f"{key}_allocated"] = _fill(f[req].values, pool)
        f[f"{key}_deficit"] = f[req] - f[f"{key}_allocated"]
        with np.errstate(divide="ignore", invalid="ignore"):
            f[f"{key}_fill"] = np.where(f[req] > 0, f[f"{key}_allocated"] / f[req], 1.0)

    worst = f[["saline_fill", "kits_fill"]].min(axis=1)
    f["supply_status"] = np.where(worst >= 1.0, "ok", np.where(worst < 0.5, "critical", "deficit"))

    need = f["tier"].map(CREWS_NEEDED).astype(int)
    f["crews_needed"] = need
    f["crews_assigned"] = _fill(need.values, int(total_crews))
    return f


def supply_summary(f, stock_pct):
    return {
        "stock_pct": stock_pct,
        "saline_required": int(f["saline_required"].sum()),
        "saline_allocated": int(f["saline_allocated"].sum()),
        "kits_required": int(f["kits_required"].sum()),
        "kits_allocated": int(f["kits_allocated"].sum()),
        "crews_needed": int(f["crews_needed"].sum()),
        "crews_assigned": int(f["crews_assigned"].sum()),
        "wards_deficit": int((f["supply_status"] != "ok").sum()),
        "wards_critical": int((f["supply_status"] == "critical").sum()),
    }


# ----------------------------------------------------------------------------
# 2. Cross-ward overflow routing (strictly inside each city)
# ----------------------------------------------------------------------------
def route_overflow(f, capacity, default_capacity=MIN_WARD_BEDS):
    """Move bed overflow to the NEAREST ward of the same city that still has free beds.

    The dataset has no coordinates, so "nearest" = closest ward number inside the city
    (ties: the ward with the most free beds). Returns (ward_df, transfers_df, city_df).
    """
    w = f[["ward_id", "city", "beds_required"]].copy()
    w["capacity"] = w["ward_id"].map(capacity).fillna(default_capacity).astype(int)
    w["overflow"] = (w["beds_required"] - w["capacity"]).clip(lower=0)
    w["headroom"] = (w["capacity"] - w["beds_required"]).clip(lower=0)
    w["num"] = w["ward_id"].str.extract(r"(\d+)$")[0].astype(int)

    transfers, unrouted = [], {}
    for city, g in w.sort_values("ward_id").groupby("city"):
        head = dict(zip(g["ward_id"], g["headroom"]))
        num = dict(zip(g["ward_id"], g["num"]))
        for src in g.sort_values(["overflow", "ward_id"], ascending=[False, True]).itertuples():
            left = int(src.overflow)
            while left > 0:
                cands = [x for x in head if head[x] > 0 and x != src.ward_id]
                if not cands:
                    break
                dst = min(cands, key=lambda x: (abs(num[x] - src.num), -head[x], x))
                n = int(min(left, head[dst]))
                transfers.append({"city": city, "from_ward": src.ward_id, "to_ward": dst, "patients": n,
                                  "steps": int(abs(num[dst] - src.num))})
                head[dst] -= n
                left -= n
            unrouted[src.ward_id] = left

    t = pd.DataFrame(transfers, columns=["city", "from_ward", "to_ward", "patients", "steps"])
    sent = t.groupby("from_ward")["patients"].sum() if not t.empty else pd.Series(dtype=int)
    recv = t.groupby("to_ward")["patients"].sum() if not t.empty else pd.Series(dtype=int)
    w["sent"] = w["ward_id"].map(sent).fillna(0).astype(int)
    w["received"] = w["ward_id"].map(recv).fillna(0).astype(int)
    w["net_deficit"] = w["ward_id"].map(unrouted).fillna(0).astype(int)
    w["final_load"] = w["beds_required"] - w["sent"] + w["received"]
    w["headroom_left"] = (w["capacity"] - w["final_load"]).clip(lower=0)

    c = w.groupby("city").agg(
        beds_required=("beds_required", "sum"), capacity=("capacity", "sum"),
        overflow=("overflow", "sum"), unrouted=("net_deficit", "sum"),
        headroom_left=("headroom_left", "sum"),
    ).reset_index()
    c["routed"] = c["overflow"] - c["unrouted"]
    c["util_before"] = c["beds_required"] / c["capacity"].clip(lower=1)
    c["util_after"] = (c["beds_required"] - c["unrouted"]) / c["capacity"].clip(lower=1)
    return w, t, c


def suggest_beds(w, ward_id, k=3):
    """Bed finder. Returns (kind, free_beds_in_own_ward, table_of_nearest_wards_with_free_beds).
    kind: 'own' (own ward has a free bed) | 'nearby' | 'none' (no free bed anywhere in the city)."""
    me = w[w["ward_id"] == ward_id].iloc[0]
    if me["headroom_left"] > 0:
        return "own", int(me["headroom_left"]), pd.DataFrame()
    cand = w[(w["city"] == me["city"]) & (w["ward_id"] != ward_id) & (w["headroom_left"] > 0)].copy()
    cand["steps"] = (cand["num"] - me["num"]).abs()
    cand = cand.sort_values(["steps", "headroom_left"], ascending=[True, False]).head(k)
    return ("nearby" if len(cand) else "none"), 0, cand[["ward_id", "steps", "capacity", "headroom_left"]]


# ----------------------------------------------------------------------------
# 3. What-if simulator (model-driven counterfactual)
# ----------------------------------------------------------------------------
def crew_reduction(crews):
    """Share of breeding habitat removed by `crews` crews (diminishing returns)."""
    return float(min(MAX_REDUCTION, 1.0 - (1.0 - CREW_EFFECT_PER_CREW) ** max(int(crews), 0)))


def _gain_table(ward_ids, predict_batch, max_crews=MAX_CREWS_PER_WARD):
    """cases[h][w][k] = predicted weekly cases at horizon h in ward w with k crews."""
    ids = list(ward_ids)
    out = {h: np.zeros((len(ids), max_crews + 1)) for h in HORIZONS}
    for k in range(max_crews + 1):
        pred = predict_batch(ids, [crew_reduction(k)] * len(ids))
        for h in HORIZONS:
            out[h][:, k] = pred[h]
    return ids, out


def simulate(ward_ids, predict_batch, total_crews, selected=None, table=None):
    """Greedy marginal deployment of `total_crews` crews + per-ward ROI.

    selected: optional list of ward_ids the officer picked; crews go only there.
    Returns (results_df, roi_df, crews_by_ward).
    ROI = cases prevented (sum of weekly forecasts at +2,+3,+4 weeks) per crew.
    """
    ids, tbl = table if table is not None else _gain_table(ward_ids, predict_batch)
    total = sum(tbl[h] for h in HORIZONS)               # (n, crews+1)
    gain = total[:, [0]] - total                        # cumulative prevented with k crews
    allowed = [i for i, w in enumerate(ids) if selected is None or w in set(selected)]

    roi = pd.DataFrame({
        "ward_id": ids,
        "prevented_1crew": gain[:, 1],
        "roi": gain[:, 1],                              # per 1 crew
    }).sort_values("roi", ascending=False).reset_index(drop=True)
    roi["roi_rank"] = np.arange(1, len(roi) + 1)

    crews = {w: 0 for w in ids}
    for _ in range(int(total_crews)):
        best, best_gain = None, 1e-9
        for i in allowed:
            k = crews[ids[i]]
            if k >= MAX_CREWS_PER_WARD:
                continue
            marginal = gain[i, k + 1] - gain[i, k]
            if marginal > best_gain:
                best, best_gain = i, marginal
        if best is None:
            break
        crews[ids[best]] += 1

    rows = []
    for i, w in enumerate(ids):
        k = crews[w]
        if k == 0:
            continue
        row = {"ward_id": w, "crews": k}
        for h in HORIZONS:
            row[f"base_{h}w"] = tbl[h][i, 0]
            row[f"after_{h}w"] = tbl[h][i, k]
            row[f"prevented_{h}w"] = tbl[h][i, 0] - tbl[h][i, k]
        row["prevented_total"] = sum(row[f"prevented_{h}w"] for h in HORIZONS)
        row["roi"] = row["prevented_total"] / k
        base_beds = demand_from_cases([row[f"base_{h}w"] for h in HORIZONS])["hospital_beds_required"]
        after_beds = demand_from_cases([row[f"after_{h}w"] for h in HORIZONS])["hospital_beds_required"]
        base_sal = demand_from_cases([row[f"base_{h}w"] for h in HORIZONS])["saline_bags_needed"]
        after_sal = demand_from_cases([row[f"after_{h}w"] for h in HORIZONS])["saline_bags_needed"]
        row["beds_saved_peak"] = int(base_beds.max() - after_beds.max())
        row["saline_saved_total"] = int(base_sal.sum() - after_sal.sum())
        rows.append(row)
    res = pd.DataFrame(rows)
    if not res.empty:
        res = res.sort_values("roi", ascending=False).reset_index(drop=True)
        res["roi_rank"] = np.arange(1, len(res) + 1)
    return res, roi, crews


# ----------------------------------------------------------------------------
# 4. Dispatch notices (templates, offline)
# ----------------------------------------------------------------------------
def _n(v, lang, d=0):
    return fmt_num(v, lang, d)


def compose_notice(row, ward_info, transfers, week_txt, lang):
    """row: allocated ward (namedtuple). ward_info: ward row from route_overflow."""
    ward, city = ward_label(row.ward_id, lang), city_label(row.city, lang)
    tier = tier_name(row.tier, lang, short=True)
    week_txt = to_bn_digits(str(week_txt)) if lang == "bn" else str(week_txt)
    cases = _n(row.predicted, lang, 0)
    out_t = transfers[transfers["from_ward"] == row.ward_id] if not transfers.empty else transfers
    in_t = transfers[transfers["to_ward"] == row.ward_id] if not transfers.empty else transfers
    deficit_bits = []
    if row.saline_deficit > 0:
        deficit_bits.append(("স্যালাইন" if lang == "bn" else "saline", _n(row.saline_deficit, lang)))
    if row.kits_deficit > 0:
        deficit_bits.append(("কিট" if lang == "bn" else "kits", _n(row.kits_deficit, lang)))
    bed_short = int(ward_info.net_deficit)

    if lang == "bn":
        sms = (
            f"ডেঙ্গু ডিসপ্যাচ: {ward} ({city}), {week_txt} সপ্তাহে প্রায় {cases} জন রোগী, ঝুঁকি {tier}। "
            f"স্যালাইন {_n(row.saline_allocated, lang)}/{_n(row.saline_required, lang)}, "
            f"কিট {_n(row.kits_allocated, lang)}/{_n(row.kits_required, lang)}, "
            f"বেড {_n(row.beds_required, lang)}/{_n(ward_info.capacity, lang)}। "
            f"স্প্রে দল: {_n(row.crews_assigned, lang)}।"
        )
        if deficit_bits:
            sms += " ঘাটতি: " + ", ".join(f"{a} {b}" for a, b in deficit_bits) + "।"
        lines = [
            f"*ডেঙ্গু ডিসপ্যাচ নোটিশ*", f"ওয়ার্ড: {ward} ({city})",
            f"পূর্বাভাস: {week_txt} সপ্তাহে প্রায় {cases} জন রোগী, *{tier_name(row.tier, lang)}*",
            "", "*সরবরাহ (বরাদ্দ / প্রয়োজন)*",
            f"• স্যালাইন: {_n(row.saline_allocated, lang)} / {_n(row.saline_required, lang)}",
            f"• ডায়াগনস্টিক কিট: {_n(row.kits_allocated, lang)} / {_n(row.kits_required, lang)}",
            f"• হাসপাতাল বেড: প্রয়োজন {_n(row.beds_required, lang)}, ধারণক্ষমতা {_n(ward_info.capacity, lang)}",
            f"• স্প্রে দল: {_n(row.crews_assigned, lang)} (প্রয়োজন {_n(row.crews_needed, lang)})",
        ]
        for r in out_t.itertuples():
            lines.append(f"→ {_n(r.patients, lang)} জন রোগী পাঠান: {ward_label(r.to_ward, lang)}")
        for r in in_t.itertuples():
            lines.append(f"← {_n(r.patients, lang)} জন রোগী আসবে: {ward_label(r.from_ward, lang)}")
        if bed_short > 0:
            lines.append(f"⚠ শহরে জায়গা নেই: {_n(bed_short, lang)} জন রোগীর বেডের ঘাটতি")
        for a, b in deficit_bits:
            lines.append(f"⚠ ঘাটতি: {a} {b}")
    else:
        sms = (
            f"Dengue dispatch: {ward} ({city}), ~{cases} cases in week of {week_txt}, risk {tier}. "
            f"Saline {_n(row.saline_allocated, lang)}/{_n(row.saline_required, lang)}, "
            f"kits {_n(row.kits_allocated, lang)}/{_n(row.kits_required, lang)}, "
            f"beds {_n(row.beds_required, lang)}/{_n(ward_info.capacity, lang)}. "
            f"Spray crews: {_n(row.crews_assigned, lang)}."
        )
        if deficit_bits:
            sms += " Deficit: " + ", ".join(f"{a} {b}" for a, b in deficit_bits) + "."
        lines = [
            "*Dengue dispatch notice*", f"Ward: {ward} ({city})",
            f"Forecast: ~{cases} cases in week of {week_txt}, *{tier_name(row.tier, lang)}*",
            "", "*Supplies (allocated / required)*",
            f"• Saline bags: {_n(row.saline_allocated, lang)} / {_n(row.saline_required, lang)}",
            f"• Diagnostic kits: {_n(row.kits_allocated, lang)} / {_n(row.kits_required, lang)}",
            f"• Hospital beds: need {_n(row.beds_required, lang)}, capacity {_n(ward_info.capacity, lang)}",
            f"• Spray crews: {_n(row.crews_assigned, lang)} (needed {_n(row.crews_needed, lang)})",
        ]
        for r in out_t.itertuples():
            lines.append(f"→ Send {_n(r.patients, lang)} patient(s) to {ward_label(r.to_ward, lang)}")
        for r in in_t.itertuples():
            lines.append(f"← Expect {_n(r.patients, lang)} patient(s) from {ward_label(r.from_ward, lang)}")
        if bed_short > 0:
            lines.append(f"⚠ No room left in city: {_n(bed_short, lang)} patient(s) without a bed")
        for a, b in deficit_bits:
            lines.append(f"⚠ Deficit: {a} {b}")
    return {"sms": sms, "whatsapp": "\n".join(lines)}


BRIEF_CSS = """
body{font-family:"Noto Sans Bengali","Nirmala UI","Kalpurush","Segoe UI",system-ui,sans-serif;color:#0F1C2E;margin:24px;line-height:1.5}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:22px 0 6px}
.meta{color:#4A5A6A;font-size:13px;margin-bottom:14px}
.kpis{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}
.kpi{border:1px solid #C9D6E3;border-radius:8px;padding:8px 12px;min-width:120px}
.kpi b{display:block;font-size:20px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid #C9D6E3;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#EEF4FB}.crit{background:#7A0C1E;color:#fff}.high{background:#FDE8E0}.med{background:#FFF4D6}
.warn{border-left:4px solid #B3380F;background:#FDE8E0;padding:6px 10px;margin:4px 0}
.small{font-size:12px;color:#4A5A6A;margin-top:18px}
@media print{body{margin:10mm}.noprint{display:none}}
"""


def build_brief_html(city, f_city, w_city, transfers_city, summary, week_txt, stock_pct, lang):
    """Printable commissioner brief for one city. Self-contained: no external assets."""
    e = html_lib.escape
    T = (lambda bn, en: bn if lang == "bn" else en)
    week_txt = to_bn_digits(str(week_txt)) if lang == "bn" else str(week_txt)
    cls = {"Critical": "crit", "High": "high", "Medium": "med", "Low": ""}
    rows = []
    wmap = w_city.set_index("ward_id")
    for r in f_city.itertuples():
        wi = wmap.loc[r.ward_id]
        flag = {"ok": "", "deficit": T("ঘাটতি", "Deficit"), "critical": T("গুরুতর ঘাটতি", "Critical deficit")}[r.supply_status]
        rows.append(
            f"<tr><td>{_n(r.priority_rank, lang)}</td><td>{e(ward_label(r.ward_id, lang))}</td>"
            f"<td class='{cls[r.tier]}'>{e(tier_name(r.tier, lang, short=True))}</td>"
            f"<td>{_n(r.predicted, lang, 1)}</td>"
            f"<td>{_n(r.saline_allocated, lang)} / {_n(r.saline_required, lang)}</td>"
            f"<td>{_n(r.kits_allocated, lang)} / {_n(r.kits_required, lang)}</td>"
            f"<td>{_n(r.beds_required, lang)} / {_n(wi.capacity, lang)}</td>"
            f"<td>{_n(r.crews_assigned, lang)}</td><td>{e(flag)}</td></tr>"
        )
    moves = "".join(
        f"<tr><td>{e(ward_label(t.from_ward, lang))}</td><td>{e(ward_label(t.to_ward, lang))}</td><td>{_n(t.patients, lang)}</td></tr>"
        for t in transfers_city.itertuples()
    ) or f"<tr><td colspan='3'>{T('কোনো স্থানান্তর দরকার নেই', 'No transfers needed')}</td></tr>"
    warns = ""
    if summary["wards_deficit"]:
        warns += f"<div class='warn'>{T('সরবরাহ ঘাটতি: ', 'Supply deficit: ')}{_n(summary['wards_deficit'], lang)} {T('টি ওয়ার্ডে চাহিদা পুরো মেটেনি', 'ward(s) not fully supplied')}</div>"
    if int(w_city["net_deficit"].sum()) > 0:
        warns += f"<div class='warn'>{T('শহরব্যাপী বেড ঘাটতি: ', 'City-wide bed shortage: ')}{_n(int(w_city['net_deficit'].sum()), lang)} {T('জন রোগী', 'patient(s)')}</div>"
    title = T(f"ডেঙ্গু কমিশনার ব্রিফ: {city_label(city, lang)}", f"Dengue commissioner brief: {city_label(city, lang)}")
    head = [T("ক্রম", "Rank"), T("ওয়ার্ড", "Ward"), T("ঝুঁকি", "Risk"), T("রোগী/সপ্তাহ", "Cases/wk"),
            T("স্যালাইন (বরাদ্দ/প্রয়োজন)", "Saline (alloc/req)"), T("কিট (বরাদ্দ/প্রয়োজন)", "Kits (alloc/req)"),
            T("বেড (প্রয়োজন/ক্ষমতা)", "Beds (need/cap)"), T("স্প্রে দল", "Crews"), T("অবস্থা", "Status")]
    th = "".join(f"<th>{e(h)}</th>" for h in head)
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{e(title)}</title>
<style>{BRIEF_CSS}</style></head><body>
<h1>{e(title)}</h1>
<div class="meta">{T('পূর্বাভাস সপ্তাহ', 'Forecast week')}: {e(week_txt)} · {T('আঞ্চলিক স্টক', 'Regional stock')}: {_n(stock_pct, lang)}%</div>
<div class="kpis">
<div class="kpi">{T('স্যালাইন', 'Saline')}<b>{_n(summary['saline_allocated'], lang)} / {_n(summary['saline_required'], lang)}</b></div>
<div class="kpi">{T('কিট', 'Kits')}<b>{_n(summary['kits_allocated'], lang)} / {_n(summary['kits_required'], lang)}</b></div>
<div class="kpi">{T('বেড ব্যবহার', 'Bed utilisation')}<b>{_n(100 * w_city['beds_required'].sum() / max(w_city['capacity'].sum(), 1), lang)}%</b></div>
<div class="kpi">{T('স্প্রে দল', 'Spray crews')}<b>{_n(summary['crews_assigned'], lang)} / {_n(summary['crews_needed'], lang)}</b></div>
</div>
{warns}
<h2>{T('ওয়ার্ডভিত্তিক বরাদ্দ (অগ্রাধিকার ক্রমে)', 'Ward allocation (priority order)')}</h2>
<table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>{T('বেড ওভারফ্লো স্থানান্তর (একই শহরের ভেতরে)', 'Bed overflow transfers (inside this city)')}</h2>
<table><thead><tr><th>{T('থেকে', 'From')}</th><th>{T('যেখানে', 'To')}</th><th>{T('রোগী', 'Patients')}</th></tr></thead><tbody>{moves}</tbody></table>
<p class="small">{T('পূর্বাভাস Phase 1 মডেলের। বেড ধারণক্ষমতা ও দলের প্রয়োজন অনুমান-ভিত্তিক; বাস্তব তথ্য পেলে বদলাতে হবে। এই ব্রিফ সম্পূর্ণ অফলাইনে তৈরি।', 'Forecast from the Phase 1 model. Bed capacity and crew need are assumptions; replace with real data. Generated fully offline.')}</p>
<p class="noprint"><button onclick="window.print()">{T('প্রিন্ট / PDF', 'Print / PDF')}</button></p>
</body></html>"""


def write_exports(out_dir, notices, briefs):
    """notices: {name: text}; briefs: {name: html}. Returns written paths."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, text in {**notices, **briefs}.items():
        p = os.path.join(out_dir, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        paths.append(p)
    return paths
