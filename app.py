import os
import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.preprocess import (FEATURE_COLS, classify_risk_tier, derive_features,
                            load_and_engineer_features, local_driver_effects, predict_interval)
from src.train import train_and_evaluate, HORIZONS, TIERS

st.set_page_config(page_title="Urban Dengue Early-Warning System", page_icon="🦟", layout="wide")

st.markdown("""<style>
.block-container{padding-top:1.4rem;max-width:1250px}
.hero{background:linear-gradient(120deg,#0f766e 0%,#14532d 100%);padding:22px 28px;border-radius:14px;margin-bottom:16px}
.hero h1{color:#fff;margin:0;font-size:1.8rem;line-height:1.25}
.hero p{color:#d1fae5;margin:8px 0 0;font-size:1rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #d3e3df;border-left:6px solid #0f766e;border-radius:12px;padding:12px 16px;box-shadow:0 1px 5px rgba(0,0,0,.07)}
.stTabs [data-baseweb="tab"]{font-weight:600;font-size:1rem}
[data-testid="stSidebar"]{border-right:1px solid #cfe0db}
[data-testid="stSidebar"] h2{font-size:1.1rem;color:#0f766e}
[data-testid="stDataFrame"]{border:1px solid #d3e3df;border-radius:10px}
</style>""", unsafe_allow_html=True)

TIER_COLORS = {"Low": "#2e7d32", "Medium": "#f9a825", "High": "#ef6c00", "Critical": "#c62828"}
TIER_ACTIONS = {
    "Low": "Routine vector surveillance and weekly drain inspection.",
    "Medium": "Deploy targeted larvicide teams to stagnant drains and construction sites.",
    "High": "Intensify fogging/larviciding; alert local health clinics to stock IV saline & NS1 kits.",
    "Critical": "Emergency ward mobilization, daily fogging, waste clearance, and hospital surge readiness.",
}
DATA = "data/hackathon_preli_dataset.xlsx"
WEEK = pd.Timedelta(weeks=1)


@st.cache_resource
def get_model_artifact():
    if os.path.exists("models/dengue_model.joblib"):
        try:
            art = joblib.load("models/dengue_model.joblib")
            if "models" in art:
                return art
        except Exception:  # ভার্সন মিলল না বা ফাইল নষ্ট → নিজে থেকে রি-ট্রেইন (~৫ সেকেন্ড)
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
BASELINES = df[FEATURE_COLS].median()  # driver-ব্যাখ্যার 'সাধারণ অবস্থা'

st.markdown(
    "<div class='hero'><h1>🦟 Urban Dengue Outbreak Early-Warning System</h1>"
    "<p>Ward-level forecasts of weekly dengue cases <b>2, 3 and 4 weeks ahead</b> from multi-week "
    "rainfall, temperature and humidity lags, Aedes breeding suitability and ward vulnerability.</p></div>",
    unsafe_allow_html=True)

# ---------------- Sidebar ----------------
st.sidebar.header("1. Target Area & Forecast Window")
selected_city = st.sidebar.selectbox("Select City", sorted(df["city"].unique()), index=0)
city_wards = sorted(df[df["city"] == selected_city]["ward_id"].unique())
selected_ward = st.sidebar.selectbox("Select Ward ID", city_wards, index=0)

ward_df = df[df["ward_id"] == selected_ward].dropna(subset=FEATURE_COLS).sort_values("date")
issue_dates = (ward_df["date"] - 2 * WEEK).dt.strftime("%Y-%m-%d").tolist()  # T = শেষ পর্যবেক্ষিত আবহাওয়া-সপ্তাহ
issue_str = st.sidebar.selectbox("Last observed weather week (forecast issue date)", issue_dates, index=len(issue_dates) - 1)
issue_date = pd.Timestamp(issue_str)
horizon = st.sidebar.radio("Forecast horizon (weeks after that week)", list(HORIZONS), index=0, horizontal=True)
base_row = ward_df[ward_df["date"] == issue_date + 2 * WEEK].iloc[0].copy()
target_date = issue_date + horizon * WEEK

st.sidebar.info(
    f"Weather observed up to **{issue_str}** → forecasts for **{(issue_date + 2*WEEK).date()}**, "
    f"**{(issue_date + 3*WEEK).date()}**, **{(issue_date + 4*WEEK).date()}**. "
    "3- and 4-week models use only older weather, so they are somewhat less accurate (see Validation tab)."
)

st.sidebar.markdown("---")
st.sidebar.header("2. Weather Scenario Simulator")
st.sidebar.caption("Edit the observed weather to test sensitivity (defaults = real observed values):")
sim_rain_2w = st.sidebar.slider("Rainfall, last observed week (mm)", 0.0, 300.0, float(round(base_row["rainfall_lag_2w"], 1)))
sim_rain_3w = st.sidebar.slider("Rainfall, 1 week earlier (mm)", 0.0, 300.0, float(round(base_row["rainfall_lag_3w"], 1)))
sim_rain_4w = st.sidebar.slider("Rainfall, 2 weeks earlier (mm)", 0.0, 300.0, float(round(base_row["rainfall_lag_4w"], 1)))
sim_temp = st.sidebar.slider("Avg Temperature, last 3 weeks (°C)", 15.0, 38.0, float(round(base_row["temp_mean_2_4w"], 1)))
sim_humidity = st.sidebar.slider("Relative Humidity, last 3 weeks (%)", 40.0, 100.0, float(round(base_row["humidity_mean_2_4w"], 1)))

# একই derive_features সূত্র (ট্রেনিং-এর সাথে হুবহু এক)
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

tab1, tab2, tab3 = st.tabs(["🎯 Forecast & Drivers", "🗺️ City Ward Risk Heatmap", "📈 Chronological Validation"])

# ---------------- Tab 1 ----------------
with tab1:
    cols = st.columns(3)
    for col, h in zip(cols, HORIZONS):
        mu, lo, hi, tier = forecasts[h]
        tdate = issue_date + h * WEEK
        actual = df[(df["ward_id"] == selected_ward) & (df["date"] == tdate)]["dengue_cases"]
        actual_txt = f"Actual: {int(actual.iloc[0])}" if len(actual) and pd.notna(actual.iloc[0]) else "Future week"
        col.metric(f"+{h} weeks ({tdate.date()})", f"{mu:.1f} cases/wk", f"80% CI [{lo:.1f}–{hi:.1f}] · {actual_txt}", delta_color="off")
        col.markdown(
            f"<span style='background-color:{TIER_COLORS[tier]};color:white;padding:6px 14px;"
            f"border-radius:6px;font-size:18px;font-weight:bold;'>{tier.upper()}</span>", unsafe_allow_html=True)
    st.info(f"**Recommended action for the +{horizon}-week forecast ({risk_tier}):** {TIER_ACTIONS[risk_tier]}")

    left, right = st.columns(2)
    with left:
        st.subheader("🔍 Model-based Risk Drivers")
        eff = local_driver_effects(artifact["models"][horizon], row, BASELINES)
        eff_df = pd.DataFrame({"Driver": list(eff), "Effect": list(eff.values())}).sort_values("Effect")
        eff_df["Direction"] = np.where(eff_df["Effect"] >= 0, "Raises risk", "Lowers risk")
        fig = px.bar(eff_df, x="Effect", y="Driver", orientation="h", color="Direction",
                     color_discrete_map={"Raises risk": "#c62828", "Lowers risk": "#2e7d32"},
                     title=f"Change in predicted cases vs. typical conditions ({selected_ward}, +{horizon}w)")
        fig.update_layout(height=380, xaxis_title="Δ predicted cases/week")
        st.plotly_chart(fig, width="stretch")
        st.caption("Each bar = how much the trained model's forecast changes if that driver were set to its "
                   "typical (median) value and everything else stayed the same. Rainfall/temperature/humidity use the lag features.")
    with right:
        st.subheader("📊 Rainfall (2–4w lag) vs. Cases — last 52 weeks")
        recent = ward_df[ward_df["date"] <= issue_date + 2 * WEEK].tail(52)
        fig_h = go.Figure()
        fig_h.add_trace(go.Bar(x=recent["date"], y=recent["rainfall_sum_2_4w"], name="Rain in lag window (mm)",
                               marker_color="rgba(54,162,235,0.45)", yaxis="y2"))
        fig_h.add_trace(go.Scatter(x=recent["date"], y=recent["dengue_cases"], name="Weekly cases",
                                   line=dict(color="#c62828", width=2.5)))
        fig_h.update_layout(yaxis=dict(title="Dengue cases"), yaxis2=dict(title="Rain (mm)", overlaying="y", side="right"),
                            legend=dict(orientation="h", y=1.12), height=380)
        st.plotly_chart(fig_h, width="stretch")

# ---------------- Tab 2 ----------------
with tab2:
    st.subheader(f"🗺️ {selected_city} — ward × week risk heatmap (+{horizon}-week forecasts, issue date {issue_str})")
    start = issue_date + 2 * WEEK - 11 * WEEK
    cs = df[(df["city"] == selected_city) & (df["date"] >= start) & (df["date"] <= issue_date + 2 * WEEK)].dropna(subset=FEATURE_COLS).copy()
    if not cs.empty:
        mdl, disp = artifact["models"][horizon], artifact["dispersion"][horizon]
        cs["Predicted_Cases"] = np.clip(mdl.predict(cs[FEATURE_COLS]), 0, None)
        cs["Target_Week"] = (cs["date"] + (horizon - 2) * WEEK).dt.strftime("%Y-%m-%d")
        piv = cs.pivot(index="ward_id", columns="Target_Week", values="Predicted_Cases")
        piv = piv.loc[piv.iloc[:, -1].sort_values(ascending=False).index]
        fig_hm = px.imshow(piv, aspect="auto", color_continuous_scale="YlOrRd",
                           labels=dict(x="Target week", y="Ward", color="Cases/wk"))
        st.plotly_chart(fig_hm, width="stretch")
        latest = cs[cs["date"] == issue_date + 2 * WEEK].copy()
        latest["CI_Low"], latest["CI_High"] = predict_interval(latest["Predicted_Cases"], disp)
        latest["Risk_Tier"] = latest["Predicted_Cases"].apply(classify_risk_tier)
        latest = latest.sort_values("Predicted_Cases", ascending=False)
        st.markdown(f"**Ward priority list for week {(issue_date + horizon * WEEK).date()}**")
        st.dataframe(latest[["ward_id", "Predicted_Cases", "CI_Low", "CI_High", "Risk_Tier", "rainfall_sum_2_4w",
                             "water_logging_risk_index", "population_density_sqkm"]].round(2), width="stretch")
        st.caption("Heatmap shows the model's forecast for each ward and each of the last 12 target weeks "
                   "(real observed weather; the scenario sliders apply to the Forecast tab only).")

# ---------------- Tab 3 ----------------
with tab3:
    st.subheader("📈 Chronological Out-of-Sample Validation (2024–2025 holdout)")
    vh = st.selectbox("Forecast horizon to validate (weeks)", list(HORIZONS), index=list(HORIZONS).index(horizon))
    st.caption(f"Trained strictly on target weeks {artifact['train_range'][vh]}; evaluated on unseen weeks {artifact['test_range'][vh]}. "
               f"80% interval holdout coverage: {artifact['ci_coverage'][vh][1]}% (weeks with ≥3 predicted cases), "
               f"{artifact['ci_coverage'][vh][0]}% overall.")
    st.dataframe(pd.DataFrame(artifact["benchmarks"][vh]).T.reset_index().rename(columns={"index": "Model"}), width="stretch")

    vw = df_val[(df_val["ward_id"] == selected_ward) & (df_val["horizon_weeks"] == vh)].sort_values("date")
    err = vw["dengue_cases"] - vw["predicted_cases"]
    gap = abs(artifact["test_mae"][vh] - artifact["train_mae"][vh])
    m1, m2, m3 = st.columns(3)
    m1.metric(f"{selected_ward} MAE", f"{np.mean(np.abs(err)):.2f} cases/wk")
    m2.metric(f"{selected_ward} RMSE", f"{np.sqrt(np.mean(err ** 2)):.2f} cases/wk")
    m3.metric("Global Train vs Test MAE gap", f"{gap:.3f}", "Low overfit" if gap < 0.15 else "Check overfit", delta_color="off")

    tr = artifact["tier_report"][vh]
    c1, c2 = st.columns([3, 2])
    with c1:
        fig_cm = px.imshow(tr["cm"], x=tr["labels"], y=tr["labels"], text_auto=True, color_continuous_scale="Blues",
                           labels=dict(x="Predicted tier", y="Actual tier", color="Ward-weeks"),
                           title="Risk-tier confusion matrix (all wards, holdout)")
        st.plotly_chart(fig_cm, width="stretch")
    with c2:
        st.markdown("**Per-tier recall (% of real tier caught)**")
        st.dataframe(pd.DataFrame({"Tier": TIERS, "Recall %": [tr["recall"][t] for t in TIERS],
                                   "Share of actual weeks %": [tr["actual_share"][t] for t in TIERS]}), hide_index=True)
        st.metric("High/Critical alert recall", f"{tr['alert_recall']}%")
        st.metric("High/Critical alert precision", f"{tr['alert_precision']}%")
        st.caption("Overall tier accuracy is inflated by the large Low class; alert recall/precision show how well real outbreaks are caught.")

    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=vw["date"], y=vw["ci_high"], mode="lines", line=dict(width=0), showlegend=False))
    fig_v.add_trace(go.Scatter(x=vw["date"], y=vw["ci_low"], mode="lines", line=dict(width=0), fill="tonexty",
                               fillcolor="rgba(239,108,0,0.2)", name="80% interval"))
    fig_v.add_trace(go.Scatter(x=vw["date"], y=vw["dengue_cases"], name="Actual", line=dict(color="#1565c0", width=2)))
    fig_v.add_trace(go.Scatter(x=vw["date"], y=vw["predicted_cases"], name="Predicted", line=dict(color="#ef6c00", width=2, dash="dash")))
    fig_v.update_layout(title=f"Actual vs predicted weekly cases, +{vh}w ({selected_ward})", height=420,
                        xaxis_title="Week", yaxis_title="Weekly cases")
    st.plotly_chart(fig_v, width="stretch")
