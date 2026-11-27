"""Two roles: viewer (default, read-only) and admin (can change settings and send).

Credentials (email + password): Streamlit secrets ADMIN_EMAIL / ADMIN_PASSWORD, or env
DENGUE_ADMIN_EMAIL / DENGUE_ADMIN_PASSWORD, else the demo defaults below. Change them
before deploying. The role lives in the server-side
session, so a viewer cannot reach admin widgets (they are never rendered for them).
This is a simple access gate for a prototype, not full user management.
"""
import hmac
import os
import time

import streamlit as st

from logo import LOGO_SVG

DEFAULT_EMAIL = "admin@dengue.local"
DEFAULT_PASSWORD = "admin123"
MAX_TRIES = 5

T = {
    "title": {"bn": "অ্যাডমিন লগইন", "en": "Admin login"},
    "welcome": {"bn": "আবার স্বাগতম", "en": "Welcome back"},
    "sub": {"bn": "সেটিং বদলাতে ও সতর্কবার্তা পাঠাতে সাইন ইন করুন", "en": "Sign in to change settings and send alerts"},
    "email": {"bn": "ইমেইল", "en": "Email address"},
    "pw": {"bn": "পাসওয়ার্ড", "en": "Password"},
    "pw_ph": {"bn": "আপনার পাসওয়ার্ড লিখুন", "en": "Enter your password"},
    "go": {"bn": "সাইন ইন →", "en": "Sign in →"},
    "viewer_note": {"bn": "অ্যাডমিন না হলে সব পেজ শুধু দেখা যাবে।", "en": "Without an admin account every page stays view-only."},
    "bad": {"bn": "ইমেইল বা পাসওয়ার্ড ভুল।", "en": "Wrong email or password."},
    "locked": {"bn": "অনেকবার ভুল হয়েছে। পেজ রিফ্রেশ করে আবার চেষ্টা করুন।", "en": "Too many attempts. Refresh the page and try again."},
    "viewer": {"bn": "দর্শক (শুধু দেখা)", "en": "Viewer (read-only)"},
    "admin": {"bn": "অ্যাডমিন", "en": "Admin"},
    "logout": {"bn": "লগআউট", "en": "Log out"},
    "default_pw": {"bn": "সতর্কতা: ডিফল্ট ইমেইল/পাসওয়ার্ড চলছে। ডিপ্লয়ের আগে ADMIN_EMAIL ও ADMIN_PASSWORD সিক্রেটে নতুন মান দিন।",
                   "en": "Warning: default email/password in use. Set ADMIN_EMAIL and ADMIN_PASSWORD in secrets before deploying."},
    "h_brand": {"bn": "ডেঙ্গু আগাম সতর্কতা", "en": "Dengue Early-Warning"},
    "h_title1": {"bn": "আপনার ওয়ার্ডভিত্তিক", "en": "Your ward-level"},
    "h_title2": {"bn": "ডেঙ্গু কমান্ড সেন্টার", "en": "dengue command centre"},
    "h_text": {"bn": "পূর্বাভাস, সরবরাহ বরাদ্দ, হাসপাতালের বেড ও স্প্রে দলের পরিকল্পনা এক জায়গায়। ২ থেকে ৪ সপ্তাহ আগেই ব্যবস্থা নিন।",
               "en": "Forecasts, supply allocation, hospital beds and spray-crew planning in one place. Act 2 to 4 weeks ahead."},
    "h_s1": {"bn": "ওয়ার্ড", "en": "WARDS"},
    "h_s2": {"bn": "শহর", "en": "CITIES"},
    "h_s3": {"bn": "সপ্তাহ আগাম", "en": "WEEKS AHEAD"},
}


def _t(key, lang):
    return T[key][lang]


def _secret(name, env, default):
    try:
        v = st.secrets.get(name)
    except Exception:
        v = None
    return str(v or os.environ.get(env) or default)


def _configured_password():
    return _secret("ADMIN_PASSWORD", "DENGUE_ADMIN_PASSWORD", DEFAULT_PASSWORD)


def _configured_email():
    return _secret("ADMIN_EMAIL", "DENGUE_ADMIN_EMAIL", DEFAULT_EMAIL).strip().lower()


def using_default_password():
    """True while the demo defaults are still active (email or password)."""
    return _configured_password() == DEFAULT_PASSWORD or _configured_email() == DEFAULT_EMAIL


def is_admin():
    return st.session_state.get("role") == "admin"


LOGIN_CSS = """<style>
.st-key-login-card{background:#fff;border:1px solid #C9D6E3 !important;border-radius:18px;padding:28px 30px 20px;
  box-shadow:0 10px 30px rgba(11,37,69,.10);}
.lg-welcome{font-size:1.9rem;font-weight:700;text-align:center;margin:0;color:#0F1C2E;line-height:1.3}
.lg-sub{text-align:center;color:#4A5A6A;margin:4px 0 14px 0}
.lg-note{text-align:center;color:#4A5A6A;font-size:.92rem;margin-top:10px}
.lg-hero{border-radius:18px;padding:34px 30px;min-height:430px;color:#fff;
  background:linear-gradient(160deg,#0B2545 0%,#13518F 60%,#1F78C8 100%);
  display:flex;flex-direction:column;justify-content:center;gap:14px}
.lg-brand{display:flex;align-items:center;gap:12px;font-weight:700;font-size:1.25rem}
.lg-brand svg{width:48px;height:48px;flex-shrink:0}
.lg-hero h2{margin:8px 0 0 0;font-size:2.1rem;line-height:1.25;color:#fff;font-weight:800}
.lg-hero h2 span{color:#FFB703}
.lg-hero p{margin:0;color:#D6E6F7;font-size:1.02rem;line-height:1.65;max-width:34rem}
.lg-stats{display:flex;gap:28px;margin-top:14px;padding-top:16px;border-top:1px solid rgba(255,255,255,.25)}
.lg-stats b{display:block;font-size:1.6rem;color:#fff}
.lg-stats small{color:#BFD6EE;letter-spacing:.06em;font-size:.78rem}
@media (max-width:640px){.lg-hero{min-height:0;padding:24px 20px}.lg-hero h2{font-size:1.6rem}}
</style>"""


def _hero_html(lang):
    nums = ("৬০", "৫", "২-৪") if lang == "bn" else ("60", "5", "2-4")
    return (
        f"<div class='lg-hero'>"
        f"<div class='lg-brand'>{LOGO_SVG}<span>{_t('h_brand', lang)}</span></div>"
        f"<h2>{_t('h_title1', lang)}<br><span>{_t('h_title2', lang)}</span></h2>"
        f"<p>{_t('h_text', lang)}</p>"
        f"<div class='lg-stats'>"
        f"<div><b>{nums[0]}</b><small>{_t('h_s1', lang)}</small></div>"
        f"<div><b>{nums[1]}</b><small>{_t('h_s2', lang)}</small></div>"
        f"<div><b>{nums[2]}</b><small>{_t('h_s3', lang)}</small></div>"
        f"</div></div>"
    )


def login_page(lang):
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    left, right = st.columns([1.15, 1], gap="large", vertical_alignment="center")
    with left:
        st.markdown(_hero_html(lang), unsafe_allow_html=True)
    with right:
        with st.container(border=True, key="login-card"):
            st.markdown(f"<h2 class='lg-welcome'>{_t('welcome', lang)}</h2>"
                        f"<p class='lg-sub'>{_t('sub', lang)}</p>", unsafe_allow_html=True)
            tries = st.session_state.get("_login_tries", 0)
            if tries >= MAX_TRIES:
                st.error(_t("locked", lang))
                return
            with st.form("admin_login", border=False):
                email = st.text_input(_t("email", lang), placeholder="you@example.com")
                pw = st.text_input(_t("pw", lang), type="password", placeholder=_t("pw_ph", lang))
                ok = st.form_submit_button(_t("go", lang), type="primary", width="stretch")
            if ok:
                good_email = hmac.compare_digest(email.strip().lower().encode(), _configured_email().encode())
                good_pw = hmac.compare_digest(pw.encode(), _configured_password().encode())
                if good_email and good_pw:  # both are always checked, so timing does not reveal which was wrong
                    st.session_state["role"] = "admin"
                    st.session_state["admin_email"] = email.strip().lower()
                    st.session_state["_login_tries"] = 0
                    st.rerun()
                else:
                    st.session_state["_login_tries"] = tries + 1
                    time.sleep(0.6)  # slow down guessing
                    st.error(_t("bad", lang))
            st.markdown(f"<p class='lg-note'>{_t('viewer_note', lang)}</p>", unsafe_allow_html=True)


def role_chip(lang):
    """Small role badge for the header; admin also gets a logout button."""
    if is_admin():
        st.markdown(f"<span class='risk-pill' style='background:#FFB703;color:#0B2545;border:1.5px solid #fff;"
                    f"padding:4px 10px;font-size:.92rem'>🔧 {_t('admin', lang)}</span>", unsafe_allow_html=True)
        if st.button(_t("logout", lang), key="logout_btn"):
            st.session_state.pop("role", None)
            st.rerun()
        if using_default_password():
            st.markdown(f"<span style='color:#FFD166;font-size:.85rem'>{_t('default_pw', lang)}</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span class='risk-pill' style='background:#E3EEFA;color:#0B2545;border:1.5px solid #C9D6E3;"
                    f"padding:4px 10px;font-size:.92rem'>👁 {_t('viewer', lang)}</span>", unsafe_allow_html=True)
