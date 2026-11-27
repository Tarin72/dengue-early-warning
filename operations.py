"""Operations page for city corporations.

1. Rank High/Critical wards from the model forecast.
2. Build a 2-week spray / cleanup / follow-up schedule under a team-capacity limit.
3. For High/Critical wards, compose Bangla (or English) SMS + WhatsApp alerts with a
   checklist for the councillor and for residents. Sending is SIMULATED (console +
   outbox) so there are no API calls and no cost; a WhatsApp click-to-chat link is
   offered for a real hand-off.

All text is template-based (no LLM): zero token cost, deterministic, reviewable.
Medical wording follows the usual DGHS dengue advice; have a native Bangla speaker
and a health officer review it before real use.
"""
import html as html_lib
import urllib.parse
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

import auth
import settings_store as store

from i18n import city_label, fmt_num, tier_name, to_bn_digits, ward_label
from styles import risk_badge_html

WEEK = pd.Timedelta(weeks=1)
ALERT_TIERS = ("High", "Critical")
TIER_ORDER = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
OFF_WEEKDAY = 4          # Friday (Monday = 0) is the weekly holiday: no field work
HORIZON_DAYS = 14        # 2-week schedule

POOL_OF = {"spray": "spray", "cleanup": "cleanup", "inspect": "cleanup"}

DAY_NAMES = {
    "bn": ["সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার", "শুক্রবার", "শনিবার", "রবিবার"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}

S = {
    "page_title": {"bn": "কর্মপরিকল্পনা ও সতর্কবার্তা", "en": "Action plan & alerts"},
    "intro": {
        "bn": "উচ্চ ও অতি উচ্চ ঝুঁকির ওয়ার্ডগুলো অগ্রাধিকার অনুযায়ী সাজিয়ে সিটি কর্পোরেশনের স্প্রে ও পরিষ্কার দলের ২ সপ্তাহের সূচি এবং কাউন্সিলর ও বাসিন্দাদের সতর্কবার্তা তৈরি করা হয়েছে। ভিত্তি: {h} সপ্তাহ পরের পূর্বাভাস ({wk})।",
        "en": "High and Critical wards are ranked by priority, then turned into a 2-week spray and cleanup schedule for the city corporation plus alerts for councillors and residents. Based on the {h}-week forecast ({wk}).",
    },
    "no_data": {"bn": "এই শহরের জন্য পূর্বাভাসের ডেটা নেই।", "en": "No forecast data for this city."},
    "no_risk": {
        "bn": "এই সময়ে কোনো ওয়ার্ডে উচ্চ বা অতি উচ্চ ঝুঁকি নেই। নিয়মিত নজরদারি চালিয়ে যান।",
        "en": "No ward is at High or Critical risk for this window. Keep routine surveillance.",
    },
    "settings": {"bn": "দলের সক্ষমতা", "en": "Team capacity"},
    "spray_teams": {"bn": "স্প্রে দল (সংখ্যা)", "en": "Spray teams"},
    "clean_teams": {"bn": "পরিষ্কার দল (সংখ্যা)", "en": "Cleanup teams"},
    "per_team": {"bn": "প্রতি দল দিনে কয়টি ওয়ার্ড", "en": "Wards per team per day"},
    "start": {"bn": "কাজ শুরুর তারিখ", "en": "Start date"},
    "inc_med": {"bn": "মাঝারি ঝুঁকির ওয়ার্ডও যোগ করুন (প্রতিরোধমূলক পরিষ্কার)", "en": "Also include Medium wards (preventive cleanup)"},
    "m_crit": {"bn": "অতি উচ্চ ঝুঁকি", "en": "Critical wards"},
    "m_high": {"bn": "উচ্চ ঝুঁকি", "en": "High wards"},
    "m_tasks": {"bn": "সূচিতে কাজ", "en": "Scheduled tasks"},
    "m_left": {"bn": "সূচিতে ধরেনি", "en": "Not scheduled"},
    "rank_title": {"bn": "১. অগ্রাধিকার র‍্যাঙ্কিং", "en": "1. Priority ranking"},
    "sched_title": {"bn": "২. ২ সপ্তাহের স্প্রে ও পরিষ্কারের সূচি", "en": "2. Two-week spray & cleanup schedule"},
    "alert_title": {"bn": "৩. কাউন্সিলর ও বাসিন্দাদের সতর্কবার্তা", "en": "3. Councillor & resident alerts"},
    "c_rank": {"bn": "ক্রম", "en": "Rank"},
    "c_ward": {"bn": "ওয়ার্ড", "en": "Ward"},
    "c_risk": {"bn": "ঝুঁকি", "en": "Risk"},
    "c_pred": {"bn": "আনুমানিক রোগী/সপ্তাহ", "en": "Cases / week"},
    "c_range": {"bn": "৮০% সীমা", "en": "80% range"},
    "c_rain": {"bn": "বৃষ্টি (মিমি)", "en": "Rain (mm)"},
    "c_wl": {"bn": "জলাবদ্ধতা সূচক", "en": "Waterlogging"},
    "c_date": {"bn": "তারিখ", "en": "Date"},
    "c_spray": {"bn": "স্প্রে দল", "en": "Spray teams"},
    "c_clean": {"bn": "পরিষ্কার ও ফলো-আপ দল", "en": "Cleanup & follow-up teams"},
    "week": {"bn": "সপ্তাহ {n}", "en": "Week {n}"},
    "off": {"bn": "ছুটি (কাজ নেই)", "en": "Weekly holiday (no field work)"},
    "team": {"bn": "দল {n}", "en": "Team {n}"},
    "task_spray": {"bn": "স্প্রে", "en": "Spray"},
    "task_respray": {"bn": "পুনরায় স্প্রে", "en": "Re-spray"},
    "task_cleanup": {"bn": "ড্রেন ও জমা পানি পরিষ্কার", "en": "Drain & standing-water cleanup"},
    "task_inspect": {"bn": "ফলো-আপ পরিদর্শন", "en": "Follow-up inspection"},
    "left_warn": {
        "bn": "{n}টি কাজ ২ সপ্তাহের মধ্যে ধরানো যায়নি। দল বা প্রতি দলের ওয়ার্ড সংখ্যা বাড়ান, অথবা শুধু শীর্ষ ওয়ার্ডগুলোতে মনোযোগ দিন।",
        "en": "{n} task(s) did not fit into 2 weeks. Add teams or wards per team, or focus on the top wards.",
    },
    "dl_sched": {"bn": "সূচি ডাউনলোড (CSV)", "en": "Download schedule (CSV)"},
    "sched_cap": {
        "bn": "শুক্রবার ছুটি ধরা হয়েছে। ক্রম অনুযায়ী আগে অতি উচ্চ, তারপর উচ্চ ঝুঁকির ওয়ার্ড। প্রতিটি ওয়ার্ডে প্রথমে স্প্রে ও পরিষ্কার, ৭ দিন পরে ফলো-আপ (অতি উচ্চ ঝুঁকিতে পুনরায় স্প্রেও)।",
        "en": "Friday is a holiday. Critical wards come first, then High. Each ward gets spray + cleanup first and a follow-up 7 days later (Critical wards also get a re-spray).",
    },
    "msg_lang": {"bn": "বার্তার ভাষা", "en": "Message language"},
    "ward_pick": {"bn": "ওয়ার্ড বাছুন", "en": "Choose a ward"},
    "phone": {"bn": "কাউন্সিলরের হোয়াটসঅ্যাপ নম্বর (ঐচ্ছিক)", "en": "Councillor WhatsApp number (optional)"},
    "tab_c": {"bn": "কাউন্সিলরের জন্য", "en": "For the councillor"},
    "tab_r": {"bn": "বাসিন্দাদের জন্য", "en": "For residents"},
    "sms": {"bn": "এসএমএস (ছোট বার্তা)", "en": "SMS (short)"},
    "wa": {"bn": "হোয়াটসঅ্যাপ (চেকলিস্টসহ)", "en": "WhatsApp (with checklist)"},
    "chars": {"bn": "{c} অক্ষর, {s}টি এসএমএস", "en": "{c} characters, {s} SMS"},
    "open_wa": {"bn": "হোয়াটসঅ্যাপে খুলুন", "en": "Open in WhatsApp"},
    "sim_one": {"bn": "সিমুলেটেড পাঠান", "en": "Simulate send"},
    "sim_all": {"bn": "সব উচ্চ ও অতি উচ্চ ঝুঁকির ওয়ার্ডে সিমুলেটেড পাঠান", "en": "Simulate alerts for all High/Critical wards"},
    "sent_one": {"bn": "সিমুলেশন: বার্তা কনসোলে লেখা হয়েছে ও আউটবক্সে যোগ হয়েছে (আসলে পাঠানো হয়নি)।", "en": "Simulated: message printed to the console and added to the outbox (nothing was really sent)."},
    "sent_all": {"bn": "সিমুলেশন: {n}টি বার্তা আউটবক্সে যোগ হয়েছে (আসলে পাঠানো হয়নি)।", "en": "Simulated: {n} messages added to the outbox (nothing was really sent)."},
    "outbox": {"bn": "আউটবক্স (সিমুলেটেড)", "en": "Outbox (simulated)"},
    "dl_out": {"bn": "আউটবক্স ডাউনলোড (CSV)", "en": "Download outbox (CSV)"},
    "review": {
        "bn": "বার্তা টেমপ্লেট-ভিত্তিক (কোনো এআই খরচ নেই)। বাস্তবে পাঠানোর আগে একজন বাংলাভাষী ও স্বাস্থ্য কর্মকর্তা দিয়ে ভাষা ও চিকিৎসা-পরামর্শ যাচাই করুন।",
        "en": "Messages are template-based (no AI cost). Have a native Bangla speaker and a health officer review wording and medical advice before real use.",
    },
    "only_alert": {"bn": "সতর্কবার্তা শুধু উচ্চ বা অতি উচ্চ ঝুঁকির ওয়ার্ডের জন্য যায়।", "en": "Alerts are sent only for High or Critical wards."},
    "o_time": {"bn": "সময়", "en": "Time"},
    "o_ward": {"bn": "ওয়ার্ড", "en": "Ward"},
    "o_aud": {"bn": "প্রাপক", "en": "Audience"},
    "o_ch": {"bn": "মাধ্যম", "en": "Channel"},
    "o_chars": {"bn": "অক্ষর", "en": "Chars"},
    "o_status": {"bn": "অবস্থা", "en": "Status"},
    "o_text": {"bn": "বার্তা", "en": "Message"},
    "aud_c": {"bn": "কাউন্সিলর", "en": "Councillor"},
    "aud_r": {"bn": "বাসিন্দা", "en": "Residents"},
    "status_sim": {"bn": "সিমুলেটেড (পাঠানো হয়নি)", "en": "Simulated (not sent)"},
}


S["viewer"] = {
    "bn": "আপনি শুধু দেখতে পারবেন। দল ও সময়ের সেটিং অ্যাডমিন ঠিক করেন: স্প্রে দল {a}, পরিষ্কার দল {b}, প্রতি দল দিনে {p}টি ওয়ার্ড, শুরু {d}। (সর্বশেষ বদল: {t})",
    "en": "View-only. Team settings are controlled by the admin: {a} spray teams, {b} cleanup teams, {p} ward(s) per team per day, start {d}. (Last changed: {t})",
}


def s(key, lang, **kw):
    text = S[key][lang]
    return text.format(**kw) if kw else text


def _num(v, lang, d=0):
    return fmt_num(v, lang, d)


# ----------------------------------------------------------------------------
# 1. Ranking
# ----------------------------------------------------------------------------
def rank_wards(frame):
    """frame needs: ward_id, predicted, ci_low, ci_high, tier. Highest priority first."""
    out = frame.copy()
    out["_t"] = out["tier"].map(TIER_ORDER)
    sort_cols = ["_t", "predicted"] + (["waterlog"] if "waterlog" in out.columns else [])
    out = out.sort_values(sort_cols, ascending=False).drop(columns="_t").reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1)
    return out


# ----------------------------------------------------------------------------
# 2. Schedule
# ----------------------------------------------------------------------------
def _task_plan(tier):
    """(task_key, earliest_day, depends_on_task_key or None)."""
    if tier == "Critical":
        return [("spray", 0, None), ("cleanup", 0, None), ("respray", 7, "spray"), ("inspect", 7, "cleanup")]
    if tier == "High":
        return [("spray", 0, None), ("cleanup", 0, None), ("inspect", 7, "cleanup")]
    return [("cleanup", 7, None)]  # Medium: preventive only


def build_schedule(targets, start_date, spray_teams, cleanup_teams, per_team, horizon_days=HORIZON_DAYS):
    """Greedy capacity-aware scheduler. Returns (schedule_df, unscheduled_df).

    Pass 1 places first-visit tasks in priority order; pass 2 places follow-ups no
    earlier than 7 days after the task they follow. Capacity per pool per working day
    = teams * wards_per_team.
    """
    start = pd.Timestamp(start_date)
    cap = {"spray": int(spray_teams) * int(per_team), "cleanup": int(cleanup_teams) * int(per_team)}
    used = {}
    placed = {}
    rows, left = [], []

    def working(day):
        return (start + pd.Timedelta(days=day)).weekday() != OFF_WEEKDAY

    def place(pool, earliest):
        if cap[pool] <= 0:
            return None
        for day in range(max(earliest, 0), horizon_days):
            if not working(day):
                continue
            n = used.get((pool, day), 0)
            if n < cap[pool]:
                used[(pool, day)] = n + 1
                return day, n // max(int(per_team), 1) + 1
        return None

    def add(r, task, earliest):
        pool = POOL_OF["spray" if task in ("spray", "respray") else task]
        res = place(pool, earliest)
        if res is None:
            left.append({"ward_id": r.ward_id, "tier": r.tier, "rank": r.rank, "task": task})
            return
        day, team = res
        placed[(r.ward_id, task)] = day
        rows.append({
            "date": start + pd.Timedelta(days=day), "day_idx": day,
            "week": day // 7 + 1, "pool": pool, "team": team,
            "ward_id": r.ward_id, "tier": r.tier, "rank": r.rank, "task": task,
        })

    plans = {r.ward_id: _task_plan(r.tier) for r in targets.itertuples()}
    for r in targets.itertuples():                       # pass 1: first visits
        for task, earliest, dep in plans[r.ward_id]:
            if dep is None:
                add(r, task, earliest)
    for r in targets.itertuples():                       # pass 2: follow-ups
        for task, earliest, dep in plans[r.ward_id]:
            if dep is not None:
                base = placed.get((r.ward_id, dep))
                if base is None:
                    left.append({"ward_id": r.ward_id, "tier": r.tier, "rank": r.rank, "task": task})
                    continue
                add(r, task, max(earliest, base + 7))

    cols = ["date", "day_idx", "week", "pool", "team", "ward_id", "tier", "rank", "task"]
    sched = pd.DataFrame(rows, columns=cols)
    if not sched.empty:
        sched = sched.sort_values(["date", "pool", "team", "rank"]).reset_index(drop=True)
    return sched, pd.DataFrame(left, columns=["ward_id", "tier", "rank", "task"])


def task_label(task, lang):
    return s("task_" + task, lang)


def _first_date(sched, ward_id, tasks):
    if sched is None or sched.empty:
        return None
    m = sched[(sched["ward_id"] == ward_id) & (sched["task"].isin(tasks))]
    return None if m.empty else m["date"].min()


# ----------------------------------------------------------------------------
# 3. Messages
# ----------------------------------------------------------------------------
def _fmt_day(ts, lang):
    if ts is None or pd.isna(ts):
        return "শীঘ্রই জানানো হবে" if lang == "bn" else "to be announced"
    txt = f"{ts.day:02d}/{ts.month:02d} ({DAY_NAMES[lang][ts.weekday()]})"
    return to_bn_digits(txt) if lang == "bn" else txt


C_CHECK = {
    "bn": [
        "ওয়ার্ডের ড্রেন, খাল ও জলাবদ্ধ জায়গা চিহ্নিত করে সিটি কর্পোরেশনকে জানান",
        "স্প্রে ও পরিষ্কার দলের জন্য প্রবেশপথ ও স্থানীয় স্বেচ্ছাসেবক ঠিক রাখুন",
        "মাইকিং বা মসজিদের মাইকে বাসিন্দাদের সতর্ক করুন",
        "নির্মাণস্থল, পুরোনো টায়ার ও পরিত্যক্ত পাত্রের তালিকা করুন",
        "স্থানীয় ক্লিনিকে জ্বরের রোগীর খবর রাখুন, সন্দেহজনক ক্ষেত্রে হাসপাতালে পাঠান",
        "কাজ শেষ হলে সিটি কর্পোরেশনকে ফিরতি খবর দিন",
    ],
    "en": [
        "Mark blocked drains, canals and waterlogged spots and report them to the city corporation",
        "Keep access open and local volunteers ready for the spray and cleanup teams",
        "Warn residents by miking or mosque loudspeaker",
        "List construction sites, old tyres and abandoned containers",
        "Track fever cases at local clinics; refer suspected cases to hospital",
        "Report back to the city corporation when work is done",
    ],
}

R_CHECK = {
    "bn": [
        "ফুলের টব, বালতি, ড্রাম, পুরোনো টায়ার ও ডাবের খোসার জমা পানি ফেলে দিন (সপ্তাহে অন্তত একবার)",
        "পানি রাখার পাত্র ঢেকে রাখুন",
        "ফ্রিজ/এসির ট্রে এবং ছাদ-বারান্দার জমা পানি পরিষ্কার করুন",
        "এডিস মশা সাধারণত দিনে কামড়ায়: দিনেও মশারি বা মশা তাড়ানোর ব্যবস্থা নিন",
        "স্প্রে ও পরিষ্কারের দল এলে সহযোগিতা করুন ({spray_d})",
        "জ্বর, শরীর ব্যথা বা চোখের পেছনে ব্যথা হলে দেরি না করে ডাক্তার দেখান। প্যারাসিটামল ও প্রচুর তরল খান; আইবুপ্রোফেন বা অ্যাসপিরিন খাবেন না",
    ],
    "en": [
        "Empty standing water from flower pots, buckets, drums, old tyres and coconut shells (at least weekly)",
        "Keep water containers covered",
        "Clean fridge/AC trays and rooftop or balcony puddles",
        "Aedes mosquitoes usually bite by day: use nets or repellent during the day too",
        "Cooperate when the spray and cleanup teams arrive ({spray_d})",
        "If you have fever, body ache or pain behind the eyes, see a doctor early. Take paracetamol and plenty of fluids; avoid ibuprofen and aspirin",
    ],
}

WARNING = {
    "bn": "পেটে তীব্র ব্যথা, বারবার বমি, নাক-মাড়ি দিয়ে রক্ত বা অতিরিক্ত দুর্বলতা হলে সঙ্গে সঙ্গে হাসপাতালে যান।",
    "en": "Severe stomach pain, repeated vomiting, nose/gum bleeding or extreme weakness: go to hospital immediately.",
}


def compose_messages(row, sched, target_week, lang, city):
    """row: one ranked ward (namedtuple or Series). Returns dict of 4 messages."""
    ward = ward_label(row.ward_id, lang)
    full = tier_name(row.tier, lang)
    short = tier_name(row.tier, lang, short=True)
    spray_ts = _first_date(sched, row.ward_id, ["spray"])
    clean_ts = _first_date(sched, row.ward_id, ["cleanup"])
    insp_ts = _first_date(sched, row.ward_id, ["inspect"])
    spray_d, clean_d, insp_d = (_fmt_day(x, lang) for x in (spray_ts, clean_ts, insp_ts))
    mu, lo, hi = _num(row.predicted, lang, 0), _num(row.ci_low, lang, 0), _num(row.ci_high, lang, 0)
    wk = to_bn_digits(str(target_week)) if lang == "bn" else str(target_week)
    two_four = to_bn_digits("২-৪") if lang == "bn" else "2-4"
    city_txt = city_label(city, lang)

    if lang == "bn":
        c_sms = (
            f"ডেঙ্গু সতর্কতা: {ward}-এ ঝুঁকি {short}, {wk} সপ্তাহে প্রায় {mu} জন রোগীর আশঙ্কা। "
            f"স্প্রে {spray_d}, ড্রেন পরিষ্কার {clean_d}। মাইকিং ও স্বেচ্ছাসেবক সমন্বয় করুন।"
        )
        r_sms = (
            f"ডেঙ্গু সতর্কতা: {ward}-এ আগামী {two_four} সপ্তাহে ডেঙ্গুর ঝুঁকি {short}। "
            f"বাড়ির আশপাশের জমা পানি ফেলুন, পাত্র ঢেকে রাখুন, দিনেও মশারি ব্যবহার করুন। "
            f"জ্বর হলে দ্রুত ডাক্তার দেখান। স্প্রে: {spray_d}।"
        )
        c_head = (
            f"*ডেঙ্গু আগাম সতর্কতা*\nএলাকা: {ward} ({city_txt})\nঝুঁকি: *{full}*\n"
            f"পূর্বাভাস: {wk} সপ্তাহে আনুমানিক {mu} জন ডেঙ্গু রোগী (সম্ভাব্য {lo}–{hi})।\n"
            f"কারণ: গত কয়েক সপ্তাহের বৃষ্টি ও জলাবদ্ধতা।\n\n"
            f"*সিটি কর্পোরেশনের সূচি*\n• স্প্রে (লার্ভিসাইড/ফগিং): {spray_d}\n"
            f"• ড্রেন ও জমা পানি পরিষ্কার: {clean_d}\n• ফলো-আপ পরিদর্শন: {insp_d}\n\n"
            f"*কাউন্সিলরের করণীয় (চেকলিস্ট)*"
        )
        r_head = (
            f"*ডেঙ্গু সতর্কতা: {ward}*\nআগামী {two_four} সপ্তাহে আপনার এলাকায় ডেঙ্গুর ঝুঁকি *{full}*। "
            f"এখনই এই কাজগুলো করুন:"
        )
    else:
        c_sms = (
            f"Dengue alert: {ward} is {short} risk, about {mu} cases expected in week of {wk}. "
            f"Spray {spray_d}, drain cleanup {clean_d}. Please coordinate miking and volunteers."
        )
        r_sms = (
            f"Dengue alert: {ward} has {short} dengue risk in the next {two_four} weeks. "
            f"Empty standing water, cover containers, use a mosquito net even by day. "
            f"See a doctor early if you have fever. Spray: {spray_d}."
        )
        c_head = (
            f"*Dengue early warning*\nArea: {ward} ({city_txt})\nRisk: *{full}*\n"
            f"Forecast: about {mu} cases in the week of {wk} (likely {lo}-{hi}).\n"
            f"Driver: recent rainfall and waterlogging.\n\n"
            f"*City corporation schedule*\n• Spray (larvicide/fogging): {spray_d}\n"
            f"• Drain and standing-water cleanup: {clean_d}\n• Follow-up inspection: {insp_d}\n\n"
            f"*Councillor checklist*"
        )
        r_head = (
            f"*Dengue alert: {ward}*\nDengue risk in your area is *{full}* for the next {two_four} weeks. "
            f"Please do these now:"
        )

    c_list = "\n".join("☐ " + x for x in C_CHECK[lang])
    r_list = "\n".join("☐ " + x.format(spray_d=spray_d) for x in R_CHECK[lang])
    return {
        "councillor_sms": c_sms,
        "councillor_wa": f"{c_head}\n{c_list}",
        "resident_sms": r_sms,
        "resident_wa": f"{r_head}\n\n{r_list}\n\n⚠ {WARNING[lang]}",
    }


def sms_segments(text):
    """Bangla needs UCS-2: 70 chars in one SMS, 67 per part when concatenated."""
    n = len(text)
    if n == 0:
        return 0
    return 1 if n <= 70 else -(-n // 67)


def wa_link(text, phone=""):
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 11 and digits.startswith("01"):
        digits = "88" + digits
    base = f"https://wa.me/{digits}" if digits else "https://wa.me/"
    return f"{base}?text={urllib.parse.quote(text)}"


def _outbox():
    return st.session_state.setdefault("alert_outbox", [])


def simulate_send(ward_id, audience, channel, text, lang):
    """Console + outbox simulation. No network call."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[SIMULATED {channel.upper()} to {audience} of {ward_id}] {text}", flush=True)
    _outbox().append({
        "time": stamp, "ward": ward_label(ward_id, lang), "audience": audience,
        "channel": channel, "chars": len(text), "status": "simulated", "message": text,
    })


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
def _ranking_frame(artifact, df, city, issue_date, horizon):
    from src.preprocess import FEATURE_COLS, classify_risk_tier, predict_interval

    cs = df[(df["city"] == city) & (df["date"] == issue_date + 2 * WEEK)].dropna(subset=FEATURE_COLS)
    if cs.empty:
        return cs
    mu = np.clip(artifact["models"][horizon].predict(cs[FEATURE_COLS]), 0, None)
    lo, hi = predict_interval(mu, artifact["dispersion"][horizon])
    frame = pd.DataFrame({
        "ward_id": cs["ward_id"].values,
        "predicted": mu,
        "ci_low": np.asarray(lo, dtype=float),
        "ci_high": np.asarray(hi, dtype=float),
        "tier": [classify_risk_tier(v) for v in mu],
        "rain": cs["rainfall_sum_2_4w"].values,
        "waterlog": cs["water_logging_risk_index"].values,
    })
    return rank_wards(frame)


def _render_ranking(targets, lang):
    heads = [s(k, lang) for k in ("c_rank", "c_ward", "c_risk", "c_pred", "c_range", "c_rain", "c_wl")]
    th = "".join(f"<th>{html_lib.escape(h)}</th>" for h in heads)
    body = []
    for r in targets.itertuples():
        body.append(
            "<tr>"
            f"<td><span class='rank-tag'>{_num(r.rank, lang, 0)}</span></td>"
            f"<td><strong>{html_lib.escape(ward_label(r.ward_id, lang))}</strong></td>"
            f"<td>{risk_badge_html(r.tier, tier_name(r.tier, lang), compact=True)}</td>"
            f"<td>{_num(r.predicted, lang, 1)}</td>"
            f"<td>{_num(r.ci_low, lang, 1)} – {_num(r.ci_high, lang, 1)}</td>"
            f"<td>{_num(r.rain, lang, 1)}</td>"
            f"<td>{_num(r.waterlog, lang, 2)}</td>"
            "</tr>"
        )
    st.markdown(
        f"<div class='table-scroll'><table class='pri-table'><thead><tr>{th}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _cell(items, lang):
    if items.empty:
        return "—"
    lines = []
    for r in items.itertuples():
        task = task_label(r.task, lang)
        lines.append(
            f"<strong>{html_lib.escape(s('team', lang, n=_num(r.team, lang, 0)))}</strong>: "
            f"{html_lib.escape(ward_label(r.ward_id, lang))} "
            f"<span style='opacity:.8'>({html_lib.escape(task)})</span> "
            f"{risk_badge_html(r.tier, tier_name(r.tier, lang, short=True), compact=True)}"
        )
    return "<br>".join(lines)


def _render_schedule(sched, start_date, lang):
    start = pd.Timestamp(start_date)
    head = (
        f"<th>{html_lib.escape(s('c_date', lang))}</th>"
        f"<th>{html_lib.escape(s('c_spray', lang))}</th>"
        f"<th>{html_lib.escape(s('c_clean', lang))}</th>"
    )
    body = []
    for day in range(HORIZON_DAYS):
        ts = start + pd.Timedelta(days=day)
        if day % 7 == 0:
            body.append(
                f"<tr><td colspan='3' style='background:#EEF4FB;font-weight:700'>"
                f"{html_lib.escape(s('week', lang, n=_num(day // 7 + 1, lang, 0)))}</td></tr>"
            )
        label = _fmt_day(ts, lang)
        if ts.weekday() == OFF_WEEKDAY:
            body.append(
                f"<tr><td><strong>{label}</strong></td>"
                f"<td colspan='2' style='opacity:.75'>{html_lib.escape(s('off', lang))}</td></tr>"
            )
            continue
        d = sched[sched["day_idx"] == day] if not sched.empty else sched
        sp = d[d["pool"] == "spray"] if not d.empty else d
        cl = d[d["pool"] == "cleanup"] if not d.empty else d
        body.append(f"<tr><td><strong>{label}</strong></td><td>{_cell(sp, lang)}</td><td>{_cell(cl, lang)}</td></tr>")
    st.markdown(
        f"<div class='table-scroll'><table class='pri-table'><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _schedule_csv(sched, lang):
    out = pd.DataFrame({
        s("c_date", lang): sched["date"].dt.strftime("%Y-%m-%d"),
        "Weekday": sched["date"].dt.weekday.map(lambda i: DAY_NAMES[lang][i]),
        s("c_ward", lang): sched["ward_id"].map(lambda w: ward_label(w, lang)),
        "Team": sched["pool"].map(lambda p: s("c_spray" if p == "spray" else "c_clean", lang)) + " " + sched["team"].astype(str),
        "Task": sched["task"].map(lambda k: task_label(k, lang)),
        s("c_risk", lang): sched["tier"].map(lambda x: tier_name(x, lang)),
        s("c_rank", lang): sched["rank"],
    })
    return out.to_csv(index=False).encode("utf-8-sig")  # utf-8-sig so Excel shows Bangla


def _text_block(label, text, key, lang, phone="", with_link=False):
    st.markdown(f"**{label}**")
    height = 120 if label == s("sms", lang) else 330
    edited = st.text_area(label, value=text, height=height, key=key, label_visibility="collapsed",
                          disabled=not auth.is_admin())
    if label == s("sms", lang):
        st.caption(s("chars", lang, c=_num(len(edited), lang, 0), s=_num(sms_segments(edited), lang, 0)))
    elif with_link and auth.is_admin():
        st.link_button(s("open_wa", lang), wa_link(edited, phone))
    return edited


def _render_alerts(targets, sched, target_week, city, lang):
    alert_wards = targets[targets["tier"].isin(ALERT_TIERS)]
    if alert_wards.empty:
        st.info(s("only_alert", lang))
        return
    st.caption(s("only_alert", lang))
    c1, c2 = st.columns([2, 1])
    with c1:
        ward_id = st.selectbox(
            s("ward_pick", lang),
            list(alert_wards["ward_id"]),
            key="ops_ward",
            format_func=lambda w: f"#{_num(int(alert_wards.loc[alert_wards.ward_id == w, 'rank'].iloc[0]), lang, 0)}  "
                                  f"{ward_label(w, lang)} ({tier_name(alert_wards.loc[alert_wards.ward_id == w, 'tier'].iloc[0], lang, short=True)})",
        )
    with c2:
        mlang = st.radio(s("msg_lang", lang), ["bn", "en"], horizontal=True, key="ops_msg_lang",
                         format_func=lambda k: "বাংলা" if k == "bn" else "English")
    phone = st.text_input(s("phone", lang), key="ops_phone", placeholder="01XXXXXXXXX") if auth.is_admin() else ""

    row = next(alert_wards[alert_wards["ward_id"] == ward_id].itertuples())
    msgs = compose_messages(row, sched, target_week, mlang, city)
    kbase = f"{ward_id}_{mlang}_{target_week}"

    tab_c, tab_r = st.tabs([s("tab_c", lang), s("tab_r", lang)])
    for tab, aud, aud_key, sms_k, wa_k, use_phone in (
        (tab_c, "councillor", "aud_c", "councillor_sms", "councillor_wa", True),
        (tab_r, "resident", "aud_r", "resident_sms", "resident_wa", False),
    ):
        with tab:
            sms = _text_block(s("sms", lang), msgs[sms_k], f"{aud}_sms_{kbase}", lang)
            wa = _text_block(s("wa", lang), msgs[wa_k], f"{aud}_wa_{kbase}", lang,
                             phone=phone if use_phone else "", with_link=True)
            if auth.is_admin() and st.button(s("sim_one", lang), key=f"send_{aud}_{kbase}", type="primary"):
                simulate_send(ward_id, s(aud_key, "en"), "sms", sms, lang)
                simulate_send(ward_id, s(aud_key, "en"), "whatsapp", wa, lang)
                st.success(s("sent_one", lang))

    if auth.is_admin() and st.button(s("sim_all", lang), key=f"send_all_{city}_{target_week}"):
        n = 0
        for r in alert_wards.itertuples():
            m = compose_messages(r, sched, target_week, mlang, city)
            for aud_key, sms_k, wa_k in (("aud_c", "councillor_sms", "councillor_wa"), ("aud_r", "resident_sms", "resident_wa")):
                simulate_send(r.ward_id, s(aud_key, "en"), "sms", m[sms_k], lang)
                simulate_send(r.ward_id, s(aud_key, "en"), "whatsapp", m[wa_k], lang)
                n += 2
        st.success(s("sent_all", lang, n=_num(n, lang, 0)))

    outbox = _outbox() if auth.is_admin() else []
    if outbox:
        st.markdown(f"**{s('outbox', lang)}**")
        ob = pd.DataFrame(outbox)
        show = pd.DataFrame({
            s("o_time", lang): ob["time"], s("o_ward", lang): ob["ward"], s("o_aud", lang): ob["audience"],
            s("o_ch", lang): ob["channel"], s("o_chars", lang): ob["chars"],
            s("o_status", lang): s("status_sim", lang), s("o_text", lang): ob["message"],
        })
        st.dataframe(show, hide_index=True, width="stretch")
        st.download_button(s("dl_out", lang), show.to_csv(index=False).encode("utf-8-sig"),
                           file_name="alert_outbox.csv", mime="text/csv", key="dl_outbox")
    st.caption(s("review", lang))


def render_operations_page(artifact, df, selected_city, issue_date, horizon, lang):
    target_week = (issue_date + horizon * WEEK).date()
    st.subheader(s("page_title", lang))
    wk_txt = to_bn_digits(str(target_week)) if lang == "bn" else str(target_week)
    st.caption(s("intro", lang, h=_num(horizon, lang, 0), wk=wk_txt))

    ranking = _ranking_frame(artifact, df, selected_city, issue_date, horizon)
    if ranking.empty:
        st.info(s("no_data", lang))
        return

    cfg = store.load()
    default_start = (issue_date + WEEK).date()
    saved_start = default_start
    if cfg["ops_start_issue"] == str(issue_date.date()) and cfg["ops_start"]:
        try:
            saved_start = pd.Timestamp(cfg["ops_start"]).date()
        except (ValueError, TypeError):
            pass
    if auth.is_admin():
        with st.container(border=True):
            st.markdown(f"**{s('settings', lang)}**")
            c1, c2, c3, c4 = st.columns(4)
            spray_teams = int(c1.number_input(s("spray_teams", lang), 0, 50, int(cfg["ops_spray"]), key="ops_spray"))
            clean_teams = int(c2.number_input(s("clean_teams", lang), 0, 50, int(cfg["ops_clean"]), key="ops_clean"))
            per_team = int(c3.number_input(s("per_team", lang), 1, 6, int(cfg["ops_per"]), key="ops_per"))
            start_date = c4.date_input(s("start", lang), value=saved_start, key=f"ops_start_{issue_date.date()}")
            include_medium = st.checkbox(s("inc_med", lang), value=bool(cfg["ops_medium"]), key="ops_medium")
        patch = {}
        if (spray_teams, clean_teams, per_team, include_medium) != (
                int(cfg["ops_spray"]), int(cfg["ops_clean"]), int(cfg["ops_per"]), bool(cfg["ops_medium"])):
            patch.update({"ops_spray": spray_teams, "ops_clean": clean_teams, "ops_per": per_team, "ops_medium": include_medium})
        if start_date != saved_start:
            patch.update({"ops_start_issue": str(issue_date.date()), "ops_start": start_date.isoformat()})
        if patch:
            store.save(patch)
    else:
        spray_teams, clean_teams, per_team = int(cfg["ops_spray"]), int(cfg["ops_clean"]), int(cfg["ops_per"])
        include_medium, start_date = bool(cfg["ops_medium"]), saved_start
        d_txt = to_bn_digits(str(start_date)) if lang == "bn" else str(start_date)
        st.info(s("viewer", lang, a=_num(spray_teams, lang, 0), b=_num(clean_teams, lang, 0), p=_num(per_team, lang, 0),
                  d=d_txt, t=cfg["updated_at"] or "-"))

    tiers = list(ALERT_TIERS) + (["Medium"] if include_medium else [])
    targets = ranking[ranking["tier"].isin(tiers)].reset_index(drop=True)
    targets["rank"] = np.arange(1, len(targets) + 1)
    if targets.empty:
        st.success(s("no_risk", lang))
        return

    sched, left = build_schedule(targets, start_date, spray_teams, clean_teams, per_team)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(s("m_crit", lang), _num((targets["tier"] == "Critical").sum(), lang, 0))
    m2.metric(s("m_high", lang), _num((targets["tier"] == "High").sum(), lang, 0))
    m3.metric(s("m_tasks", lang), _num(len(sched), lang, 0))
    m4.metric(s("m_left", lang), _num(len(left), lang, 0))

    st.markdown(f"### {s('rank_title', lang)}")
    _render_ranking(targets, lang)

    st.markdown(f"### {s('sched_title', lang)}")
    st.caption(s("sched_cap", lang))
    if len(left):
        st.warning(s("left_warn", lang, n=_num(len(left), lang, 0)))
    _render_schedule(sched, start_date, lang)
    if not sched.empty:
        st.download_button(s("dl_sched", lang), _schedule_csv(sched, lang),
                           file_name="spray_cleanup_schedule.csv", mime="text/csv", key="dl_sched")

    st.markdown(f"### {s('alert_title', lang)}")
    _render_alerts(targets, sched, target_week, selected_city, lang)
