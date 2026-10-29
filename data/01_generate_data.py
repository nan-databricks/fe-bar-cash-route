# Databricks notebook source
# MAGIC %pip install pandas numpy

# COMMAND ----------

import os
import shutil
from datetime import date

import numpy as np
import pandas as pd

dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
raw_root = f"/Volumes/{catalog}/{schema}/raw"

SEED = 42026
rng = np.random.default_rng(SEED)
dates = pd.date_range("2025-04-01", "2026-09-30", freq="D")

for entity in ["depots", "vehicles", "branches", "machines", "calendar",
               "machine_daily", "branch_daily", "cit_trips"]:
    path = f"{raw_root}/{entity}"
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)

def write_parts(frame, entity, parts=1):
    """Write deterministic CSV parts with headers for Auto Loader."""
    folder = f"{raw_root}/{entity}"
    for i, part in enumerate(np.array_split(frame, parts)):
        part.to_csv(f"{folder}/part-{i:03d}.csv", index=False)

def dist_km(lat1, lng1, lat2, lng2):
    return np.sqrt(((lat1 - lat2) * 111.0) ** 2 + ((lng1 - lng2) * 106.5) ** 2)

# COMMAND ----------

depots = pd.DataFrame([
    ["DEP-KKN-C", "SNB Khon Kaen Central Cash Centre", "Mueang Khon Kaen", 16.441, 102.835, 220_000_000],
    ["DEP-KKN-N", "SNB Khon Kaen North Cash Centre", "Nam Phong", 16.708, 102.766, 150_000_000],
    ["DEP-KKN-S", "SNB Khon Kaen South Cash Centre", "Ban Haet", 16.195, 102.900, 150_000_000],
], columns=["depot_id", "depot_name", "district", "lat", "lng", "vault_capacity_thb"])

thai_given = ["Anan", "Boonmee", "Chai", "Dao", "Kanya", "Mali", "Niran", "Pim", "Somchai", "Suda"]
thai_family = ["Chantarat", "Inthara", "Kittisak", "Maneewong", "Panyasri", "Rattanakul", "Sombun", "Wichai"]
vehicles = []
for i in range(30):
    depot = depots.iloc[i % 3].depot_id
    vehicles.append([
        f"VAN-{i + 1:02d}", depot, "ARMORED_VAN", int(rng.integers(7_000_000, 11_000_001)),
        28.0, 2, f"{thai_given[i % len(thai_given)]} {thai_family[(i * 3) % len(thai_family)]}",
        f"08{rng.integers(10000000, 99999999)}",
    ])
vehicles = pd.DataFrame(vehicles, columns=[
    "vehicle_id", "depot_id", "vehicle_type", "cash_capacity_thb", "cost_per_km_thb",
    "crew_size", "custodian_name", "custodian_phone",
])

districts = ["Mueang Khon Kaen", "Nam Phong", "Ban Haet", "Chum Phae", "Mancha Khiri", "Phon", "Ban Phai"]
branch_rows = []
for i in range(159):
    # Cluster primarily within 60km of the city, retaining credible province-wide variety.
    radius = rng.uniform(2, 59)
    angle = rng.uniform(0, 2 * np.pi)
    lat = 16.43 + radius * np.cos(angle) / 111
    lng = 102.83 + radius * np.sin(angle) / (111 * np.cos(np.deg2rad(16.43)))
    ds = depots.assign(_distance=depots.apply(lambda x: dist_km(lat, lng, x.lat, x.lng), axis=1))
    nearest = ds.loc[ds._distance.idxmin()]
    branch_rows.append([
        f"SNB-B{i + 1:03d}", f"SNB {districts[i % len(districts)]} Service Branch {i + 1:03d}",
        districts[i % len(districts)], nearest.depot_id, round(lat, 6), round(lng, 6),
        int(rng.integers(9_000_000, 19_000_001)), int(rng.integers(1_800_000, 3_500_001)),
        int(rng.integers(480, 541)), int(rng.integers(960, 1141)),
    ])
branches = pd.DataFrame(branch_rows, columns=[
    "branch_id", "branch_name", "district", "depot_id", "lat", "lng", "vault_capacity_thb",
    "min_cash_thb", "open_min", "close_min",
])

machine_rows = []
for i in range(520):
    b = branches.iloc[i % len(branches)]
    machine_type = "ATM" if i < 400 else "RCM"
    # Machines are near a branch, including synthetic retail/mall sites.
    lat, lng = b.lat + rng.normal(0, 0.006), b.lng + rng.normal(0, 0.007)
    mid = f"SNB-A{i + 1:04d}" if machine_type == "ATM" else f"SNB-R{i - 399:04d}"
    site = f"{b.district} {'Retail Point' if i % 3 else 'Mall'} {i + 1:03d}"
    machine_rows.append([
        mid, machine_type, site, b.district, b.depot_id, round(lat, 6), round(lng, 6),
        2_000_000 if machine_type == "ATM" else 3_500_000,
        350_000 if machine_type == "ATM" else 600_000,
    ])
machines = pd.DataFrame(machine_rows, columns=[
    "machine_id", "machine_type", "site_name", "district", "depot_id", "lat", "lng",
    "cassette_capacity_thb", "min_cash_thb",
])

write_parts(depots, "depots")
write_parts(vehicles, "vehicles")
write_parts(branches, "branches")
write_parts(machines, "machines")

# COMMAND ----------

holiday_map = {
    "2025-04-06": "Chakri Memorial Day", "2025-04-13": "Songkran Festival",
    "2025-04-14": "Songkran Festival", "2025-04-15": "Songkran Festival",
    "2025-05-01": "Labour Day", "2025-07-28": "Royal Birthday",
    "2025-08-12": "Mother's Day", "2025-10-13": "Memorial Day",
    "2025-12-05": "National Day", "2025-12-10": "Constitution Day",
    "2025-12-31": "New Year's Eve", "2026-01-01": "New Year",
    "2026-04-13": "Songkran Festival", "2026-04-14": "Songkran Festival",
    "2026-04-15": "Songkran Festival", "2026-05-01": "Labour Day",
    "2026-07-28": "Royal Birthday", "2026-08-12": "Mother's Day",
}
calendar = pd.DataFrame({"cal_date": dates})
calendar["dow"] = calendar.cal_date.dt.dayofweek + 1
calendar["is_weekend"] = calendar.dow >= 6
calendar["holiday_name"] = calendar.cal_date.dt.strftime("%Y-%m-%d").map(holiday_map).fillna("")
calendar["is_holiday"] = calendar.holiday_name.ne("")
calendar["is_payday"] = (calendar.cal_date.dt.day >= 25) | (calendar.cal_date.dt.day == 1)
calendar = calendar[["cal_date", "dow", "is_weekend", "is_holiday", "holiday_name", "is_payday"]]
calendar["cal_date"] = calendar.cal_date.dt.strftime("%Y-%m-%d")
write_parts(calendar, "calendar")

# COMMAND ----------

calendar_idx = pd.DataFrame({"txn_date": dates})
calendar_idx["dow"] = calendar_idx.txn_date.dt.dayofweek
calendar_idx["weekend"] = calendar_idx.dow >= 5
calendar_idx["payday"] = (calendar_idx.txn_date.dt.day >= 25) | (calendar_idx.txn_date.dt.day == 1)
calendar_idx["holiday"] = calendar_idx.txn_date.dt.strftime("%Y-%m-%d").isin(holiday_map)
calendar_idx["season"] = 1 + np.where(calendar_idx.txn_date.dt.month.isin([4, 12]), 0.20, 0)
calendar_idx["factor"] = (1 + 0.10 * calendar_idx.weekend + 0.35 * calendar_idx.payday
                          + 0.18 * calendar_idx.holiday) * calendar_idx.season

def make_machine_history():
    records = []
    # Fixed five-day history naturally creates cash-out events and avoidable idle cash.
    for ix, node in machines.iterrows():
        base = rng.uniform(55_000, 135_000) if node.machine_type == "ATM" else rng.uniform(75_000, 180_000)
        cap, min_cash = node.cassette_capacity_thb, node.min_cash_thb
        cash = float(rng.uniform(cap * 0.55, cap * 0.95))
        cycle_offset = ix % 5
        for day_ix, d in calendar_idx.iterrows():
            withdrawal = max(5_000, base * d.factor * rng.lognormal(0, 0.16))
            deposit = (withdrawal * rng.uniform(0.02, 0.12) if node.machine_type == "ATM"
                       else withdrawal * rng.uniform(0.30, 0.75))
            # Do not replenish the planning-date history on 30 Sep; ensure actionable nodes.
            scheduled = (day_ix + cycle_offset) % 5 == 0 and day_ix < len(calendar_idx) - 1
            replenished = max(0, cap * rng.uniform(0.77, 0.93) - cash + withdrawal - deposit) if scheduled else 0
            cash = min(cap, max(0, cash - withdrawal + deposit + replenished))
            cashout = cash < min_cash
            records.append([node.machine_id, d.txn_date.strftime("%Y-%m-%d"), round(withdrawal, 2),
                            round(deposit, 2), round(replenished, 2), round(cash, 2), bool(cashout)])
    return pd.DataFrame(records, columns=[
        "machine_id", "txn_date", "withdrawals_thb", "deposits_thb", "replenished_thb",
        "closing_cash_thb", "cash_out_flag",
    ])

def make_branch_history():
    records = []
    for ix, node in branches.iterrows():
        base = rng.uniform(250_000, 700_000)
        cap, min_cash = node.vault_capacity_thb, node.min_cash_thb
        cash = float(rng.uniform(cap * 0.45, cap * 0.80))
        cycle_offset = (ix + 2) % 5
        for day_ix, d in calendar_idx.iterrows():
            outflow = max(10_000, base * d.factor * rng.lognormal(0, 0.14))
            inflow = outflow * rng.uniform(0.52, 0.96)
            scheduled = (day_ix + cycle_offset) % 5 == 0 and day_ix < len(calendar_idx) - 1
            delivered = max(0, cap * rng.uniform(0.65, 0.85) - cash + outflow - inflow) if scheduled else 0
            collected = max(0, cash + inflow - outflow - cap * 0.82) if scheduled else 0
            cash = min(cap, max(0, cash + inflow - outflow + delivered - collected))
            records.append([node.branch_id, d.txn_date.strftime("%Y-%m-%d"), round(inflow, 2),
                            round(outflow, 2), round(delivered, 2), round(collected, 2), round(cash, 2)])
    return pd.DataFrame(records, columns=[
        "branch_id", "txn_date", "inflow_thb", "outflow_thb", "delivered_thb", "collected_thb",
        "closing_vault_thb",
    ])

machine_daily = make_machine_history()
branch_daily = make_branch_history()

# Make the plan-date snapshot decisively actionable but still variable: 75 low-cash nodes.
last_day = "2026-09-30"
all_nodes = [(x.machine_id, "machine") for _, x in machines.iterrows()] + [(x.branch_id, "branch") for _, x in branches.iterrows()]
urgent = set(rng.choice(np.arange(len(all_nodes)), size=75, replace=False))
for index in urgent:
    node_id, kind = all_nodes[index]
    if kind == "machine":
        minimum = float(machines.loc[machines.machine_id == node_id, "min_cash_thb"].iloc[0])
        mask = (machine_daily.machine_id == node_id) & (machine_daily.txn_date == last_day)
        machine_daily.loc[mask, "closing_cash_thb"] = round(minimum * rng.uniform(0.10, 0.55), 2)
        machine_daily.loc[mask, "cash_out_flag"] = True
    else:
        minimum = float(branches.loc[branches.branch_id == node_id, "min_cash_thb"].iloc[0])
        mask = (branch_daily.branch_id == node_id) & (branch_daily.txn_date == last_day)
        branch_daily.loc[mask, "closing_vault_thb"] = round(minimum * rng.uniform(0.15, 0.65), 2)

write_parts(machine_daily, "machine_daily", parts=6)
write_parts(branch_daily, "branch_daily", parts=3)

# COMMAND ----------

trip_rows = []
for d_ix, d in calendar_idx.iterrows():
    # Historical fixed-cycle fleet plan: weekdays typically 26, weekends 22; extra payday coverage.
    vans = int(np.clip(24 + (0 if d.weekend else 3) + (2 if d.payday else 0) + rng.integers(-2, 3), 22, 28))
    active_vehicles = vehicles.sample(vans, random_state=SEED + d_ix).reset_index(drop=True)
    for seq, vehicle in active_vehicles.iterrows():
        stops = int(rng.integers(8, 16))
        km = float(rng.uniform(70, 175))
        duration = km / rng.uniform(30, 42) * 60 + stops * rng.uniform(9, 14)
        crew_cost = float(vehicle.crew_size * duration / 60 * 180)
        trip_rows.append([
            f"TRIP-{d.txn_date:%Y%m%d}-{seq + 1:02d}", d.txn_date.strftime("%Y-%m-%d"), vehicle.depot_id,
            vehicle.vehicle_id, stops, round(km, 2), round(duration, 1), round(km * 28 + crew_cost, 2),
        ])
cit_trips = pd.DataFrame(trip_rows, columns=[
    "trip_id", "service_date", "depot_id", "vehicle_id", "stops", "km", "duration_min", "cost_thb",
])
write_parts(cit_trips, "cit_trips", parts=3)

counts = {
    "depots": len(depots), "vehicles": len(vehicles), "branches": len(branches), "machines": len(machines),
    "calendar": len(calendar), "machine_daily": len(machine_daily), "branch_daily": len(branch_daily),
    "cit_trips": len(cit_trips),
}
print("Synthetic SNB raw data generated at", raw_root)
for name, count in counts.items():
    print(f"{name}: {count:,}")
print("urgent nodes on 2026-09-30:", len(urgent))
