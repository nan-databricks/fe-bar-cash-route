# Databricks notebook source
# MAGIC %md
# MAGIC # SNB CIT route optimization — CVRP-TW with OR-Tools
# MAGIC * **OPTIMIZED**: forecast-driven orders (`gold_replenishment_orders`) solved per depot as a
# MAGIC   capacitated VRP with time windows. Objective = km cost + THB 2,500 crew cost per van used,
# MAGIC   with drop penalties so CRITICAL stops are always served.
# MAGIC * **BASELINE**: today's fixed 5-day cycle — every node whose cycle day falls on the service
# MAGIC   date is visited regardless of need, machines are topped up to full, routed nearest-neighbor.
# MAGIC
# MAGIC Both plans are written with the same contract so the app and Genie can compare them.

# COMMAND ----------

# MAGIC %pip install ortools==9.11.4210

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
T = f"{CATALOG}.{SCHEMA}"

import hashlib, json, math, time
from datetime import date
import numpy as np, pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from pyspark.sql import functions as F

SERVICE_DATE = date(2026, 10, 1)
SHIFT_START, SHIFT_END = 7 * 60, 18 * 60
SPEED_KMH, ROAD_FACTOR, CREW_COST_THB = 40.0, 1.3, 2500.0
SOLVER_SECONDS = 25
PENALTY = {"CRITICAL": 10_000_000, "HIGH": 1_000_000, "NORMAL": 100_000}


def road_km(lat1, lng1, lat2, lng2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lng2 - lng1) * p / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a)) * ROAD_FACTOR


def drive_min(km):
    return int(math.ceil(km / SPEED_KMH * 60))


def write(pdf, table, schema):
    sdf = spark.createDataFrame(pdf).select([F.col(c).cast(t).alias(c) for c, t in schema])
    sdf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{T}.{table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Inputs

# COMMAND ----------

orders = spark.table(f"{T}.gold_replenishment_orders").where(F.col("service_date") == F.lit(SERVICE_DATE)).toPandas()
depots = spark.table(f"{T}.silver_depots").toPandas().set_index("depot_id")
vehicles = spark.table(f"{T}.silver_vehicles").toPandas().sort_values("vehicle_id")
status = spark.table(f"{T}.gold_node_status").toPandas()
nodes = spark.table(f"{T}.gold_cash_nodes").select("node_id", "open_min", "close_min").toPandas()
fc = spark.table(f"{T}.gold_demand_forecast").toPandas()
if orders.empty:
    raise ValueError("No replenishment orders for the service date; run 03_score_orders first.")
need3 = fc[fc.horizon_day <= 3].groupby("node_id").pred_net_outflow_thb.sum().clip(lower=0).rename("need_3d")
p80_d1 = fc[fc.horizon_day == 1].set_index("node_id").pred_p80_thb.rename("p80_d1")
print(f"orders={len(orders)} vehicles={len(vehicles)} nodes={len(status)}")
print(orders.groupby(["depot_id", "priority"]).size().unstack(fill_value=0).to_string())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. OPTIMIZED plan — OR-Tools CVRP-TW per depot
# MAGIC Capacity is measured in THB thousands and counts deliveries and pickups (cash on board).
# MAGIC Guided local search runs for ~25 s per depot.

# COMMAND ----------

def solve_depot(depot_id, sub, fleet):
    sub, fleet = sub.reset_index(drop=True), fleet.reset_index(drop=True)
    dep = depots.loc[depot_id]
    pts = [(dep.lat, dep.lng)] + list(zip(sub.lat, sub.lng))
    n = len(pts)
    km = np.array([[road_km(*pts[i], *pts[j]) for j in range(n)] for i in range(n)])
    service = [0] + sub.service_min.astype(int).tolist()
    travel = [[drive_min(km[i][j]) + service[i] for j in range(n)] for i in range(n)]
    load = [0] + np.ceil(sub.amount_thb.abs() / 1000).astype(int).tolist()

    mgr = pywrapcp.RoutingIndexManager(n, len(fleet), 0)
    rt = pywrapcp.RoutingModel(mgr)
    for v, veh in fleet.iterrows():
        rate = float(veh.cost_per_km_thb)
        cb = rt.RegisterTransitCallback(lambda i, j, rate=rate: int(round(km[mgr.IndexToNode(i)][mgr.IndexToNode(j)] * rate)))
        rt.SetArcCostEvaluatorOfVehicle(cb, v)
    rt.SetFixedCostOfAllVehicles(int(CREW_COST_THB))

    load_cb = rt.RegisterUnaryTransitCallback(lambda i: load[mgr.IndexToNode(i)])
    rt.AddDimensionWithVehicleCapacity(load_cb, 0, np.floor(fleet.cash_capacity_thb / 1000).astype(int).tolist(), True, "Cash")
    time_cb = rt.RegisterTransitCallback(lambda i, j: travel[mgr.IndexToNode(i)][mgr.IndexToNode(j)])
    rt.AddDimension(time_cb, 300, SHIFT_END, False, "Time")
    td = rt.GetDimensionOrDie("Time")
    for k, r in sub.iterrows():
        idx = mgr.NodeToIndex(k + 1)
        td.CumulVar(idx).SetRange(max(SHIFT_START, int(r.tw_start_min)), min(SHIFT_END, int(r.tw_end_min)))
        rt.AddDisjunction([idx], PENALTY.get(r.priority, 100_000))
    for v in range(len(fleet)):
        td.CumulVar(rt.Start(v)).SetRange(SHIFT_START, SHIFT_END)
        td.CumulVar(rt.End(v)).SetRange(SHIFT_START, SHIFT_END)
        rt.AddVariableMaximizedByFinalizer(td.CumulVar(rt.Start(v)))
        rt.AddVariableMinimizedByFinalizer(td.CumulVar(rt.End(v)))

    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.FromSeconds(SOLVER_SECONDS)
    sol = rt.SolveWithParameters(prm)
    if sol is None:
        raise RuntimeError(f"No feasible solution for {depot_id}")

    stops, routes = [], []
    for v, veh in fleet.iterrows():
        idx = rt.Start(v)
        if rt.IsEnd(sol.Value(rt.NextVar(idx))):
            continue
        rid = f"OPT-{depot_id}-{veh.vehicle_id}"
        start = sol.Value(td.CumulVar(idx))
        prev, cum, seq, dlv, col = 0, 0.0, 0, 0.0, 0.0
        idx = sol.Value(rt.NextVar(idx))
        while not rt.IsEnd(idx):
            node = mgr.IndexToNode(idx)
            r = sub.iloc[node - 1]
            cum += km[prev][node]
            seq += 1
            dlv += r.amount_thb if r.action == "DELIVER" else 0.0
            col += r.amount_thb if r.action == "PICKUP" else 0.0
            stops.append(dict(service_date=SERVICE_DATE, plan_type="OPTIMIZED", route_id=rid, vehicle_id=veh.vehicle_id,
                              depot_id=depot_id, stop_seq=seq, node_id=r.node_id, node_type=r.node_type,
                              node_name=r.node_name, action=r.action, amount_thb=float(r.amount_thb),
                              eta_min=int(sol.Value(td.CumulVar(idx))), lat=float(r.lat), lng=float(r.lng),
                              cum_km=round(cum, 2)))
            prev, idx = node, sol.Value(rt.NextVar(idx))
        cum += km[prev][0]
        end = sol.Value(td.CumulVar(idx))
        routes.append(dict(service_date=SERVICE_DATE, plan_type="OPTIMIZED", route_id=rid, depot_id=depot_id,
                           vehicle_id=veh.vehicle_id, stops=seq, km=round(cum, 2), duration_min=float(end - start),
                           cash_delivered_thb=dlv, cash_collected_thb=col,
                           cost_thb=round(cum * float(veh.cost_per_km_thb) + CREW_COST_THB, 2),
                           start_min=int(start), end_min=int(end)))
    return stops, routes


opt_stops, opt_routes = [], []
for depot_id in sorted(orders.depot_id.unique()):
    t0 = time.time()
    sub = orders[orders.depot_id == depot_id]
    s, r = solve_depot(depot_id, sub, vehicles[vehicles.depot_id == depot_id])
    opt_stops += s
    opt_routes += r
    print(f"{depot_id}: {len(sub)} orders -> {len(s)} stops on {len(r)} vans "
          f"({sum(x['km'] for x in r):.1f} km) in {time.time() - t0:.1f}s; dropped={len(sub) - len(s)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. BASELINE plan — fixed 5-day cycle, nearest-neighbor
# MAGIC Each node has a fixed cycle slot (hash of node_id mod 5). On the service date every node in
# MAGIC that slot is visited: machines are topped up to full cassette, branches to min cash + 7 days
# MAGIC of average outflow, over-full RCMs/branches have their excess collected. Nodes not on the
# MAGIC cycle are not visited, even if they are about to cash out.

# COMMAND ----------

slot = (SERVICE_DATE - date(2025, 4, 1)).days % 5
cand = status.merge(nodes, on="node_id")
cand = cand[cand.node_id.map(lambda x: int(hashlib.md5(x.encode()).hexdigest(), 16) % 5) == slot].copy()
over = cand.node_type.isin(["RCM", "BRANCH"]) & (cand.current_cash_thb > 0.85 * cand.capacity_thb)
target = np.where(cand.node_type == "BRANCH",
                  np.minimum(cand.capacity_thb, cand.min_cash_thb + 7 * cand.avg_daily_outflow_28d),
                  cand.capacity_thb)
cand["action"] = np.where(over, "PICKUP", "DELIVER")
cand["amount_thb"] = np.round(np.where(over, cand.current_cash_thb - 0.85 * cand.capacity_thb,
                                       np.clip(target - cand.current_cash_thb, 0, None)) / 1000) * 1000
branch = cand.node_type == "BRANCH"
cand["tw_start_min"] = np.where(branch, cand.open_min, 480)
cand["tw_end_min"] = np.where(branch, cand.close_min, 1080)
cand["service_min"] = np.where(branch, 25, 15)


def nearest_neighbor(depot_id, todo, fleet):
    dep = depots.loc[depot_id]
    todo = todo.copy()
    stops, routes = [], []
    for _, veh in fleet.iterrows():
        if todo.empty:
            break
        rid = f"BASE-{depot_id}-{veh.vehicle_id}"
        pos, clock, cum, room, seq, dlv, col = (dep.lat, dep.lng), SHIFT_START, 0.0, float(veh.cash_capacity_thb), 0, 0.0, 0.0
        while not todo.empty:
            d = todo.apply(lambda r: road_km(pos[0], pos[1], r.lat, r.lng), axis=1)
            k = d.idxmin()
            r = todo.loc[k]
            arrive = max(clock + drive_min(d[k]), int(r.tw_start_min))
            back = road_km(r.lat, r.lng, dep.lat, dep.lng)
            if abs(r.amount_thb) > room or arrive > r.tw_end_min or arrive + r.service_min + drive_min(back) > SHIFT_END:
                break
            seq += 1
            cum += d[k]
            room -= abs(r.amount_thb)
            dlv += r.amount_thb if r.action == "DELIVER" else 0.0
            col += r.amount_thb if r.action == "PICKUP" else 0.0
            stops.append(dict(service_date=SERVICE_DATE, plan_type="BASELINE", route_id=rid, vehicle_id=veh.vehicle_id,
                              depot_id=depot_id, stop_seq=seq, node_id=r.node_id, node_type=r.node_type,
                              node_name=r.node_name, action=r.action, amount_thb=float(r.amount_thb), eta_min=int(arrive),
                              lat=float(r.lat), lng=float(r.lng), cum_km=round(cum, 2)))
            clock, pos = arrive + int(r.service_min), (r.lat, r.lng)
            todo = todo.drop(k)
        if seq:
            last = road_km(pos[0], pos[1], dep.lat, dep.lng)
            cum += last
            end = clock + drive_min(last)
            routes.append(dict(service_date=SERVICE_DATE, plan_type="BASELINE", route_id=rid, depot_id=depot_id,
                               vehicle_id=veh.vehicle_id, stops=seq, km=round(cum, 2), duration_min=float(end - SHIFT_START),
                               cash_delivered_thb=dlv, cash_collected_thb=col,
                               cost_thb=round(cum * float(veh.cost_per_km_thb) + CREW_COST_THB, 2),
                               start_min=SHIFT_START, end_min=int(end)))
    return stops, routes, len(todo)


base_stops, base_routes = [], []
for depot_id in sorted(cand.depot_id.unique()):
    s, r, left = nearest_neighbor(depot_id, cand[cand.depot_id == depot_id], vehicles[vehicles.depot_id == depot_id])
    base_stops += s
    base_routes += r
    print(f"{depot_id}: cycle nodes={int((cand.depot_id == depot_id).sum())} -> {len(s)} stops on {len(r)} vans; unrouted={left}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Write routes and stops (CDF on for the Lakebase synced table)

# COMMAND ----------

routes_pdf = pd.DataFrame(base_routes + opt_routes)
stops_pdf = pd.DataFrame(base_stops + opt_stops)
pk = ["service_date", "plan_type", "route_id", "stop_seq"]
assert not stops_pdf.duplicated(pk).any(), "gold_route_stops primary key is not unique"

write(routes_pdf, "gold_routes", [
    ("service_date", "date"), ("plan_type", "string"), ("route_id", "string"), ("depot_id", "string"),
    ("vehicle_id", "string"), ("stops", "int"), ("km", "double"), ("duration_min", "double"),
    ("cash_delivered_thb", "double"), ("cash_collected_thb", "double"), ("cost_thb", "double"),
    ("start_min", "int"), ("end_min", "int")])
write(stops_pdf, "gold_route_stops", [
    ("service_date", "date"), ("plan_type", "string"), ("route_id", "string"), ("vehicle_id", "string"),
    ("depot_id", "string"), ("stop_seq", "int"), ("node_id", "string"), ("node_type", "string"),
    ("node_name", "string"), ("action", "string"), ("amount_thb", "double"), ("eta_min", "int"),
    ("lat", "double"), ("lng", "double"), ("cum_km", "double")])
spark.sql(f"ALTER TABLE {T}.gold_route_stops SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Plan KPIs → `gold_route_summary`
# MAGIC * **idle_cash_thb**: cash left in nodes after the plan above min cash + 3 days of forecast demand.
# MAGIC * **cashout_risk_nodes**: nodes under 1 day to cash-out (P80) that get no delivery.
# MAGIC * **sla_pct**: share of CRITICAL/HIGH orders served inside their time window.

# COMMAND ----------

risk = status.set_index("node_id").join(need3).join(p80_d1)
risk["days"] = (risk.current_cash_thb - risk.min_cash_thb) / risk.p80_d1.clip(lower=1000.0)
urgent = orders[orders.priority.isin(["CRITICAL", "HIGH"])].set_index("node_id")
summary = []
for plan, rts in [("BASELINE", routes_pdf[routes_pdf.plan_type == "BASELINE"]),
                  ("OPTIMIZED", routes_pdf[routes_pdf.plan_type == "OPTIMIZED"])]:
    st = stops_pdf[stops_pdf.plan_type == plan].set_index("node_id")
    signed = st.amount_thb.where(st.action == "DELIVER", -st.amount_thb).groupby(level=0).sum()
    after = risk.current_cash_thb.add(signed, fill_value=0)
    idle = float((after - risk.min_cash_thb - risk.need_3d.fillna(0)).clip(lower=0).sum())
    delivered = set(st[(st.action == "DELIVER") & (st.amount_thb > 0)].index)
    cashout = int(((risk.days < 1) & ~risk.index.isin(delivered)).sum())
    served = st.join(urgent[["tw_start_min", "tw_end_min"]], how="inner")
    on_time = served[(served.eta_min >= served.tw_start_min) & (served.eta_min <= served.tw_end_min)].index.nunique()
    summary.append(dict(service_date=SERVICE_DATE, plan_type=plan, routes=len(rts), vehicles_used=rts.vehicle_id.nunique(),
                        stops=int(rts.stops.sum()), km=round(float(rts.km.sum()), 1),
                        duration_hr=round(float(rts.duration_min.sum()) / 60, 1), cost_thb=round(float(rts.cost_thb.sum()), 0),
                        idle_cash_thb=round(idle, 0), cashout_risk_nodes=cashout,
                        sla_pct=round(100.0 * on_time / max(len(urgent), 1), 1)))
summary_pdf = pd.DataFrame(summary)
write(summary_pdf, "gold_route_summary", [
    ("service_date", "date"), ("plan_type", "string"), ("routes", "int"), ("vehicles_used", "int"), ("stops", "int"),
    ("km", "double"), ("duration_hr", "double"), ("cost_thb", "double"), ("idle_cash_thb", "double"),
    ("cashout_risk_nodes", "int"), ("sla_pct", "double")])

b, o = summary_pdf.set_index("plan_type").loc["BASELINE"], summary_pdf.set_index("plan_type").loc["OPTIMIZED"]
print(f"{'KPI':22} {'BASELINE':>16} {'OPTIMIZED':>16} {'change':>9}")
for k in ["cost_thb", "km", "vehicles_used", "stops", "duration_hr", "idle_cash_thb", "cashout_risk_nodes", "sla_pct"]:
    chg = f"{(o[k] - b[k]) / b[k] * 100:+.1f}%" if b[k] else "n/a"
    print(f"{k:22} {b[k]:>16,.1f} {o[k]:>16,.1f} {chg:>9}")
dbutils.notebook.exit(json.dumps(summary_pdf.assign(service_date=str(SERVICE_DATE)).to_dict(orient="records"), default=float))
