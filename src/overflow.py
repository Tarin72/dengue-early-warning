"""Feature 2: hospital surge + intra-city overflow routing (deterministic).

Each ward has a bed capacity. Where predicted bed demand > capacity, the overflow
is routed ONLY to wards of the same city, taking the lowest-utilisation ward first.
Outputs: per-ward net deficit, transfer list, city-wide utilisation + headroom.
"""
import numpy as np
import pandas as pd


def ward_capacity(peak_beds, pct=40, override_csv="data/bed_capacity.csv"):
    """Bed capacity per ward. The dataset has no capacity column, so by default
    capacity = pct% of the ward's historical peak weekly bed requirement (floor 2).
    If data/bed_capacity.csv (ward_id, bed_capacity) exists, it overrides the assumption."""
    import os
    cap = {w: int(max(2, round(pct / 100.0 * v))) for w, v in peak_beds.items()}
    if os.path.exists(override_csv):
        o = pd.read_csv(override_csv)
        cap.update(dict(zip(o["ward_id"], o["bed_capacity"].astype(int))))
    return cap


def route_overflow(fc, ratios, capacity, beds_col="pred_peak_week"):
    """fc: forecast table (ward_id, city, pred_*). Beds demand = cases * bed ratio."""
    w = fc[["ward_id", "city", "risk_tier", beds_col]].copy()
    w["beds_demand"] = np.rint(w[beds_col] * ratios["hospital_beds_required"]).astype(int)
    w["capacity"] = w["ward_id"].map(capacity).astype(int)
    w["overflow"] = (w["beds_demand"] - w["capacity"]).clip(lower=0)
    w["headroom"] = (w["capacity"] - w["beds_demand"]).clip(lower=0)
    w["received"] = 0
    # No coordinates in the dataset: "nearest" = closest ward number inside the same city
    # (ward numbers run roughly along the city, so neighbours have neighbouring numbers).
    w["num"] = w["ward_id"].str.extract(r"(\d+)$")[0].astype(int)
    free0 = w["headroom"].copy()

    transfers = []
    for city, grp in w.groupby("city"):
        donors = grp[grp["overflow"] > 0].sort_values("overflow", ascending=False)
        for di, drow in donors.iterrows():
            left = int(drow["overflow"])
            # receivers: same city, NEAREST ward number first, then lowest utilisation
            recv = w[(w["city"] == city) & (w["headroom"] > 0)].copy()
            recv["util"] = (w.loc[recv.index, "beds_demand"] + w.loc[recv.index, "received"]) / recv["capacity"]
            recv["steps"] = (recv["num"] - drow["num"]).abs()
            for ri in recv.sort_values(["steps", "util"]).index:
                if left <= 0:
                    break
                room = int(w.loc[ri, "headroom"])
                move = min(left, room)
                if move <= 0:
                    continue
                transfers.append({"city": city, "from_ward": drow["ward_id"],
                                  "to_ward": w.loc[ri, "ward_id"], "patients": move,
                                  "steps": int(recv.loc[ri, "steps"])})
                w.loc[ri, "headroom"] -= move
                w.loc[ri, "received"] += move
                left -= move
            w.loc[di, "overflow"] = left            # unplaced = net deficit

    w["net_deficit"] = w["overflow"]
    w["final_load"] = np.where(w["beds_demand"] > w["capacity"], w["capacity"], w["beds_demand"]) + w["received"]
    w["final_util_pct"] = (100 * w["final_load"] / w["capacity"]).round(1)
    w["free_now"] = (w["capacity"] - w["final_load"]).clip(lower=0).astype(int)
    w["initial_util_pct"] = (100 * w["beds_demand"] / w["capacity"]).round(1)

    city = w.groupby("city").agg(capacity=("capacity", "sum"), demand=("beds_demand", "sum"),
                                 net_deficit=("net_deficit", "sum")).reset_index()
    city["utilisation_pct"] = (100 * city["demand"] / city["capacity"]).round(1)
    city["headroom_after_routing"] = (city["capacity"] - city["demand"] + city["net_deficit"]).clip(lower=0)
    city["status"] = np.where(city["net_deficit"] > 0, "CITY OVER CAPACITY",
                              np.where(city["utilisation_pct"] > 85, "TIGHT", "OK"))
    t = pd.DataFrame(transfers, columns=["city", "from_ward", "to_ward", "patients", "steps"])

    # nearby seat availability for every ward that ran out of beds (3 nearest wards, same city)
    near = []
    for di, d in w[w["beds_demand"] > w["capacity"]].iterrows():
        cand = w[(w["city"] == d["city"]) & (w.index != di)].copy()
        cand["steps"] = (cand["num"] - d["num"]).abs()
        cand["free_before"] = free0.loc[cand.index]
        cand["free_after"] = w.loc[cand.index, "headroom"]
        for _, r in cand.sort_values(["steps", "ward_id"]).head(3).iterrows():
            near.append({"city": d["city"], "ward": d["ward_id"], "nearby_ward": r["ward_id"],
                         "steps": int(r["steps"]), "capacity": int(r["capacity"]),
                         "free_before": int(r["free_before"]), "free_after": int(r["free_after"])})
    nearby = pd.DataFrame(near, columns=["city", "ward", "nearby_ward", "steps", "capacity",
                                         "free_before", "free_after"])
    return w.sort_values(["city", "ward_id"]).reset_index(drop=True), t, city, nearby


def suggest_beds(wards, ward_id, k=3):
    """Bed finder: own ward if it has a free bed, otherwise the nearest wards (same city)
    that still have free beds, nearest first, most free beds as tie-break."""
    me = wards[wards["ward_id"] == ward_id].iloc[0]
    if me["free_now"] > 0:
        return "own", int(me["free_now"]), pd.DataFrame()
    cand = wards[(wards["city"] == me["city"]) & (wards["ward_id"] != ward_id) & (wards["free_now"] > 0)].copy()
    cand["steps"] = (cand["num"] - me["num"]).abs()
    cand = cand.sort_values(["steps", "free_now"], ascending=[True, False]).head(k)
    return ("nearby" if len(cand) else "none"), 0, cand[["ward_id", "steps", "capacity", "free_now"]]
