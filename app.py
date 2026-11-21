import os
import json
import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from src.preprocess import (FEATURE_COLS, classify_risk_tier, derive_features,
                            load_and_engineer_features, local_driver_effects, predict_interval)
from src.train import train_and_evaluate, HORIZONS, TIERS

st.set_page_config(page_title="Dengue Early-Warning | ডেঙ্গু আগাম সতর্কতা", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input { font-family: 'Hind Siliguri','Nirmala UI','Segoe UI',sans-serif; }
.block-container{padding-top:1.6rem;max-width:1200px}
.hero{border:1px solid #dcd6c6;background:#fff;border-radius:14px;padding:20px 26px;margin-bottom:14px}
.hero h1{color:#1b5e3a;margin:0 0 4px 0;font-size:1.75rem;font-weight:700}
.hero p{color:#4a5a52;margin:0;font-size:1.02rem}
.fc{background:#fff;border:1px solid #dcd6c6;border-radius:12px;padding:14px 18px;min-height:178px}
.fc-h{color:#5c6b63;font-size:.92rem;font-weight:500}
.fc-n{font-size:2.1rem;font-weight:700;color:#23312b;line-height:1.25}
.fc-n span{font-size:.95rem;font-weight:500;color:#5c6b63}
.fc-r{color:#5c6b63;font-size:.9rem}
.fc-a{color:#8a8f87;font-size:.85rem;margin-bottom:8px}
.badge{color:#fff;padding:4px 14px;border-radius:6px;font-weight:600;font-size:.95rem}
.act{background:#fff;border:1px solid #dcd6c6;border-radius:12px;padding:12px 18px;margin:14px 0 6px 0}
[data-testid="stMetric"]{background:#fff;border:1px solid #dcd6c6;border-radius:12px;padding:10px 16px}
.stTabs [data-baseweb="tab"]{font-weight:600;font-size:1rem}
[data-testid="stSidebar"]{border-right:1px solid #dcd6c6}
[data-testid="stSidebar"] h2{font-size:1.05rem;color:#1b5e3a}
</style>""", unsafe_allow_html=True)

# ---------------- ভাষা / language ----------------
TX = {
 "title": ("Urban Dengue Early-Warning System", "শহুরে ডেঙ্গু আগাম সতর্কতা ব্যবস্থা"),
 "subtitle": ("Ward-level forecasts of weekly dengue cases 2, 3 and 4 weeks ahead, built from rainfall, temperature and humidity lags and each ward's vulnerability.",
              "বৃষ্টি, তাপমাত্রা ও আর্দ্রতার আগের সপ্তাহের তথ্য এবং ওয়ার্ডের ঝুঁকি থেকে ২, ৩ ও ৪ সপ্তাহ আগে ওয়ার্ড অনুযায়ী ডেঙ্গুর পূর্বাভাস।"),
 "area": ("1. Area and forecast window", "১. এলাকা ও পূর্বাভাসের সময়"),
 "city": ("City", "শহর"), "ward": ("Ward", "ওয়ার্ড"),
 "issue": ("Last observed weather week", "সর্বশেষ আবহাওয়ার সপ্তাহ"),
 "horizon": ("Forecast horizon (weeks ahead)", "কত সপ্তাহ পরের পূর্বাভাস"),
 "info": ("Weather observed up to {t}. Forecasts are for the weeks of {a}, {b} and {c}. The 3- and 4-week models use older weather, so they are a little less accurate (see the Validation tab).",
          "{t} পর্যন্ত আবহাওয়া ধরা হয়েছে। পূর্বাভাস {a}, {b} ও {c} তারিখের সপ্তাহের। ৩ ও ৪ সপ্তাহের মডেল পুরনো আবহাওয়া ব্যবহার করে, তাই একটু কম নির্ভুল (ভ্যালিডেশন ট্যাব দেখুন)।"),
 "sim": ("2. Weather scenario", "২. আবহাওয়ার পরিস্থিতি"),
 "simcap": ("Change the observed weather to see how the forecast reacts. Defaults are the real values.",
            "আবহাওয়া বদলে দেখুন পূর্বাভাস কীভাবে বদলায়। শুরুতে আসল মান দেওয়া আছে।"),
 "r1": ("Rainfall, last observed week (mm)", "বৃষ্টি, সর্বশেষ সপ্তাহ (মিমি)"),
 "r2": ("Rainfall, 1 week earlier (mm)", "বৃষ্টি, ১ সপ্তাহ আগে (মিমি)"),
 "r3": ("Rainfall, 2 weeks earlier (mm)", "বৃষ্টি, ২ সপ্তাহ আগে (মিমি)"),
 "temp": ("Average temperature, last 3 weeks (°C)", "গড় তাপমাত্রা, গত ৩ সপ্তাহ (°সে)"),
 "hum": ("Relative humidity, last 3 weeks (%)", "আপেক্ষিক আর্দ্রতা, গত ৩ সপ্তাহ (%)"),
 "tab1": ("Forecast and drivers", "পূর্বাভাস ও কারণ"),
 "tab2": ("Ward risk heatmap", "ওয়ার্ড ঝুঁকির হিটম্যাপ"),
 "tab3": ("Validation", "ভ্যালিডেশন"),
 "fc_title": ("{h} weeks ahead · week of {d}", "{h} সপ্তাহ পরে · {d} তারিখের সপ্তাহ"),
 "unit": ("cases / week", "কেস / সপ্তাহ"),
 "range": ("80% range", "৮০% সম্ভাব্য সীমা"),
 "actual": ("Actual: {n}", "আসলে হয়েছিল: {n}"), "future": ("Future week", "ভবিষ্যৎ সপ্তাহ"),
 "act": ("What to do for the {h}-week forecast ({tier})", "{h} সপ্তাহের পূর্বাভাসে করণীয় ({tier})"),
 "drv": ("What is driving this forecast", "এই পূর্বাভাসের পেছনের কারণ"),
 "drv_t": ("Change in predicted cases compared with typical conditions ({w}, {h} weeks ahead)",
           "সাধারণ অবস্থার তুলনায় পূর্বাভাসিত কেসের পরিবর্তন ({w}, {h} সপ্তাহ পরে)"),
 "drv_x": ("Change in predicted cases per week", "সাপ্তাহিক কেসের পরিবর্তন"),
 "drv_cap": ("Each bar shows how much the model's forecast changes if that factor were at its typical (median) value and everything else stayed the same.",
             "প্রতিটি দণ্ড দেখায় ঐ কারণটি সাধারণ (মধ্যমান) অবস্থায় থাকলে মডেলের পূর্বাভাস কতটা বদলাত, বাকি সব একই ধরে।"),
 "up": ("Raises risk", "ঝুঁকি বাড়ায়"), "down": ("Lowers risk", "ঝুঁকি কমায়"),
 "Rainfall (lags 2–4w)": ("Rainfall (2–4 weeks earlier)", "বৃষ্টি (২–৪ সপ্তাহ আগের)"),
 "Temperature": ("Temperature", "তাপমাত্রা"), "Humidity": ("Humidity", "আর্দ্রতা"),
 "Water-logging risk": ("Water-logging risk", "জলাবদ্ধতার ঝুঁকি"),
 "Population density": ("Population density", "জনঘনত্ব"), "Sanitation": ("Sanitation", "স্যানিটেশন"),
 "hist": ("Rainfall and cases, last 52 weeks", "বৃষ্টি ও কেস, গত ৫২ সপ্তাহ"),
 "hist_rain": ("Rain in the 2–4 week window (mm)", "২–৪ সপ্তাহের বৃষ্টি (মিমি)"),
 "hist_cases": ("Weekly cases", "সাপ্তাহিক কেস"), "hist_y": ("Dengue cases", "ডেঙ্গু কেস"), "hist_y2": ("Rain (mm)", "বৃষ্টি (মিমি)"),
 "hm_t": ("{c}: ward by week forecast ({h} weeks ahead, issued {d})", "{c}: ওয়ার্ড ও সপ্তাহ অনুযায়ী পূর্বাভাস ({h} সপ্তাহ পরে, {d} তারিখে দেওয়া)"),
 "hm_x": ("Target week", "লক্ষ্য সপ্তাহ"), "hm_y": ("Ward", "ওয়ার্ড"), "hm_c": ("Cases / week", "কেস / সপ্তাহ"),
 "pri": ("Ward priority list for the week of {d}", "{d} তারিখের সপ্তাহের ওয়ার্ড অগ্রাধিকার তালিকা"),
 "c_ward": ("Ward", "ওয়ার্ড"), "c_pred": ("Predicted cases", "পূর্বাভাসিত কেস"), "c_lo": ("Low end", "সর্বনিম্ন"),
 "c_hi": ("High end", "সর্বোচ্চ"), "c_tier": ("Risk level", "ঝুঁকির স্তর"), "c_rain": ("Rain, 2–4 wk (mm)", "বৃষ্টি, ২–৪ সপ্তাহ (মিমি)"),
 "c_wl": ("Water-logging index", "জলাবদ্ধতা সূচক"), "c_pop": ("Density per km²", "জনঘনত্ব/বর্গকিমি"),
 "hm_cap": ("The heatmap uses real observed weather for the last 12 target weeks. The scenario sliders affect only the first tab.",
            "হিটম্যাপে শেষ ১২টি লক্ষ্য সপ্তাহের আসল আবহাওয়া ব্যবহার হয়েছে। স্লাইডার শুধু প্রথম ট্যাবে কাজ করে।"),
 "val_h": ("Chronological validation (2024–2025 held-out weeks)", "সময়ানুক্রমিক ভ্যালিডেশন (২০২৪–২০২৫ এর অদেখা সপ্তাহ)"),
 "val_sel": ("Horizon to validate (weeks)", "কোন সপ্তাহের পূর্বাভাস যাচাই হবে"),
 "val_cap": ("Trained on target weeks {tr}; tested on unseen weeks {te}. 80% range coverage on the test weeks: {c1}% (weeks with 3 or more predicted cases), {c0}% overall.",
             "প্রশিক্ষণ: {tr}; অদেখা পরীক্ষা: {te}। ৮০% সীমার কভারেজ: {c1}% (৩ বা বেশি কেস পূর্বাভাস এমন সপ্তাহে), সব মিলিয়ে {c0}%।"),
 "gap": ("Train vs test MAE gap", "ট্রেন ও টেস্ট MAE এর ব্যবধান"),
 "lowof": ("Little overfitting", "ওভারফিটিং কম"), "chkof": ("Check overfitting", "ওভারফিটিং যাচাই করুন"),
 "cm_t": ("Risk level: actual vs predicted (all wards)", "ঝুঁকির স্তর: আসল বনাম পূর্বাভাস (সব ওয়ার্ড)"),
 "cm_x": ("Predicted", "পূর্বাভাস"), "cm_y": ("Actual", "আসল"), "cm_c": ("Ward-weeks", "ওয়ার্ড-সপ্তাহ"),
 "rec_h": ("Share of each real risk level that the model caught", "প্রতিটি আসল ঝুঁকির স্তরের কত শতাংশ মডেল ধরতে পেরেছে"),
 "rec_a": ("Recall %", "ধরা পড়েছে %"), "rec_b": ("Share of real weeks %", "আসল সপ্তাহের অংশ %"),
 "al_r": ("High/Critical alert recall", "উচ্চ/সংকটজনক সতর্কতায় ধরা পড়ার হার"),
 "al_p": ("High/Critical alert precision", "উচ্চ/সংকটজনক সতর্কতার নির্ভুলতা"),
 "al_cap": ("Overall accuracy looks high because most weeks are Low. The alert numbers show how well real outbreaks are caught.",
            "বেশির ভাগ সপ্তাহ কম ঝুঁকির, তাই মোট নির্ভুলতা বেশি দেখায়। প্রকৃত প্রাদুর্ভাব কতটা ধরা পড়ছে তা সতর্কতার সংখ্যাগুলো দেখায়।"),
 "av_t": ("Actual vs predicted weekly cases, {h} weeks ahead ({w})", "সাপ্তাহিক কেস: আসল বনাম পূর্বাভাস, {h} সপ্তাহ পরে ({w})"),
 "av_int": ("80% range", "৮০% সীমা"), "av_a": ("Actual", "আসল"), "av_p": ("Predicted", "পূর্বাভাস"),
 "av_x": ("Week", "সপ্তাহ"), "av_y": ("Weekly cases", "সাপ্তাহিক কেস"),
 "mae": ("{w}: average error (MAE)", "{w}: গড় ত্রুটি (MAE)"), "rmse": ("{w}: RMSE", "{w}: RMSE (বড় ভুলের মাপ)"),
 "col_mae": ("MAE", "MAE (গড় ত্রুটি)"), "col_rmse": ("RMSE", "RMSE"), "col_r2": ("R²", "R²"),
 "col_acc": ("Risk-level accuracy %", "ঝুঁকির স্তরে নির্ভুলতা %"),
 "m_ridge": ("Ridge baseline", "রিজ বেসলাইন"), "m_hgb": ("Gradient boosting (Poisson), chosen model", "গ্রেডিয়েন্ট বুস্টিং (পয়সন), নির্বাচিত মডেল"),
 "to": (" to ", " থেকে "),
 "plan_t": ("Detailed action plan for {tier} risk ({h} weeks ahead)", "{tier} ঝুঁকির বিস্তারিত করণীয় ({h} সপ্তাহ পরের জন্য)"),
 "plan_o": ("For city corporation and health officers", "সিটি করপোরেশন ও স্বাস্থ্য কর্মকর্তাদের জন্য"),
 "plan_p": ("For residents", "বাসিন্দাদের জন্য"),
 "plan_n": ("This is general guidance only. Follow the national dengue guidelines (DGHS) and your city corporation's protocols, and see a doctor for any illness.",
            "এটি শুধু সাধারণ নির্দেশনা। স্বাস্থ্য অধিদপ্তরের (DGHS) জাতীয় ডেঙ্গু নির্দেশিকা ও সিটি করপোরেশনের নিয়ম মেনে চলুন, অসুস্থ হলে ডাক্তার দেখান।"),
 "listen": ("Listen to this forecast", "পূর্বাভাসটি শুনুন"),
 "novoice": ("No English voice found on this device.", "এই ডিভাইসে বাংলা কণ্ঠ পাওয়া যায়নি; Microsoft Edge ব্রাউজারে চেষ্টা করুন।"),
 "say": ("{w}. Forecast {h} weeks ahead: about {n} cases per week. Risk level: {tier}. {act}",
         "{w}। {h} সপ্তাহ পরের পূর্বাভাস: সপ্তাহে প্রায় {n}টি কেস। ঝুঁকির স্তর: {tier}। করণীয়: {act}"), "cw": ("cases/week", "কেস/সপ্তাহ"),
 "model": ("Model", "মডেল"),
}
TIER_BN = {"Low": "কম", "Medium": "মাঝারি", "High": "উচ্চ", "Critical": "সংকটজনক"}
TIER_ACTIONS = {
    "Low": ("Keep routine mosquito surveillance and weekly drain checks.", "নিয়মিত মশা নজরদারি ও সাপ্তাহিক ড্রেন পরিদর্শন চালিয়ে যান।"),
    "Medium": ("Send targeted larvicide teams to standing water and construction sites.", "জমা পানি ও নির্মাণস্থলে লক্ষ্যভিত্তিক লার্ভিসাইড টিম পাঠান।"),
    "High": ("Increase fogging and larviciding; warn local clinics to stock IV saline and NS1 kits.", "ফগিং ও লার্ভিসাইডিং বাড়ান; স্থানীয় ক্লিনিককে স্যালাইন ও NS1 কিট মজুতের সতর্কতা দিন।"),
    "Critical": ("Prepare hospital surge capacity, fog daily and clear waste immediately.", "হাসপাতালে অতিরিক্ত রোগীর প্রস্তুতি নিন, প্রতিদিন ফগিং করুন ও বর্জ্য দ্রুত সরান।"),
}

# ঝুঁকির স্তর অনুযায়ী বিস্তারিত করণীয় (সাধারণ জনস্বাস্থ্য নির্দেশনা; DGHS/সিটি করপোরেশনের নিয়ম প্রযোজ্য)
TIER_PLAN = {
 "Low": {
  "officers": (["Keep weekly larval surveys going in drains, construction sites and tyre stores.",
                "Finish drain cleaning and waste collection before the next heavy rain.",
                "Check that larvicide, spraying equipment and dengue test kits are in stock."],
               ["ড্রেন, নির্মাণস্থল ও টায়ারের দোকানে সাপ্তাহিক লার্ভা জরিপ চালিয়ে যান।",
                "পরবর্তী ভারী বৃষ্টির আগেই ড্রেন পরিষ্কার ও বর্জ্য অপসারণ শেষ করুন।",
                "লার্ভিসাইড, স্প্রে সরঞ্জাম ও ডেঙ্গু পরীক্ষার কিট মজুত আছে কিনা দেখুন।"]),
  "public": (["Empty and scrub flower pots, buckets, coolers and tyres once a week.",
              "Keep water storage containers tightly covered.",
              "Learn the symptoms: fever, severe headache, pain behind the eyes, body aches."],
             ["ফুলের টব, বালতি, কুলার ও টায়ারের পানি সপ্তাহে একবার ফেলে ঘষে পরিষ্কার করুন।",
              "পানি জমিয়ে রাখার পাত্র ভালোভাবে ঢেকে রাখুন।",
              "লক্ষণ চিনে রাখুন: জ্বর, তীব্র মাথাব্যথা, চোখের পেছনে ব্যথা, গা ব্যথা।"]),
 },
 "Medium": {
  "officers": (["Send larvicide teams to standing-water hotspots: blocked drains, construction sites, tyre dumps.",
                "Start door-to-door container checks in the most crowded parts of the ward.",
                "Brief local clinics on dengue case definition and NS1 testing in the first days of fever."],
               ["জমা পানির হটস্পটে (বন্ধ ড্রেন, নির্মাণস্থল, টায়ারের স্তূপ) লার্ভিসাইড টিম পাঠান।",
                "ওয়ার্ডের ঘনবসতিপূর্ণ এলাকায় বাড়ি বাড়ি পানির পাত্র পরীক্ষা শুরু করুন।",
                "স্থানীয় ক্লিনিকগুলোকে ডেঙ্গুর সংজ্ঞা ও জ্বরের প্রথম কয়েক দিনে NS1 পরীক্ষা সম্পর্কে অবহিত করুন।"]),
  "public": (["Empty water containers every 2 to 3 days; remove water collected around the home.",
              "Use window screens or mosquito nets, and repellent in the daytime.",
              "If fever lasts more than 2 days, see a doctor instead of waiting."],
             ["২–৩ দিন পরপর পানির পাত্র খালি করুন; বাড়ির আশপাশের জমা পানি সরান।",
              "জানালায় নেট বা মশারি ব্যবহার করুন, দিনেও মশা তাড়ানোর ক্রিম লাগান।",
              "জ্বর ২ দিনের বেশি থাকলে অপেক্ষা না করে ডাক্তার দেখান।"]),
 },
 "High": {
  "officers": (["Intensify larviciding and source reduction. Use fogging only as a supplement against adult mosquitoes, not a replacement.",
                "Alert clinics and hospitals to stock IV saline, NS1/IgM test kits and blood-count (platelet) monitoring.",
                "Clear waste and fix drainage or water-logging points in the ward within days."],
               ["লার্ভিসাইডিং ও উৎস ধ্বংস বাড়ান। ফগিং শুধু প্রাপ্তবয়স্ক মশার বিরুদ্ধে সম্পূরক হিসেবে করুন, মূল উপায় হিসেবে নয়।",
                "ক্লিনিক ও হাসপাতালকে স্যালাইন, NS1/IgM কিট এবং রক্তের প্লেটলেট পরীক্ষার প্রস্তুতি রাখতে সতর্ক করুন।",
                "ওয়ার্ডের বর্জ্য সরান এবং ড্রেনেজ বা জলাবদ্ধতার স্থানগুলো কয়েক দিনের মধ্যে ঠিক করুন।"]),
  "public": (["Aedes bites in the daytime, mostly morning and late afternoon: use nets, long sleeves and repellent.",
              "With fever, get tested early. Take paracetamol for fever and drink plenty of fluids.",
              "Do not take aspirin or ibuprofen (NSAIDs) for dengue fever."],
             ["এডিস মশা দিনে কামড়ায়, বিশেষ করে সকাল ও বিকেলে: মশারি, লম্বা হাতার জামা ও রিপেলেন্ট ব্যবহার করুন।",
              "জ্বর হলে তাড়াতাড়ি পরীক্ষা করান। জ্বরের জন্য প্যারাসিটামল খান ও প্রচুর তরল পান করুন।",
              "ডেঙ্গু জ্বরে অ্যাসপিরিন বা আইবুপ্রোফেন (NSAID) খাবেন না।"]),
 },
 "Critical": {
  "officers": (["Start a ward-level emergency response: daily larviciding, fogging and waste clearance.",
                "Prepare hospital surge capacity: extra beds, a dengue corner, IV saline and test kits.",
                "Use ward councillors, schools, mosques and loudspeakers for public warnings; report cases daily."],
               ["ওয়ার্ড পর্যায়ে জরুরি প্রতিক্রিয়া শুরু করুন: প্রতিদিন লার্ভিসাইডিং, ফগিং ও বর্জ্য অপসারণ।",
                "হাসপাতালে অতিরিক্ত বেড, ডেঙ্গু কর্নার, স্যালাইন ও পরীক্ষার কিটের প্রস্তুতি নিন।",
                "ওয়ার্ড কাউন্সিলর, স্কুল, মসজিদ ও মাইকের মাধ্যমে জনসতর্কতা দিন; প্রতিদিন রোগীর তথ্য জানান।"]),
  "public": (["Go to a hospital immediately for warning signs: severe belly pain, repeated vomiting, bleeding gums or nose, black stool, drowsiness or restlessness, difficulty breathing.",
              "Also follow every step for High risk: nets, repellent, early testing, paracetamol only.",
              "Check and empty every water container around the home today."],
             ["সতর্ক লক্ষণ দেখা দিলেই সঙ্গে সঙ্গে হাসপাতালে যান: তীব্র পেটব্যথা, বারবার বমি, মাড়ি বা নাক থেকে রক্তপাত, কালো পায়খানা, ঝিমুনি বা অস্থিরতা, শ্বাসকষ্ট।",
              "উচ্চ ঝুঁকির সব নিয়মও মানুন: মশারি, রিপেলেন্ট, দ্রুত পরীক্ষা, শুধু প্যারাসিটামল।",
              "আজই বাড়ির আশপাশের সব পানির পাত্র দেখে খালি করুন।"]),
 },
}
TIER_COLORS = {"Low": "#2e7d32", "Medium": "#c9a227", "High": "#e07b00", "Critical": "#b3261e"}

def speak_button(text, lang_code, label, no_voice):
    """ব্রাউজারের নিজস্ব Web Speech API দিয়ে পড়ে শোনায় — কোনো API কল বা খরচ নেই"""
    html = f"""
<div style="font-family:'Hind Siliguri','Nirmala UI','Segoe UI',sans-serif">
<button id="b" style="background:#1b5e3a;color:#fff;border:0;border-radius:8px;padding:8px 18px;font-size:15px;cursor:pointer">&#9654; {label}</button>
<span id="m" style="color:#8a5a00;font-size:13px;margin-left:10px"></span></div>
<script>
const text={json.dumps(text)}, lang={json.dumps(lang_code)}, nov={json.dumps(no_voice)};
const b=document.getElementById('b'), m=document.getElementById('m');
b.onclick=()=>{{
  const s=window.speechSynthesis; s.cancel();
  const u=new SpeechSynthesisUtterance(text); u.lang=lang;
  const v=s.getVoices().find(x=>x.lang.toLowerCase().replace('_','-').startsWith(lang.slice(0,2).toLowerCase()));
  if(v){{u.voice=v; m.textContent='';}} else {{m.textContent=nov;}}
  s.speak(u);
}};
</script>"""
    html = html.strip()
    if hasattr(st, "iframe"):          # নতুন Streamlit
        st.iframe(html, height=50)
    else:                              # পুরনো Streamlit
        components.html(html, height=50)


lang = st.sidebar.radio("Language / ভাষা", ["English", "বাংলা"], horizontal=True, key="lang")
L = 0 if lang == "English" else 1


BN_DIG = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
CITY_BN = {"Dhaka North": "ঢাকা উত্তর", "Dhaka South": "ঢাকা দক্ষিণ", "Chattogram": "চট্টগ্রাম",
           "Gazipur": "গাজীপুর", "Narayanganj": "নারায়ণগঞ্জ"}
CORP_BN = {"DNCC": "ডিএনসিসি", "DSCC": "ডিএসসিসি", "CCC": "চসিক", "GCC": "জিসিসি", "NCC": "এনসিসি"}


def D(x):
    """বাংলা মোডে ইংরেজি অঙ্ক বাংলা অঙ্কে দেখায়"""
    return str(x).translate(BN_DIG) if L == 1 else str(x)


def t(key, **kw):
    s = TX[key][L]
    return D(s.format(**kw)) if kw else s


def city_label(c):
    return CITY_BN.get(c, c) if L == 1 else c


def ward_label(w):
    if L == 0:
        return w
    corp, _, num = w.split("_")
    return D(f"{CORP_BN.get(corp, corp)} ওয়ার্ড {num}")


def tier_name(x):
    return x if L == 0 else TIER_BN[x]


DATA = "data/hackathon_preli_dataset.xlsx"
WEEK = pd.Timedelta(weeks=1)


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


artifact = get_model_artifact()
df = get_processed_data()
df_val = get_validation_data()
BASELINES = df[FEATURE_COLS].median()

st.markdown(f"<div class='hero'><h1>{t('title')}</h1><p>{t('subtitle')}</p></div>", unsafe_allow_html=True)

# ---------------- Sidebar ----------------
st.sidebar.header(t("area"))
selected_city = st.sidebar.selectbox(t("city"), sorted(df["city"].unique()), key="city", format_func=city_label)
city_wards = sorted(df[df["city"] == selected_city]["ward_id"].unique())
selected_ward = st.sidebar.selectbox(t("ward"), city_wards, key="ward", format_func=ward_label)

ward_df = df[df["ward_id"] == selected_ward].dropna(subset=FEATURE_COLS).sort_values("date")
issue_dates = (ward_df["date"] - 2 * WEEK).dt.strftime("%Y-%m-%d").tolist()
issue_str = st.sidebar.selectbox(t("issue"), issue_dates, index=len(issue_dates) - 1, key="issue", format_func=D)
issue_date = pd.Timestamp(issue_str)
horizon = st.sidebar.radio(t("horizon"), list(HORIZONS), index=0, horizontal=True, key="hz",
                          format_func=lambda h: D(h) + (" wk" if L == 0 else " সপ্তাহ"))
base_row = ward_df[ward_df["date"] == issue_date + 2 * WEEK].iloc[0].copy()

st.sidebar.info(t("info", t=issue_str, a=(issue_date + 2 * WEEK).date(), b=(issue_date + 3 * WEEK).date(), c=(issue_date + 4 * WEEK).date()))

st.sidebar.markdown("---")
st.sidebar.header(t("sim"))
st.sidebar.caption(t("simcap"))
sk = f"{selected_ward}_{issue_str}"
sim_rain_2w = st.sidebar.slider(t("r1"), 0.0, 300.0, float(round(base_row["rainfall_lag_2w"], 1)), key="r1" + sk)
sim_rain_3w = st.sidebar.slider(t("r2"), 0.0, 300.0, float(round(base_row["rainfall_lag_3w"], 1)), key="r2" + sk)
sim_rain_4w = st.sidebar.slider(t("r3"), 0.0, 300.0, float(round(base_row["rainfall_lag_4w"], 1)), key="r3" + sk)
sim_temp = st.sidebar.slider(t("temp"), 15.0, 38.0, float(round(base_row["temp_mean_2_4w"], 1)), key="tp" + sk)
sim_humidity = st.sidebar.slider(t("hum"), 40.0, 100.0, float(round(base_row["humidity_mean_2_4w"], 1)), key="hu" + sk)

row = {c: float(base_row[c]) for c in FEATURE_COLS}
row.update(rainfall_lag_2w=sim_rain_2w, rainfall_lag_3w=sim_rain_3w, rainfall_lag_4w=sim_rain_4w,
           temp_lag_2w=sim_temp, temp_lag_3w=sim_temp, temp_lag_4w=sim_temp,
           humidity_lag_2w=sim_humidity, humidity_lag_3w=sim_humidity, humidity_lag_4w=sim_humidity)
row = derive_features(row)
X_input = pd.DataFrame([row])[FEATURE_COLS].astype("float32")

forecasts = {}
for h in HORIZONS:
    mu = float(np.clip(artifact["models"][h].predict(X_input)[0], 0, None))
    lo, hi = (float(v[0]) for v in predict_interval([mu], artifact["dispersion"][h]))
    forecasts[h] = (mu, lo, hi, classify_risk_tier(mu))
pred_cases, ci_low, ci_high, risk_tier = forecasts[horizon]

tab1, tab2, tab3 = st.tabs([t("tab1"), t("tab2"), t("tab3")])

# ---------------- Tab 1 ----------------
with tab1:
    cols = st.columns(3)
    for col, h in zip(cols, HORIZONS):
        mu, lo, hi, tier = forecasts[h]
        tdate = (issue_date + h * WEEK).date()
        actual = df[(df["ward_id"] == selected_ward) & (df["date"] == issue_date + h * WEEK)]["dengue_cases"]
        atxt = t("actual", n=int(actual.iloc[0])) if len(actual) and pd.notna(actual.iloc[0]) else t("future")
        col.markdown(
            f"<div class='fc' style='border-left:6px solid {TIER_COLORS[tier]}'>"
            f"<div class='fc-h'>{t('fc_title', h=h, d=tdate)}</div>"
            f"<div class='fc-n'>{D(f'{mu:.1f}')} <span>{t('unit')}</span></div>"
            f"<div class='fc-r'>{t('range')}: {D(f'{lo:.1f}')} – {D(f'{hi:.1f}')}</div>"
            f"<div class='fc-a'>{atxt}</div>"
            f"<span class='badge' style='background:{TIER_COLORS[tier]}'>{tier_name(tier)}</span></div>",
            unsafe_allow_html=True)
    st.markdown(f"<div class='act'><b>{t('act', h=horizon, tier=tier_name(risk_tier))}:</b> {TIER_ACTIONS[risk_tier][L]}</div>",
                unsafe_allow_html=True)

    speech = t("say", w=ward_label(selected_ward), h=horizon, n=f"{pred_cases:.0f}",
               tier=tier_name(risk_tier), act=TIER_ACTIONS[risk_tier][L])
    speak_button(speech, "en-US" if L == 0 else "bn-BD", t("listen"), t("novoice"))

    with st.expander(t("plan_t", tier=tier_name(risk_tier), h=horizon), expanded=False):
        po, pp = st.columns(2)
        po.markdown(f"**{t('plan_o')}**\n\n" + "\n".join("- " + x for x in TIER_PLAN[risk_tier]["officers"][L]))
        pp.markdown(f"**{t('plan_p')}**\n\n" + "\n".join("- " + x for x in TIER_PLAN[risk_tier]["public"][L]))
        st.caption(t("plan_n"))

    left, right = st.columns(2)
    with left:
        st.subheader(t("drv"))
        eff = local_driver_effects(artifact["models"][horizon], row, BASELINES)
        eff_df = pd.DataFrame({"Driver": [t(k) for k in eff], "Effect": list(eff.values())}).sort_values("Effect")
        eff_df["Direction"] = np.where(eff_df["Effect"] >= 0, t("up"), t("down"))
        fig = px.bar(eff_df, x="Effect", y="Driver", orientation="h", color="Direction",
                     color_discrete_map={t("up"): "#b3261e", t("down"): "#2e7d32"},
                     title=t("drv_t", w=ward_label(selected_ward), h=horizon))
        fig.update_layout(height=380, xaxis_title=t("drv_x"), yaxis_title=None, legend_title_text=None,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        st.caption(t("drv_cap"))
    with right:
        st.subheader(t("hist"))
        recent = ward_df[ward_df["date"] <= issue_date + 2 * WEEK].tail(52)
        fig_h = go.Figure()
        fig_h.add_trace(go.Bar(x=recent["date"], y=recent["rainfall_sum_2_4w"], name=t("hist_rain"),
                               marker_color="rgba(70,130,180,0.40)", yaxis="y2"))
        fig_h.add_trace(go.Scatter(x=recent["date"], y=recent["dengue_cases"], name=t("hist_cases"),
                                   line=dict(color="#b3261e", width=2.5)))
        fig_h.update_layout(yaxis=dict(title=t("hist_y")), yaxis2=dict(title=t("hist_y2"), overlaying="y", side="right"),
                            legend=dict(orientation="h", y=1.12), height=380,
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_h, width="stretch")

# ---------------- Tab 2 ----------------
with tab2:
    st.subheader(t("hm_t", c=city_label(selected_city), h=horizon, d=issue_str))
    start = issue_date + 2 * WEEK - 11 * WEEK
    cs = df[(df["city"] == selected_city) & (df["date"] >= start) & (df["date"] <= issue_date + 2 * WEEK)].dropna(subset=FEATURE_COLS).copy()
    if not cs.empty:
        mdl, disp = artifact["models"][horizon], artifact["dispersion"][horizon]
        cs["Predicted_Cases"] = np.clip(mdl.predict(cs[FEATURE_COLS]), 0, None)
        cs["Target_Week"] = (cs["date"] + (horizon - 2) * WEEK).dt.strftime("%Y-%m-%d")
        piv = cs.pivot(index="ward_id", columns="Target_Week", values="Predicted_Cases")
        piv = piv.loc[piv.iloc[:, -1].sort_values(ascending=False).index]
        fig_hm = px.imshow(piv, aspect="auto", color_continuous_scale="YlOrRd",
                           labels=dict(x=t("hm_x"), y=t("hm_y"), color=t("hm_c")))
        fig_hm.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_hm, width="stretch")
        latest = cs[cs["date"] == issue_date + 2 * WEEK].copy()
        latest["CI_Low"], latest["CI_High"] = predict_interval(latest["Predicted_Cases"], disp)
        latest["Risk_Tier"] = latest["Predicted_Cases"].apply(lambda v: tier_name(classify_risk_tier(v)))
        latest = latest.sort_values("Predicted_Cases", ascending=False)
        st.markdown(f"**{t('pri', d=(issue_date + horizon * WEEK).date())}**")
        tbl = latest[["ward_id", "Predicted_Cases", "CI_Low", "CI_High", "Risk_Tier", "rainfall_sum_2_4w",
                      "water_logging_risk_index", "population_density_sqkm"]].round(2)
        tbl.iloc[:, 0] = tbl.iloc[:, 0].map(ward_label)
        tbl.columns = [t(k) for k in ("c_ward", "c_pred", "c_lo", "c_hi", "c_tier", "c_rain", "c_wl", "c_pop")]
        if L == 1:
            for c in tbl.columns:
                if c not in (t("c_ward"), t("c_tier")):
                    tbl[c] = tbl[c].map(lambda v: D(f"{v:.2f}"))
        st.dataframe(tbl, width="stretch", hide_index=True)
        st.caption(t("hm_cap"))

# ---------------- Tab 3 ----------------
with tab3:
    st.subheader(t("val_h"))
    vh = st.selectbox(t("val_sel"), list(HORIZONS), index=list(HORIZONS).index(horizon), key="vh",
                      format_func=lambda h: D(h) + (" wk" if L == 0 else " সপ্তাহ"))
    st.caption(t("val_cap", tr=artifact["train_range"][vh].replace(" to ", t("to")), te=artifact["test_range"][vh].replace(" to ", t("to")),
                 c1=artifact["ci_coverage"][vh][1], c0=artifact["ci_coverage"][vh][0]))
    bm = pd.DataFrame(artifact["benchmarks"][vh]).T.reset_index()
    bm["index"] = bm["index"].map(lambda n: t("m_ridge") if n.startswith("Ridge") else t("m_hgb"))
    bm = bm.rename(columns={"index": t("model"), "MAE": t("col_mae"), "RMSE": t("col_rmse"), "R2": t("col_r2"),
                            "Tier_Accuracy_Pct": t("col_acc")})
    if L == 1:
        for c in bm.columns[1:]:
            bm[c] = bm[c].map(lambda v: D(f"{v:.4g}" if v < 10 else f"{v:.2f}"))
    st.dataframe(bm, width="stretch", hide_index=True)

    vw = df_val[(df_val["ward_id"] == selected_ward) & (df_val["horizon_weeks"] == vh)].sort_values("date")
    err = vw["dengue_cases"] - vw["predicted_cases"]
    gap = abs(artifact["test_mae"][vh] - artifact["train_mae"][vh])
    m1, m2, m3 = st.columns(3)
    m1.metric(t("mae", w=ward_label(selected_ward)), D(f"{np.mean(np.abs(err)):.2f}") + " " + t("cw"))
    m2.metric(t("rmse", w=ward_label(selected_ward)), D(f"{np.sqrt(np.mean(err ** 2)):.2f}") + " " + t("cw"))
    m3.metric(t("gap"), D(f"{gap:.3f}"))
    m3.caption(t("lowof") if gap < 0.15 else t("chkof"))

    tr = artifact["tier_report"][vh]
    names = [tier_name(x) for x in tr["labels"]]
    c1, c2 = st.columns([3, 2])
    with c1:
        fig_cm = px.imshow(tr["cm"], x=names, y=names, text_auto=True, color_continuous_scale="Greens",
                           labels=dict(x=t("cm_x"), y=t("cm_y"), color=t("cm_c")), title=t("cm_t"))
        fig_cm.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_cm, width="stretch")
    with c2:
        st.markdown(f"**{t('rec_h')}**")
        st.dataframe(pd.DataFrame({t("c_tier"): names, t("rec_a"): [D(tr["recall"][x]) for x in TIERS],
                                   t("rec_b"): [D(tr["actual_share"][x]) for x in TIERS]}), hide_index=True)
        st.metric(t("al_r"), D(f"{tr['alert_recall']}%"))
        st.metric(t("al_p"), D(f"{tr['alert_precision']}%"))
        st.caption(t("al_cap"))

    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=vw["date"], y=vw["ci_high"], mode="lines", line=dict(width=0), showlegend=False))
    fig_v.add_trace(go.Scatter(x=vw["date"], y=vw["ci_low"], mode="lines", line=dict(width=0), fill="tonexty",
                               fillcolor="rgba(224,123,0,0.18)", name=t("av_int")))
    fig_v.add_trace(go.Scatter(x=vw["date"], y=vw["dengue_cases"], name=t("av_a"), line=dict(color="#1b5e3a", width=2)))
    fig_v.add_trace(go.Scatter(x=vw["date"], y=vw["predicted_cases"], name=t("av_p"), line=dict(color="#e07b00", width=2, dash="dash")))
    fig_v.update_layout(title=t("av_t", h=vh, w=ward_label(selected_ward)), height=420, xaxis_title=t("av_x"), yaxis_title=t("av_y"),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_v, width="stretch")
