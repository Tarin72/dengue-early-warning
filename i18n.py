"""Central bilingual (Bangla / English) copy and formatting helpers.

Bangla action-plan translations (TIER_ACTIONS, TIER_PLAN) are adapted from the
existing DGHS-referenced English guidance and flagged for native-speaker review.
"""

BN_DIG = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

CITY_NAMES = {
    "bn": {
        "Dhaka North": "ঢাকা উত্তর",
        "Dhaka South": "ঢাকা দক্ষিণ",
        "Chattogram": "চট্টগ্রাম",
        "Gazipur": "গাজীপুর",
        "Narayanganj": "নারায়ণগঞ্জ",
    },
    "en": {
        "Dhaka North": "Dhaka North",
        "Dhaka South": "Dhaka South",
        "Chattogram": "Chattogram",
        "Gazipur": "Gazipur",
        "Narayanganj": "Narayanganj",
    },
}

CORP_NAMES = {
    "bn": {"DNCC": "ডিএনসিসি", "DSCC": "ডিএসসিসি", "CCC": "চসিক", "GCC": "জিসিসি", "NCC": "এনসিসি"},
    "en": {"DNCC": "DNCC", "DSCC": "DSCC", "CCC": "CCC", "GCC": "GCC", "NCC": "NCC"},
}

TIER_LABELS = {
    "bn": {
        "Low": "কম ঝুঁকি",
        "Medium": "মাঝারি ঝুঁকি",
        "High": "উচ্চ ঝুঁকি",
        "Critical": "অতি উচ্চ ঝুঁকি",
    },
    "en": {
        "Low": "Low risk",
        "Medium": "Medium risk",
        "High": "High risk",
        "Critical": "Critical risk",
    },
}

TIER_SHORT = {
    "bn": {"Low": "কম", "Medium": "মাঝারি", "High": "উচ্চ", "Critical": "অতি উচ্চ"},
    "en": {"Low": "Low", "Medium": "Medium", "High": "High", "Critical": "Critical"},
}

# NOTE: Flagged for human review by a native Bangla speaker (DGHS guideline alignment).
TIER_ACTIONS = {
    "bn": {
        "Low": "নিয়মিত মশা নজরদারি এবং সাপ্তাহিক ড্রেন পরিষ্কার রাখুন।",
        "Medium": "জমা পানি ও নির্মাণস্থলে লক্ষ্যভিত্তিক লার্ভিসাইড দল পাঠান।",
        "High": "লার্ভা নিধন ও ফগিং বাড়ান; স্থানীয় ক্লিনিকে স্যালাইন ও ডেঙ্গু পরীক্ষার কিট মজুত নিশ্চিত করুন।",
        "Critical": "হাসপাতালে বাড়তি রোগীর প্রস্তুতি নিন, প্রতিদিন লার্ভিসাইডিং ও ফগিং করুন এবং বর্জ্য দ্রুত সরান।",
    },
    "en": {
        "Low": "Keep routine mosquito checks and weekly drain cleaning going.",
        "Medium": "Send targeted larvicide teams to standing water and construction sites.",
        "High": "Step up larviciding and fogging; warn local clinics to stock IV saline and dengue test kits.",
        "Critical": "Prepare hospital surge beds, run daily mosquito control, and clear waste immediately.",
    },
}

# NOTE: Flagged for human review by a native Bangla speaker (DGHS guideline alignment).
TIER_PLAN = {
    "Low": {
        "public": {
            "bn": [
                "ফুলের টব, বালতি, কুলার ও টায়ারের জমা পানি সপ্তাহে একবার ফেলে ঘষে পরিষ্কার করুন।",
                "পানি জমিয়ে রাখার পাত্র ভালোভাবে ঢেকে রাখুন।",
                "লক্ষণ চিনে রাখুন: জ্বর, তীব্র মাথাব্যথা, চোখের পেছনে ব্যথা ও গা ব্যথা।",
            ],
            "en": [
                "Empty and scrub flower pots, buckets, coolers and tyres once a week.",
                "Keep water storage containers tightly covered.",
                "Know the symptoms: fever, severe headache, pain behind the eyes, body aches.",
            ],
        },
        "officers": {
            "bn": [
                "ড্রেন, নির্মাণস্থল ও টায়ারের দোকানে সাপ্তাহিক লার্ভা জরিপ চালিয়ে যান।",
                "পরবর্তী ভারী বৃষ্টির আগেই ড্রেন পরিষ্কার ও বর্জ্য অপসারণ শেষ করুন।",
                "লার্ভিসাইড, স্প্রে যন্ত্র ও ডেঙ্গু পরীক্ষার কিট মজুত আছে কিনা যাচাই করুন।",
            ],
            "en": [
                "Keep weekly larval surveys going in drains, construction sites and tyre stores.",
                "Finish drain cleaning and waste collection before the next heavy rain.",
                "Check that larvicide, spraying equipment and dengue test kits are in stock.",
            ],
        },
    },
    "Medium": {
        "public": {
            "bn": [
                "২–৩ দিন পরপর পানির পাত্র খালি করুন এবং বাড়ির আশপাশের জমা পানি সরান।",
                "জানালায় নেট বা মশারি ব্যবহার করুন এবং দিনেও মশা তাড়ানোর ক্রিম লাগান।",
                "জ্বর ২ দিনের বেশি থাকলে অপেক্ষা না করে ডাক্তার দেখান।",
            ],
            "en": [
                "Empty water containers every 2 to 3 days and remove standing water around your home.",
                "Use window screens or mosquito nets, and apply repellent during the day.",
                "If fever lasts more than 2 days, see a doctor instead of waiting.",
            ],
        },
        "officers": {
            "bn": [
                "জমা পানির হটস্পটে (বন্ধ ড্রেন, নির্মাণস্থল, টায়ারের স্তূপ) লার্ভিসাইড দল পাঠান।",
                "ওয়ার্ডের ঘনবসতিপূর্ণ এলাকায় বাড়ি বাড়ি পানির পাত্র পরীক্ষা শুরু করুন।",
                "স্থানীয় ক্লিনিকগুলোকে জ্বরের প্রথম দিনেই NS1 পরীক্ষার বিষয়ে সতর্ক করুন।",
            ],
            "en": [
                "Send larvicide teams to standing-water hotspots: blocked drains, construction sites, tyre dumps.",
                "Start door-to-door container checks in the most crowded parts of the ward.",
                "Brief local clinics on early NS1 testing in the first days of fever.",
            ],
        },
    },
    "High": {
        "public": {
            "bn": [
                "এডিস মশা দিনে (সকাল ও বিকেলে) কামড়ায়: মশারি, লম্বা হাতার জামা ও রিপেলেন্ট ব্যবহার করুন।",
                "জ্বর হলে দ্রুত পরীক্ষা করান; জ্বরের জন্য শুধু প্যারাসিটামল খান ও প্রচুর তরল পান করুন।",
                "ডেঙ্গু জ্বরে অ্যাসপিরিন বা আইবুপ্রোফেন (NSAID) খাবেন না।",
            ],
            "en": [
                "Aedes mosquitoes bite in the daytime (morning and late afternoon): use nets, long sleeves and repellent.",
                "With fever, get tested early; take only paracetamol for fever and drink plenty of fluids.",
                "Do not take aspirin or ibuprofen (NSAIDs) for dengue fever.",
            ],
        },
        "officers": {
            "bn": [
                "লার্ভিসাইডিং ও উৎস ধ্বংস বাড়ান; ফগিং শুধু প্রাপ্তবয়স্ক মশার বিরুদ্ধে সহায়ক হিসেবে ব্যবহার করুন।",
                "হাসপাতাল ও ক্লিনিককে স্যালাইন, NS1/IgM কিট ও প্লেটলেট পরীক্ষার প্রস্তুতি রাখতে সতর্ক করুন।",
                "কয়েক দিনের মধ্যে ওয়ার্ডের বর্জ্য সরান এবং জলাবদ্ধ ড্রেন ঠিক করুন।",
            ],
            "en": [
                "Intensify larviciding and breeding-source removal; use fogging only as a supplement against adult mosquitoes.",
                "Alert clinics and hospitals to stock IV saline, NS1/IgM test kits and platelet monitoring.",
                "Clear waste and fix blocked drainage or water-logging points in the ward within days.",
            ],
        },
    },
    "Critical": {
        "public": {
            "bn": [
                "সতর্ক লক্ষণ (তীব্র পেটব্যথা, বারবার বমি, নাক/মাড়ি দিয়ে রক্তপাত, কালো পায়খানা, ঝিমুনি বা শ্বাসকষ্ট) দেখলেই হাসপাতালে যান।",
                "উচ্চ ঝুঁকির সব নিয়ম মানুন: মশারি, রিপেলেন্ট, দ্রুত পরীক্ষা ও শুধু প্যারাসিটামল।",
                "আজই বাড়ির ভেতর ও আশপাশের সব জমা পানির পাত্র খালি করুন।",
            ],
            "en": [
                "Go to a hospital immediately for warning signs: severe belly pain, repeated vomiting, bleeding gums or nose, black stool, drowsiness or difficulty breathing.",
                "Follow every High-risk step: mosquito nets, repellent, early testing, and paracetamol only.",
                "Check and empty every water container around your home today.",
            ],
        },
        "officers": {
            "bn": [
                "ওয়ার্ডে জরুরি ব্যবস্থা চালু করুন: প্রতিদিন লার্ভিসাইডিং, ফগিং ও বর্জ্য অপসারণ।",
                "হাসপাতালে অতিরিক্ত বেড, ডেঙ্গু কর্নার, স্যালাইন ও পরীক্ষার কিট প্রস্তুত রাখুন।",
                "ওয়ার্ড কাউন্সিলর, স্কুল, মসজিদ ও মাইকের মাধ্যমে সতর্কতা প্রচার করুন এবং প্রতিদিন কেস রিপোর্ট করুন।",
            ],
            "en": [
                "Start a ward-level emergency response: daily larviciding, fogging and waste clearance.",
                "Prepare hospital surge capacity: extra beds, a dengue corner, IV saline and test kits.",
                "Use ward councillors, schools, mosques and loudspeakers for public alerts and report cases daily.",
            ],
        },
    },
}

DRIVER_LABELS = {
    "bn": {
        "Rainfall (lags 2–4w)": "২–৪ সপ্তাহ আগের বৃষ্টি",
        "Temperature": "তাপমাত্রা",
        "Humidity": "আর্দ্রতা",
        "Water-logging risk": "জলাবদ্ধতা",
        "Population density": "ঘনবসতি",
        "Sanitation": "স্যানিটেশন",
    },
    "en": {
        "Rainfall (lags 2–4w)": "Rain 2 to 4 weeks ago",
        "Temperature": "Temperature",
        "Humidity": "Humidity",
        "Water-logging risk": "Water-logging",
        "Population density": "Crowding",
        "Sanitation": "Sanitation",
    },
}

STRINGS = {
    "bn": {
        "page_title": "ডেঙ্গু আগাম সতর্কতা | Dengue Early Warning",
        "title": "ডেঙ্গু আগাম সতর্কতা",
        "subtitle": "আগামী ২ থেকে ৪ সপ্তাহে আপনার ওয়ার্ডে ডেঙ্গুর ঝুঁকি কেমন, জানুন।",
        # Navigation & page intros
        "nav_home": "হোম",
        "nav_how": "কীভাবে কাজ করে",
        "nav_dashboard": "ড্যাশবোর্ড",
        "nav_trust": "আস্থা ও সীমাবদ্ধতা",
        "intro_home": "এই পাতায় আপনার ওয়ার্ডের আগামী ২–৪ সপ্তাহের ডেঙ্গু ঝুঁকি এবং এখন কী করবেন তা দ্রুত জানতে পারবেন।",
        "intro_how": "এই পাতায় সহজ ৪টি ধাপে জানুন কীভাবে বৃষ্টি ও আবহাওয়া দেখে ডেঙ্গুর আগাম সতর্কতা তৈরি হয়।",
        "intro_dashboard": "এই পাতায় বিস্তারিত পূর্বাভাস, কারণ, গত ১ বছরের চিত্র, সব ওয়ার্ডের তালিকা ও নির্ভরযোগ্যতা দেখুন।",
        "intro_trust": "এই পাতায় জানুন পূর্বাভাস কতটা নির্ভরযোগ্য, তথ্য কোথা থেকে আসে এবং এই ব্যবস্থার সীমাবদ্ধতা কী।",
        # Home page
        "home_hint": "প্রথমবার? এখান থেকে শুরু করুন",
        "home_headline": "আপনার এলাকায় ডেঙ্গুর ঝুঁকি, আগেই জানুন।",
        "home_sub": "বৃষ্টি ও আবহাওয়ার তথ্য দেখে ২ থেকে ৪ সপ্তাহ আগেই জানুন আপনার ওয়ার্ডে ঝুঁকি কেমন এবং এখন কী করবেন।",
        "home_pick": "আপনার ওয়ার্ড বেছে নিন",
        "home_to_dash": "বিস্তারিত চার্ট ও সব ওয়ার্ড দেখুন →",
        "stat_wards_lbl": "আওতাভুক্ত এলাকা",
        "stat_wards_val": "{w}টি ওয়ার্ড",
        "stat_wards_sub": "{c}টি সিটি কর্পোরেশনে নজরদারি",
        "stat_hz_lbl": "আগাম সতর্কতার সময়",
        "stat_hz_val": "২–৪ সপ্তাহ",
        "stat_hz_sub": "আক্রান্ত বাড়ার আগেই প্রস্তুতির সুযোগ",
        "stat_yrs_lbl": "তথ্যের সময়কাল",
        "stat_yrs_val": "{y1}–{y2}",
        "stat_yrs_sub": "{yrs} বছরের আবহাওয়া ও রোগীর তথ্য",
        # How it works page
        "how_title": "সহজ কথায়: কীভাবে কাজ করে?",
        "how_sub": "জটিল কোনো হিসাব নয়—বৃষ্টি, মশার জীবনচক্র আর আগের বছরের তথ্যের ওপর ভিত্তি করেই এই সতর্কতা।",
        "how_step_tag": "ধাপ {n}",
        "how_s1_t": "বৃষ্টি ও আবহাওয়া",
        "how_s1_b": "টানা বৃষ্টি, উষ্ণ তাপমাত্রা ও আর্দ্রতা বাড়লে বাড়ির আশপাশে পানি জমে। এই পরিবেশ এডিস মশার ডিম পাড়ার জন্য উপযুক্ত।",
        "how_s2_t": "মশা বড় হতে ১–২ সপ্তাহ লাগে",
        "how_s2_b": "জমে থাকা পানিতে মশার ডিম থেকে পূর্ণবয়স্ক মশা হতে ১ থেকে ২ সপ্তাহ লাগে। এরপর রোগী বাড়তে আরও ১–২ সপ্তাহ সময় লাগে।",
        "how_s3_t": "আগের বছরের প্যাটার্ন দেখে হিসাব",
        "how_s3_b": "আমাদের ব্যবস্থা গত ১০ বছরের বৃষ্টি, আবহাওয়া ও রোগীর সংখ্যার সম্পর্ক থেকে শিখেছে। আজকের আবহাওয়া দেখে এটি আগের মতো ঝুঁকিপূর্ণ অবস্থা চিনতে পারে।",
        "how_s4_t": "আপনি ২–৪ সপ্তাহ আগে সতর্ক হন",
        "how_s4_b": "তাই রোগী বাড়ার ২ থেকে ৪ সপ্তাহ আগেই আপনি ও সিটি কর্পোরেশন প্রস্তুতি নিতে পারেন। আগে থেকেই জমা পানি সরালে ঝুঁকি কমানো সহজ হয়।",
        "how_end_note": "এটি অনুমান, নিশ্চিত রোগ নির্ণয় নয়।",
        "same_rain_t": "একই বৃষ্টি, তবু আলাদা ঝুঁকি কেন?",
        "same_rain_sub": "দুটি এলাকায় সমান বৃষ্টি হলেও নিচের তিনটি কারণে ডেঙ্গুর ঝুঁকি কম বা বেশি হতে পারে:",
        "sr1_t": "জলাবদ্ধতা",
        "sr1_b": "যেখানে ড্রেন বন্ধ থাকে বা সহজে পানি জমে, সেখানে মশা ডিম পাড়ার বেশি জায়গা পায়।",
        "sr2_t": "ঘনবসতি",
        "sr2_b": "অনেক মানুষ কাছাকাছি বসবাস করলে একটি আক্রান্ত মশা দ্রুত অনেকের মধ্যে রোগ ছড়াতে পারে।",
        "sr3_t": "পরিচ্ছন্নতা ও পানি সংরক্ষণ",
        "sr3_b": "খোলা পানির ট্যাংক, নির্মাণস্থল বা বর্জ্য বেশি থাকলে মশার বংশবৃদ্ধি দ্রুত বাড়ে।",
        "how_listen_all": "পুরো ৪টি ধাপ একসাথে শুনুন",
        # Step 1 & shared controls
        "step1": "১. আপনার এলাকা বেছে নিন",
        "city": "শহর",
        "ward": "ওয়ার্ড",
        "horizon": "কত সপ্তাহ পরের পূর্বাভাস দেখতে চান?",
        "hz_opt": "{h} সপ্তাহ পরে",
        "weather_note": "{date} পর্যন্ত আবহাওয়ার তথ্যের ভিত্তিতে।",
        "other_week_exp": "পুরোনো সপ্তাহের পূর্বাভাস দেখুন (ঐচ্ছিক)",
        "issue": "সর্বশেষ পর্যবেক্ষিত আবহাওয়ার সপ্তাহ",
        # Dashboard & tabs
        "dash_guide": "নিচের তিনটি ট্যাব থেকে বিস্তারিত বিশ্লেষণ বেছে নিন:",
        "tab_forecast": "পূর্বাভাস",
        "tab_wards": "সব ওয়ার্ড",
        "tab_accuracy": "নির্ভরযোগ্যতা",
        "fc_for_week": "{d} তারিখের সপ্তাহ · {h} সপ্তাহ পরে",
        "main_sentence": "{d} সপ্তাহে {ward}-এ ডেঙ্গুর ঝুঁকি: {risk}।",
        "very_few": "এই সপ্তাহে খুব কম রোগী হওয়ার সম্ভাবনা।",
        "expected_cases": "ওই সপ্তাহে প্রায় {n} জন আক্রান্ত হতে পারেন।",
        "unit_cases_week": "জন / সপ্তাহ",
        "range_line": "সম্ভাব্য সংখ্যা {a} থেকে {b}-এর মধ্যে।",
        "uncertainty": "এটি একটি আনুমানিক হিসাব। প্রকৃত সংখ্যা কিছুটা কম বা বেশি হতে পারে।",
        "learn_more": "৮০% সীমা কী? আরও জানুন",
        "learn_more_body": "বেশিরভাগ সময় (১০ সপ্তাহের মধ্যে প্রায় ৮ সপ্তাহ) প্রকৃত সংখ্যা এই সীমার মধ্যে থাকে। যত দূরের সপ্তাহ, অনিশ্চয়তা তত বেশি।",
        "actual_past": "তুলনা: আসল রোগী ছিল {n} জন",
        "future_week": "ভবিষ্যৎ সপ্তাহের পূর্বাভাস",
        "city_ctx_low": "{city}-এর বেশিরভাগ ওয়ার্ডের তুলনায় এখানে ঝুঁকি কম ({rank}/{total} তম)।",
        "city_ctx_high": "{city}-এর {total}টি ওয়ার্ডের মধ্যে ঝুঁকির দিক থেকে অবস্থান #{rank}।",
        "other_horizons": "অন্যান্য সপ্তাহের পূর্বাভাস (দেখতে ক্লিক করুন)",
        "select_horizon_btn": "{h} সপ্তাহ পরের পূর্বাভাস দেখুন",
        "scenario_badge": "কল্পিত আবহাওয়া চালু আছে — এটি আসল পূর্বাভাস নয়",
        "action_title": "এখন কী করবেন",
        "listen": "শুনুন",
        "stop": "থামান",
        "novoice": "আপনার ডিভাইসে বাংলা ভয়েস নেই",
        "say": "{w}। {d} সপ্তাহে ঝুঁকি: {risk}। প্রায় {n} জন রোগী হতে পারেন। করণীয়: {acts}",
        "full_plan": "পূর্ণ করণীয় তালিকা দেখুন",
        "tab_residents": "বাসিন্দাদের জন্য",
        "tab_officers": "সিটি কর্পোরেশন ও স্বাস্থ্যকর্মীদের জন্য",
        "plan_note": "এটি শুধু সাধারণ নির্দেশনা। স্বাস্থ্য অধিদপ্তরের (DGHS) জাতীয় ডেঙ্গু নির্দেশিকা ও সিটি করপোরেশনের নিয়ম মেনে চলুন, অসুস্থ হলে ডাক্তার দেখান।",
        "exp_why": "ঝুঁকি কেন এমন?",
        "exp_history": "গত ৫২ সপ্তাহের বৃষ্টি ও ডেঙ্গু রোগী",
        "exp_scenario": "আবহাওয়া বদলালে কী হবে, দেখুন",
        "drv_title": "এখানে কী ঝুঁকি বাড়াচ্ছে বা কমাচ্ছে",
        "drv_up": "ঝুঁকি বাড়ায়",
        "drv_down": "ঝুঁকি কমায়",
        "drv_x": "সাপ্তাহিক সম্ভাব্য রোগীর পরিবর্তন",
        "drv_takeaway_up": "সাধারণ অবস্থার তুলনায় এখানে '{top}' ঝুঁকি সবচেয়ে বেশি বাড়াচ্ছে।",
        "drv_takeaway_down": "সাধারণ অবস্থার তুলনায় এখানে '{top}' ঝুঁকি সবচেয়ে বেশি কমিয়ে রাখছে।",
        "drv_takeaway_flat": "এই মুহূর্তে সবগুলো কারণই সাধারণ মাত্রার কাছাকাছি আছে।",
        "hist_title": "গত ৫২ সপ্তাহের বৃষ্টি ও ডেঙ্গু রোগী",
        "hist_rain": "বৃষ্টি (মিমি)",
        "hist_cases": "সাপ্তাহিক রোগী",
        "hist_takeaway": "গত ১ বছরে সর্বোচ্চ সাপ্তাহিক রোগী ছিল {max_c} জন ({max_c_date}) এবং সর্বোচ্চ বৃষ্টি ছিল {max_r} মিমি।",
        "scen_cap": "বৃষ্টি, তাপমাত্রা বা আর্দ্রতা বদলে দেখুন পূর্বাভাস কীভাবে বদলায়। শুরুতে আসল তথ্য দেওয়া আছে।",
        "r1": "বৃষ্টি, সর্বশেষ সপ্তাহ (মিমি)",
        "r2": "বৃষ্টি, ১ সপ্তাহ আগে (মিমি)",
        "r3": "বৃষ্টি, ২ সপ্তাহ আগে (মিমি)",
        "temp": "গড় তাপমাত্রা, গত ৩ সপ্তাহ (°সে)",
        "hum": "আপেক্ষিক আর্দ্রতা, গত ৩ সপ্তাহ (%)",
        "reset_weather": "আসল তথ্যে ফিরুন",
        "hm_title": "{city}: সব ওয়ার্ডের ঝুঁকি ({h} সপ্তাহ পরের পূর্বাভাস)",
        "hm_takeaway": "যে ওয়ার্ডগুলোতে আগে নজর দেওয়া দরকার — শীর্ষ ঝুঁকিতে রয়েছে {top_ward}।",
        "hm_x": "লক্ষ্য সপ্তাহ",
        "hm_y": "ওয়ার্ড",
        "hm_c": "রোগী / সপ্তাহ",
        "pri_title": "{d} সপ্তাহের জন্য ওয়ার্ড অগ্রাধিকার তালিকা (শীর্ষ ৫টি চিহ্নিত)",
        "sort_label": "তালিকা সাজান",
        "sort_risk": "অগ্রাধিকার (বেশি ঝুঁকি আগে)",
        "sort_ward": "ওয়ার্ডের নাম",
        "sort_rain": "বৃষ্টি (বেশি থেকে কম)",
        "sort_wl": "জলাবদ্ধতা (বেশি থেকে কম)",
        "top5_tag": "শীর্ষ {n}",
        "c_ward": "ওয়ার্ড",
        "c_risk": "ঝুঁকি",
        "c_pred": "সম্ভাব্য রোগী",
        "c_range": "সম্ভাব্য সীমা",
        "c_rain": "বৃষ্টি (মিমি)",
        "c_wl": "জলাবদ্ধতা",
        "c_pop": "ঘনবসতি/বর্গকিমি",
        "hm_cap": "এই পাতায় শেষ ১২ সপ্তাহের আসল আবহাওয়ার তথ্য ব্যবহার হয়েছে। আবহাওয়া বদলানোর স্লাইডার শুধু 'পূর্বাভাস' ট্যাবে কাজ করে।",
        "acc_title": "এই পূর্বাভাস কতটা নির্ভরযোগ্য?",
        "acc_sel": "কোন সপ্তাহের পূর্বাভাস যাচাই করবেন",
        "acc_card_err": "সাধারণ ভুল",
        "acc_card_err_val": "সপ্তাহে প্রায় {x} জন",
        "acc_card_caught": "উচ্চ ঝুঁকির সপ্তাহ ধরা পড়েছে",
        "acc_card_prec": "সতর্কতা সঠিক ছিল",
        "acc_caveat": "বেশিরভাগ সপ্তাহে ঝুঁকি কম থাকে, তাই মোট নির্ভুলতা বেশি দেখায়। আসল প্রাদুর্ভাব কতটা ধরা পড়ে, তা সতর্কতার সংখ্যায় বোঝা যায়।",
        "acc_cov": "{tr} সালের তথ্যে শিখে {te} সালের অদেখা সপ্তাহে পরীক্ষিত। ঝুঁকিপূর্ণ সপ্তাহে (৩+ রোগী) ৮০% সীমা সঠিক ছিল {c1}% ক্ষেত্রে (সব সপ্তাহ মিলিয়ে {c0}%)।",
        "acc_expert": "বিশেষজ্ঞদের জন্য: বিস্তারিত মান",
        "acc_bm_title": "মডেল তুলনা (অদেখা পরীক্ষা সেট)",
        "model": "মডেল",
        "m_ridge": "রিজ বেসলাইন",
        "m_hgb": "গ্রেডিয়েন্ট বুস্টিং (পয়সন), নির্বাচিত মডেল",
        "col_mae": "MAE (গড় ভুল)",
        "col_rmse": "RMSE",
        "col_r2": "R²",
        "col_acc": "ঝুঁকির স্তর সঠিক %",
        "ward_mae": "{w}: গড় ভুল (MAE)",
        "ward_rmse": "{w}: RMSE",
        "gap_lbl": "ট্রেন ও টেস্ট MAE ব্যবধান",
        "lowof": "ওভারফিটিং কম",
        "chkof": "ওভারফিটিং যাচাই করুন",
        "cm_t": "ঝুঁকির স্তর: আসল বনাম পূর্বাভাস (সব ওয়ার্ড)",
        "cm_x": "পূর্বাভাস",
        "cm_y": "আসল",
        "cm_c": "ওয়ার্ড-সপ্তাহ",
        "rec_h": "প্রতিটি আসল স্তরের কত শতাংশ ধরা পড়েছে",
        "rec_a": "ধরা পড়েছে %",
        "rec_b": "আসল সপ্তাহ %",
        "av_t": "সাপ্তাহিক রোগী: আসল বনাম পূর্বাভাস ({h} সপ্তাহ পরে · {w})",
        "av_int": "৮০% সীমা",
        "av_a": "আসল রোগী",
        "av_p": "পূর্বাভাস",
        "av_x": "সপ্তাহ",
        "av_y": "সাপ্তাহিক রোগী",
        "to": " থেকে ",
        # Trust & limits page
        "trust_title": "আস্থা, তথ্যের উৎস ও সীমাবদ্ধতা",
        "trust_can_t": "এই ব্যবস্থা যা করতে পারে",
        "trust_can_1": "আবহাওয়া ও এলাকার অবস্থা দেখে ২–৪ সপ্তাহ আগে ওয়ার্ড-ভিত্তিক ঝুঁকির ধারণা দিতে পারে।",
        "trust_can_2": "কোন কারণে ঝুঁকি বাড়ছে বা কমছে (বৃষ্টি, তাপমাত্রা, জলাবদ্ধতা, ঘনবসতি) তা দেখাতে পারে।",
        "trust_can_3": "সিটি কর্পোরেশনকে কোন ওয়ার্ডে আগে নজর দিতে হবে তা অগ্রাধিকার ভিত্তিতে বোঝাতে পারে।",
        "trust_cant_t": "যা করতে পারে না (সীমাবদ্ধতা)",
        "trust_cant_1": "এটি কোনো চিকিৎসা পরামর্শ বা রোগ নির্ণয়ের যন্ত্র নয়; জ্বর হলে অবশ্যই ডাক্তার দেখান।",
        "trust_cant_2": "প্রতি সপ্তাহে একদম নিখুঁত রোগীর সংখ্যা নিশ্চিতভাবে বলতে পারে না—এটি একটি সম্ভাব্য অনুমান।",
        "trust_cant_3": "আবহাওয়ার হঠাৎ বড় পরিবর্তন বা নতুন কোনো অপ্রত্যাশিত পরিস্থিতি আগে থেকে জানতে পারে না।",
        "trust_data_t": "তথ্যের উৎস ও পরীক্ষা পদ্ধতি",
        "trust_data_b": "২০১৬ থেকে ২০২৫ সাল পর্যন্ত বাংলাদেশের {c}টি শহরের {w}টি ওয়ার্ডের সাপ্তাহিক আবহাওয়া (বৃষ্টি, তাপমাত্রা, আর্দ্রতা), জলাবদ্ধতা ও জনঘনত্বের {rows}টি পর্যবেক্ষিত রেকর্ডের ওপর ভিত্তি করে এটি তৈরি। ২০২৪–২০২৫ সালের অদেখা সপ্তাহগুলোতে আলাদাভাবে যাচাই করা হয়েছে।",
        "trust_review_t": "বাংলা অনুবাদ ও জনস্বাস্থ্য পর্যালোচনা",
        "trust_review_b": "করণীয় নির্দেশনাগুলো স্বাস্থ্য অধিদপ্তরের (DGHS) জাতীয় নির্দেশিকার আলোকে বাংলায় অনুবাদ করা হয়েছে। চূড়ান্ত মাঠ-পর্যায়ে ব্যবহারের আগে বাংলা ভাষাভাষী জনস্বাস্থ্য বিশেষজ্ঞের পর্যালোচনা সুপারিশ করা হচ্ছে।",
        "trust_say": "{h} সপ্তাহ পরের পূর্বাভাসে সাধারণ ভুল সপ্তাহে প্রায় {err} জন। উচ্চ ঝুঁকির সপ্তাহ ধরা পড়েছে {caught} শতাংশ এবং সতর্কতা সঠিক ছিল {prec} শতাংশ। এটি আগাম সতর্কতার সহায়ক, রোগ নির্ণয় নয়।",
        # Help & states & footer
        "help_title": "সহায়তা / Help",
        "help_q1": "আমার ঝুঁকি কত?",
        "help_q2": "এখন কী করব?",
        "help_q3": "এই পূর্বাভাস কেন?",
        "help_a1": "{d} তারিখের সপ্তাহে {ward}-এ ডেঙ্গুর ঝুঁকি **{risk}**। ওই সপ্তাহে প্রায় **{n} জন** আক্রান্ত হতে পারেন (সম্ভাব্য সীমা {a}–{b})। এটি একটি আনুমানিক হিসাব।",
        "help_a2": "{risk}-এর জন্য এখন করণীয়: ১) {p1} ২) {p2} ৩) {p3}",
        "help_a3": "এই পূর্বাভাসটি {issue_d} পর্যন্ত বৃষ্টি, তাপমাত্রা, আর্দ্রতা এবং ওয়ার্ডের জলাবদ্ধতা ও ঘনবসতির তথ্যের ওপর ভিত্তি করে তৈরি। এখানে প্রধানত '{top_drv}' প্রভাব ফেলছে।",
        "loading": "পূর্বাভাস তৈরি হচ্ছে...",
        "no_data": "এই ওয়ার্ডের তথ্য পাওয়া যায়নি। অন্য ওয়ার্ড বেছে নিন।",
        "error": "কিছু একটা সমস্যা হয়েছে। পেজটি আবার লোড করুন।",
        "disclaimer": "এটি আগাম সতর্কতার সহায়ক, রোগ নির্ণয় নয়। জ্বর হলে ডাক্তার দেখান।",
        "footer_meta": "তথ্যসূত্র: বাংলাদেশের নগর ডেঙ্গু ও আবহাওয়া নজরদারি ডেটা (২০১৬–২০২৫) · সর্বশেষ তথ্য: {date}",
    },
    "en": {
        "page_title": "Dengue Early Warning | ডেঙ্গু আগাম সতর্কতা",
        "title": "Dengue Early Warning",
        "subtitle": "See the dengue risk in your ward for the next 2 to 4 weeks.",
        # Navigation & page intros
        "nav_home": "Home",
        "nav_how": "How it works",
        "nav_dashboard": "Dashboard",
        "nav_trust": "Trust & limits",
        "intro_home": "On this page, quickly check your ward's dengue risk for the next 2–4 weeks and what to do right now.",
        "intro_how": "See in 4 plain steps how rainfall and weather help warn you about dengue weeks before cases peak.",
        "intro_dashboard": "Explore detailed ward forecasts, key drivers, the past 52 weeks, city-wide ward priority, and accuracy checks.",
        "intro_trust": "Learn how reliable this forecast is, where the data comes from, and what this tool can and cannot do.",
        # Home page
        "home_hint": "First time here? Start below",
        "home_headline": "Know your area's dengue risk before it spreads.",
        "home_sub": "Check your ward's dengue risk 2 to 4 weeks ahead from recent weather, and get clear steps to act early.",
        "home_pick": "Choose your area",
        "home_to_dash": "Open detailed charts & all wards →",
        "stat_wards_lbl": "Areas covered",
        "stat_wards_val": "{w} wards",
        "stat_wards_sub": "Monitored across {c} cities",
        "stat_hz_lbl": "Early warning window",
        "stat_hz_val": "2–4 weeks",
        "stat_hz_sub": "Head start before cases rise",
        "stat_yrs_lbl": "Historical record",
        "stat_yrs_val": "{y1}–{y2}",
        "stat_yrs_sub": "{yrs} years of weather & case data",
        # How it works page
        "how_title": "In plain words: how does it work?",
        "how_sub": "No complicated jargon—this warning follows rainfall, the mosquito life cycle, and patterns seen in past years.",
        "how_step_tag": "Step {n}",
        "how_s1_t": "Rain and weather",
        "how_s1_b": "Steady rain, warm temperatures and high humidity leave standing water around homes. These conditions help Aedes mosquitoes breed.",
        "how_s2_t": "Mosquitoes take 1–2 weeks to grow",
        "how_s2_b": "Mosquito eggs in standing water take 1 to 2 weeks to grow into biting adults. Another 1 to 2 weeks pass before people fall sick.",
        "how_s3_t": "Our system checks patterns from past years",
        "how_s3_b": "Our system learned from 10 years of weather and dengue records across cities. By checking today's weather, it spots conditions that led to outbreaks before.",
        "how_s4_t": "You get warned 2–4 weeks early",
        "how_s4_b": "This gives families and city teams a 2 to 4 week head start. Clearing standing water early makes it much easier to prevent outbreaks.",
        "how_end_note": "This is an estimate, not a confirmed medical diagnosis.",
        "same_rain_t": "Same rain, different risk — why?",
        "same_rain_sub": "Even when two wards receive the same rainfall, dengue risk can differ for three local reasons:",
        "sr1_t": "Standing water",
        "sr1_b": "Areas with blocked drains or poor drainage hold puddles longer, giving mosquitoes more places to lay eggs.",
        "sr2_t": "Crowded neighborhoods",
        "sr2_b": "When many people live closely together, one infected mosquito can spread illness to more people.",
        "sr3_t": "Sanitation & water storage",
        "sr3_b": "Uncovered water tanks, construction sites, or uncollected waste let mosquito numbers grow faster.",
        "how_listen_all": "Listen to all 4 steps together",
        # Step 1 & shared controls
        "step1": "1. Choose your area",
        "city": "City",
        "ward": "Ward",
        "horizon": "Forecast for how many weeks from now?",
        "hz_opt": "In {h} weeks",
        "weather_note": "Based on weather up to {date}.",
        "other_week_exp": "Check an earlier week (optional)",
        "issue": "Last observed weather week",
        # Dashboard & tabs
        "dash_guide": "Choose a section below for detailed charts, city-wide risk, or accuracy checks:",
        "tab_forecast": "Forecast",
        "tab_wards": "All wards",
        "tab_accuracy": "Accuracy",
        "fc_for_week": "Week of {d} · In {h} weeks",
        "main_sentence": "Dengue risk in {ward} in the week of {d}: {risk}.",
        "very_few": "Very few cases expected that week.",
        "expected_cases": "About {n} cases expected that week.",
        "unit_cases_week": "cases / week",
        "range_line": "Likely between {a} and {b}.",
        "uncertainty": "This is an estimate. The real number can be a little lower or higher.",
        "learn_more": "What is this 80% range? Learn more",
        "learn_more_body": "Most of the time (about 8 in 10 weeks) the real number falls inside this range. The further ahead, the less certain.",
        "actual_past": "Actual recorded cases: {n}",
        "future_week": "Upcoming week forecast",
        "city_ctx_low": "Lower risk than most wards in {city} (rank #{rank} of {total}).",
        "city_ctx_high": "Ranked #{rank} of {total} wards by expected cases in {city}.",
        "other_horizons": "Other forecast weeks (click to switch)",
        "select_horizon_btn": "View {h}-week forecast",
        "scenario_badge": "Scenario mode active — showing modified weather, not real forecast",
        "action_title": "What to do now",
        "listen": "Listen",
        "stop": "Stop",
        "novoice": "Your device has no English voice",
        "say": "{w}. Week of {d}: {risk}. About {n} cases expected. Actions: {acts}",
        "full_plan": "See full action plan",
        "tab_residents": "For residents",
        "tab_officers": "For city corporation and health workers",
        "plan_note": "This is general guidance only. Follow the national dengue guidelines (DGHS) and your city corporation's protocols, and see a doctor for any illness.",
        "exp_why": "Why this risk?",
        "exp_history": "Last 52 weeks: rain and dengue cases",
        "exp_scenario": "Try changing the weather",
        "drv_title": "What raises or lowers the risk here",
        "drv_up": "Raises risk",
        "drv_down": "Lowers risk",
        "drv_x": "Change in expected weekly cases",
        "drv_takeaway_up": "Compared with typical conditions, '{top}' raises the risk most here.",
        "drv_takeaway_down": "Compared with typical conditions, '{top}' keeps the risk lowest here.",
        "drv_takeaway_flat": "All factors are currently close to typical conditions.",
        "hist_title": "Rain and dengue cases, last 52 weeks",
        "hist_rain": "Rain (mm)",
        "hist_cases": "Weekly cases",
        "hist_takeaway": "Over the last 52 weeks, weekly cases peaked at {max_c} ({max_c_date}) and rainfall peaked at {max_r} mm.",
        "scen_cap": "Change rain, temperature or humidity to see how the forecast reacts. Real observed values are loaded by default.",
        "r1": "Rain, last observed week (mm)",
        "r2": "Rain, 1 week earlier (mm)",
        "r3": "Rain, 2 weeks earlier (mm)",
        "temp": "Temperature, last 3 weeks (°C)",
        "hum": "Humidity, last 3 weeks (%)",
        "reset_weather": "Back to real weather",
        "hm_title": "{city}: risk in all wards ({h} weeks ahead)",
        "hm_takeaway": "Wards that need attention first — {top_ward} currently has the highest expected cases.",
        "hm_x": "Target week",
        "hm_y": "Ward",
        "hm_c": "Cases / week",
        "pri_title": "Wards that need attention first · week of {d} (top 5 highlighted)",
        "sort_label": "Sort list by",
        "sort_risk": "Priority (highest risk first)",
        "sort_ward": "Ward name",
        "sort_rain": "Rain (high to low)",
        "sort_wl": "Water-logging (high to low)",
        "top5_tag": "Top {n}",
        "c_ward": "Ward",
        "c_risk": "Risk",
        "c_pred": "Expected cases",
        "c_range": "Likely range",
        "c_rain": "Rain (mm)",
        "c_wl": "Water-logging",
        "c_pop": "Density / km²",
        "hm_cap": "This view uses real observed weather for the last 12 weeks. Weather scenario sliders only apply in the Forecast tab.",
        "acc_title": "How reliable is this forecast?",
        "acc_sel": "Forecast horizon to check",
        "acc_card_err": "Typical error",
        "acc_card_err_val": "about {x} cases / week",
        "acc_card_caught": "Outbreak weeks caught",
        "acc_card_prec": "Alerts that were right",
        "acc_caveat": "Most weeks are low risk, so overall accuracy looks high. Alert numbers show how well real outbreaks are caught.",
        "acc_cov": "Trained on {tr}; tested on unseen weeks {te}. On weeks with 3+ predicted cases, 80% ranges held {c1}% of real counts ({c0}% overall).",
        "acc_expert": "For experts: detailed metrics",
        "acc_bm_title": "Model benchmark (unseen test weeks)",
        "model": "Model",
        "m_ridge": "Ridge baseline",
        "m_hgb": "Gradient boosting (Poisson), chosen model",
        "col_mae": "MAE",
        "col_rmse": "RMSE",
        "col_r2": "R²",
        "col_acc": "Risk-level accuracy %",
        "ward_mae": "{w}: average error (MAE)",
        "ward_rmse": "{w}: RMSE",
        "gap_lbl": "Train vs test MAE gap",
        "lowof": "Little overfitting",
        "chkof": "Check overfitting",
        "cm_t": "Risk level: actual vs predicted (all wards)",
        "cm_x": "Predicted",
        "cm_y": "Actual",
        "cm_c": "Ward-weeks",
        "rec_h": "Share of each real risk level caught",
        "rec_a": "Caught %",
        "rec_b": "Share of weeks %",
        "av_t": "Actual vs predicted weekly cases ({h} weeks ahead · {w})",
        "av_int": "80% range",
        "av_a": "Actual",
        "av_p": "Predicted",
        "av_x": "Week",
        "av_y": "Weekly cases",
        "to": " to ",
        # Trust & limits page
        "trust_title": "Trust, data source, and limits",
        "trust_can_t": "What this tool can do",
        "trust_can_1": "Estimate ward-level dengue risk 2 to 4 weeks ahead from weather and local conditions.",
        "trust_can_2": "Show whether recent rain, temperature, humidity, drainage, or crowding raises or lowers risk.",
        "trust_can_3": "Help city teams see which wards need inspection and prevention first.",
        "trust_cant_t": "What it cannot do (limits)",
        "trust_cant_1": "It is not medical advice or a diagnostic test; always see a doctor if you have a fever.",
        "trust_cant_2": "It cannot predict exact weekly case numbers with certainty—every forecast is an estimate.",
        "trust_cant_3": "It cannot anticipate sudden weather shifts or unexpected events outside past patterns.",
        "trust_data_t": "Data source and how we tested it",
        "trust_data_b": "Built from {rows} observed weekly records across {w} wards in {c} Bangladesh cities (2016–2025), combining rainfall, temperature, humidity, water-logging, and population density. Accuracy was checked on unseen 2024–2025 weeks.",
        "trust_review_t": "Bangla translation & public-health review",
        "trust_review_b": "Action guidance follows national DGHS dengue protocols. Before public rollout, a native Bangla public-health speaker should review the Bangla wording.",
        "trust_say": "For the {h}-week forecast, typical error is about {err} cases per week. Outbreak weeks caught: {caught} percent. Alerts that were right: {prec} percent. This is an early-warning aid, not a medical diagnosis.",
        # Help & states & footer
        "help_title": "Help / সহায়তা",
        "help_q1": "What is my risk?",
        "help_q2": "What should I do now?",
        "help_q3": "Why this forecast?",
        "help_a1": "In {ward} for the week of {d}, dengue risk is **{risk}**. About **{n} cases** per week are expected (likely range {a}–{b}). This is an estimate.",
        "help_a2": "Steps for {risk}: 1) {p1} 2) {p2} 3) {p3}",
        "help_a3": "This forecast uses weather up to {issue_d} (rain, temperature, humidity) plus local water-logging and crowding. Right now, '{top_drv}' has the largest effect.",
        "loading": "Preparing the forecast...",
        "no_data": "No data for this ward. Please choose another ward.",
        "error": "Something went wrong. Please reload the page.",
        "disclaimer": "This is an early-warning aid, not a medical diagnosis. If you have fever, see a doctor.",
        "footer_meta": "Source: Bangladesh urban dengue & weather surveillance dataset (2016–2025) · Weather up to {date}",
    },
}


def to_bn_digits(value):
    return str(value).translate(BN_DIG)


def fmt_num(value, lang, decimals=1):
    if decimals is None:
        s = str(value)
    else:
        s = f"{float(value):.{decimals}f}"
    return to_bn_digits(s) if lang == "bn" else s


def fmt_date(date_val, lang):
    s = str(date_val)
    return to_bn_digits(s) if lang == "bn" else s


def t(key, lang, **kw):
    text = STRINGS[lang][key]
    if not kw:
        return text
    formatted = text.format(**kw)
    return to_bn_digits(formatted) if lang == "bn" else formatted


def city_label(city, lang):
    return CITY_NAMES[lang].get(city, city)


def ward_label(ward_id, lang):
    parts = ward_id.split("_")
    if len(parts) != 3:
        return ward_id
    corp, _, num_str = parts
    num_int = int(num_str) if num_str.isdigit() else num_str
    if lang == "bn":
        return to_bn_digits(f"{CORP_NAMES['bn'].get(corp, corp)} ওয়ার্ড {num_int}")
    return f"{CORP_NAMES['en'].get(corp, corp)} Ward {num_int}"


def tier_name(tier, lang, short=False):
    mapping = TIER_SHORT if short else TIER_LABELS
    return mapping[lang][tier]


def driver_label(raw_name, lang):
    return DRIVER_LABELS[lang].get(raw_name, raw_name)
