import os
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import (mean_absolute_error, root_mean_squared_error, r2_score,
                             accuracy_score, confusion_matrix)
try:
    from preprocess import FEATURE_COLS, classify_risk_tier, load_and_engineer_features, predict_interval
except ImportError:  # app.py থেকে চালালে
    from src.preprocess import FEATURE_COLS, classify_risk_tier, load_and_engineer_features, predict_interval

HORIZONS = (2, 3, 4)          # শেষ পর্যবেক্ষিত আবহাওয়া-সপ্তাহের কত সপ্তাহ পরের কেস
TIERS = ["Low", "Medium", "High", "Critical"]
CUTOFF_VAL, CUTOFF_TEST = "2022-01-01", "2024-01-01"


def make_model(loss, quantile=None, max_iter=100, lr=0.08):
    return HistGradientBoostingRegressor(
        loss=loss, quantile=quantile, max_iter=max_iter, learning_rate=lr,
        max_depth=5, min_samples_leaf=35, l2_regularization=5.0,
        max_bins=64, random_state=42,
    )


def make_horizon_frame(df, horizon):
    """সারি s-এর ফিচার = আবহাওয়া (s-2..s-4)। horizon h হলে টার্গেট = s+(h-2) সপ্তাহের কেস,
    অর্থাৎ ফিচার ও টার্গেটের মধ্যে আসলে h..h+2 সপ্তাহের ল্যাগ থাকে। বিভাজন টার্গেটের তারিখ ধরে (লিকেজ নেই)।"""
    j = horizon - 2
    d = df.copy()
    d["target"] = d.groupby("ward_id")["dengue_cases"].shift(-j)
    d["target_date"] = d["date"] + pd.Timedelta(weeks=j)
    return d.dropna(subset=FEATURE_COLS + ["target"]).reset_index(drop=True)


def interval_coverage(y, mean_pred, dispersion):
    """আসল কেস কত % সময় রেঞ্জের ভেতরে (সব সারি, এবং পূর্বাভাস >= 3 এমন ঝুঁকিপূর্ণ সপ্তাহ)"""
    low, high = predict_interval(mean_pred, dispersion)
    inside = (np.asarray(y) >= low) & (np.asarray(y) <= high)
    risky = np.asarray(mean_pred) >= 3
    return round(float(inside.mean() * 100), 1), round(float(inside[risky].mean() * 100), 1)


def pick_dispersion(hf):
    """শুধু ২০২২–২৩ validation থেকে dispersion বাছে (টেস্ট সেট ছোঁয় না), লক্ষ্য: ঝুঁকিপূর্ণ সপ্তাহে ~80% coverage"""
    tr = hf[hf["target_date"] < CUTOFF_VAL]
    va = hf[(hf["target_date"] >= CUTOFF_VAL) & (hf["target_date"] < CUTOFF_TEST)]
    m = make_model("poisson").fit(tr[FEATURE_COLS], tr["target"])
    mu = np.clip(m.predict(va[FEATURE_COLS]), 0, None)
    grid = [0.01, 0.03, 0.05, 0.07, 0.10, 0.13, 0.16, 0.20]
    return min(grid, key=lambda a: abs(interval_coverage(va["target"], mu, a)[1] - 80))


def tiers_of(values):
    return [classify_risk_tier(v) for v in values]


def tier_accuracy(y_true, y_pred):
    return round(accuracy_score(tiers_of(y_true), tiers_of(y_pred)) * 100, 2)


def scores(y_true, y_pred):
    return {
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "RMSE": round(float(root_mean_squared_error(y_true, y_pred)), 4),
        "R2": round(float(r2_score(y_true, y_pred)), 4),
        "Tier_Accuracy_Pct": float(tier_accuracy(y_true, y_pred)),
    }


def tier_report(y_true, y_pred):
    """Confusion matrix, প্রতি tier-এর recall, এবং High/Critical 'অ্যালার্ট' precision/recall।
    Low ক্লাস বড় বলে শুধু accuracy বিভ্রান্তিকর, তাই এগুলো আলাদা করে দেখানো হয়।"""
    t, p = tiers_of(y_true), tiers_of(y_pred)
    cm = confusion_matrix(t, p, labels=TIERS)
    recall = {k: (round(float(cm[i, i] / cm[i].sum() * 100), 1) if cm[i].sum() else None) for i, k in enumerate(TIERS)}
    t_hi = np.array([x in ("High", "Critical") for x in t]); p_hi = np.array([x in ("High", "Critical") for x in p])
    tp = int((t_hi & p_hi).sum())
    return {
        "labels": TIERS, "cm": cm.tolist(), "recall": recall,
        "actual_share": {k: round(float(np.mean([x == k for x in t]) * 100), 1) for k in TIERS},
        "alert_recall": round(tp / max(int(t_hi.sum()), 1) * 100, 1),
        "alert_precision": round(tp / max(int(p_hi.sum()), 1) * 100, 1),
    }


def train_and_evaluate(data_path="data/hackathon_preli_dataset.xlsx"):
    t0 = time.time()
    os.makedirs("models", exist_ok=True)
    df = load_and_engineer_features(data_path, "models/processed_features_v2.pkl")

    art = {"models": {}, "dispersion": {}, "benchmarks": {}, "ci_coverage": {},
           "tier_report": {}, "train_mae": {}, "test_mae": {}, "feature_cols": FEATURE_COLS}
    val_frames = []
    for h in HORIZONS:
        hf = make_horizon_frame(df, h)
        train_df = hf[hf["target_date"] < CUTOFF_TEST]
        test_df = hf[hf["target_date"] >= CUTOFF_TEST].copy()
        X_train, y_train = train_df[FEATURE_COLS], train_df["target"]
        X_test, y_test = test_df[FEATURE_COLS], test_df["target"]

        dispersion = pick_dispersion(hf)
        model = make_model("poisson").fit(X_train, y_train)
        ridge = Ridge(alpha=1.0).fit(X_train, y_train)
        tr_preds = np.clip(model.predict(X_train), 0, None)
        te_preds = np.clip(model.predict(X_test), 0, None)
        ridge_preds = np.clip(ridge.predict(X_test), 0, None)

        test_df["predicted_cases"] = te_preds
        test_df["ci_low"], test_df["ci_high"] = predict_interval(te_preds, dispersion)
        out = test_df[["target_date", "city", "ward_id", "target", "predicted_cases", "ci_low", "ci_high"]]
        out = out.rename(columns={"target_date": "date", "target": "dengue_cases"})
        out.insert(0, "horizon_weeks", h)
        val_frames.append(out)

        art["models"][h] = model
        art["dispersion"][h] = dispersion
        art["benchmarks"][h] = {
            "Ridge Baseline": scores(y_test, ridge_preds),
            "HistGradientBoosting (Poisson Regularized)": scores(y_test, te_preds),
        }
        art["ci_coverage"][h] = interval_coverage(y_test, te_preds, dispersion)
        art["tier_report"][h] = tier_report(y_test, te_preds)
        art["train_mae"][h] = round(float(mean_absolute_error(y_train, tr_preds)), 4)
        art["test_mae"][h] = round(float(mean_absolute_error(y_test, te_preds)), 4)
        art.setdefault("train_range", {})[h] = f"{train_df['target_date'].min().date()} to {train_df['target_date'].max().date()}"
        art.setdefault("test_range", {})[h] = f"{test_df['target_date'].min().date()} to {test_df['target_date'].max().date()}"
        print(f"h={h}w | {art['benchmarks'][h]['HistGradientBoosting (Poisson Regularized)']} | "
              f"Ridge MAE={art['benchmarks'][h]['Ridge Baseline']['MAE']} | cov(risky)={art['ci_coverage'][h][1]}%")

    pd.concat(val_frames).to_csv("models/validation_results.csv", index=False)
    joblib.dump(art, "models/dengue_model.joblib", compress=0)
    print(f"Training completed in {time.time() - t0:.2f}s")


if __name__ == "__main__":
    train_and_evaluate()
