# Databricks notebook source
# MAGIC %md
# MAGIC # SNB CIT CVRP-TW optimization
# MAGIC Optimizes independently per depot with OR-Tools.  A fixed-cycle nearest-neighbor
# MAGIC baseline is retained with the same output contract for operational comparison.

# COMMAND ----------

# MAGIC %pip install ortools==9.11.4210 pandas numpy
# COMMAND ----------
dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "stable_classic_nan_fe_vm_catalog")
dbutils.widgets.text("schema", "snb_cash_ops")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
T, SERVICE_DATE = f"{CATALOG}.{SCHEMA}", "2026-10-01"
import math, time, hashlib
import numpy as np, pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

SHIFT_START, SHIFT_END, SPEED_KMH, ROAD_FACTOR = 420, 1080, 40.0, 1.3
CREW_COST = 2500.0
def hav(a,b,c,d):
    p = math.pi / 180; x=(c-a)*p; y=(d-b)*p
    z=math.sin(x/2)**2+math.cos(a*p)*math.cos(c*p)*math.sin(y/2)**2
    return 6371*2*math.asin(math.sqrt(z))*ROAD_FACTOR
def matrix(coords):
    n=len(coords); out=np.zeros((n,n))
    for i in range(n):
        for j in range(i+1,n): out[i,j]=out[j,i]=hav(*coords[i],*coords[j])
    return out

orders = spark.table(f"{T}.gold_replenishment_orders").where(f"service_date = DATE '{SERVICE_DATE}'").toPandas()
depots = spark.table(f"{T}.silver_depots").toPandas().set_index("depot_id")
vehicles = spark.table(f"{T}.silver_vehicles").toPandas()
status = spark.table(f"{T}.gold_node_status").toPandas()
if orders.empty: raise ValueError("No replenishment orders; run 03_score_orders first.")
print(f"Optimizing {len(orders)} orders across {orders.depot_id.nunique()} depots")

# COMMAND ----------

# MAGIC %md
# MAGIC ## OR-Tools CVRP-TW solver (capacity in THB thousands)

# COMMAND ----------

def optimize(depot_id, sub, fleet):
    if sub.empty or fleet.empty: return [], []
    sub=sub.reset_index(drop=True); fleet=fleet.reset_index(drop=True)
    coords=[(depots.loc[depot_id].lat,depots.loc[depot_id].lng)]+list(zip(sub.lat,sub.lng))
    km=matrix(coords); travel=np.ceil(km/SPEED_KMH*60).astype(int)
    manager=pywrapcp.RoutingIndexManager(len(coords),len(fleet),0); routing=pywrapcp.RoutingModel(manager)
    transit=routing.RegisterTransitCallback(lambda i,j: int(travel[manager.IndexToNode(i),manager.IndexToNode(j)] + (0 if manager.IndexToNode(i)==0 else sub.iloc[manager.IndexToNode(i)-1].service_min)))
    routing.SetArcCostEvaluatorOfAllVehicles(transit)
    demand=[0]+np.ceil(sub.amount_thb.abs()/1000).astype(int).tolist()
    didx=routing.RegisterUnaryTransitCallback(lambda i: demand[manager.IndexToNode(i)])
    routing.AddDimensionWithVehicleCapacity(didx,0,np.ceil(fleet.cash_capacity_thb/1000).astype(int).tolist(),True,"Cash")
    routing.AddDimension(transit,60,SHIFT_END,False,"Time"); td=routing.GetDimensionOrDie("Time")
    for n in range(1,len(coords)):
        r=sub.iloc[n-1]; td.CumulVar(manager.NodeToIndex(n)).SetRange(max(SHIFT_START,int(r.tw_start_min)),min(SHIFT_END,int(r.tw_end_min)))
        routing.AddDisjunction([manager.NodeToIndex(n)], 100000000 if r.priority=="CRITICAL" else (10000000 if r.priority=="HIGH" else 1000000))
    for v in range(len(fleet)):
        td.CumulVar(routing.Start(v)).SetRange(SHIFT_START,SHIFT_START)
        td.CumulVar(routing.End(v)).SetRange(SHIFT_START,SHIFT_END)
    prm=pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    prm.local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.seconds=25
    sol=routing.SolveWithParameters(prm)
    if not sol: return [], []
    stop_rows=[]; route_rows=[]
    for v in range(len(fleet)):
        idx=routing.Start(v); prev=0; seq=1; cumul=0.; delivered=collected=0.; used=False
        rid=f"OPT-{depot_id}-{fleet.iloc[v].vehicle_id}"
        while not routing.IsEnd(idx):
            n=manager.IndexToNode(idx)
            if n:
                used=True; r=sub.iloc[n-1]; cumul+=km[prev,n]
                delivered += r.amount_thb if r.action=="DELIVER" else 0
                collected += r.amount_thb if r.action=="PICKUP" else 0
                stop_rows.append(dict(service_date=SERVICE_DATE,plan_type="OPTIMIZED",route_id=rid,vehicle_id=fleet.iloc[v].vehicle_id,depot_id=depot_id,stop_seq=seq,node_id=r.node_id,node_type=r.node_type,node_name=r.node_name,action=r.action,amount_thb=float(r.amount_thb),eta_min=int(sol.Value(td.CumulVar(idx))),lat=float(r.lat),lng=float(r.lng),cum_km=float(cumul)))
                seq+=1
            prev=n; idx=sol.Value(routing.NextVar(idx))
        if used:
            cumul+=km[prev,0]; end=int(sol.Value(td.CumulVar(idx))); cost=cumul*float(fleet.iloc[v].cost_per_km_thb)+CREW_COST
            route_rows.append(dict(service_date=SERVICE_DATE,plan_type="OPTIMIZED",route_id=rid,depot_id=depot_id,vehicle_id=fleet.iloc[v].vehicle_id,stops=seq-1,km=float(cumul),duration_min=end-SHIFT_START,cash_delivered_thb=float(delivered),cash_collected_thb=float(collected),cost_thb=float(cost),start_min=SHIFT_START,end_min=end))
    return stop_rows,route_rows

opt_stops=[]; opt_routes=[]
for depot_id in sorted(orders.depot_id.unique()):
    s,r=optimize(depot_id,orders[orders.depot_id==depot_id],vehicles[vehicles.depot_id==depot_id])
    opt_stops+=s; opt_routes+=r
print(f"OPTIMIZED_ROUTES={len(opt_routes)}, OPTIMIZED_STOPS={len(opt_stops)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fixed-cycle baseline: select daily historical stop volume, assign nearest-neighbor routes

# COMMAND ----------

def baseline(depot_id, candidates, fleet, target):
    """Deterministic nearest-neighbor baseline, bounded by historical daily stops."""
    if candidates.empty or fleet.empty: return [], []
    depot=depots.loc[depot_id]; remaining=candidates.copy()
    remaining["_cycle"] = remaining.node_id.map(lambda x: int(hashlib.md5(str(x).encode()).hexdigest(),16)%5)
    chosen=remaining[remaining._cycle == (pd.Timestamp(SERVICE_DATE).dayofyear%5)].copy()
    if len(chosen)<target: chosen=pd.concat([chosen,remaining[~remaining.node_id.isin(chosen.node_id)].head(target-len(chosen))])
    chosen=chosen.head(max(1,int(target))).reset_index(drop=True)
    rows=[]; routes=[]; vehicle_i=0
    while not chosen.empty and vehicle_i<len(fleet):
        v=fleet.iloc[vehicle_i]; rid=f"BASE-{depot_id}-{v.vehicle_id}"; cur=(depot.lat,depot.lng); seq=1; total=0.; delivered=collected=0.; start=SHIFT_START
        capacity=float(v.cash_capacity_thb); picked=[]
        while not chosen.empty:
            dist=chosen.apply(lambda x:hav(cur[0],cur[1],x.lat,x.lng),axis=1); ix=dist.idxmin(); x=chosen.loc[ix]
            if x.amount_thb>capacity and picked: break
            leg=float(dist.loc[ix]); total+=leg; start+=int(math.ceil(leg/SPEED_KMH*60)); start=max(start,int(x.tw_start_min)); start+=int(x.service_min)
            if start>min(int(x.tw_end_min),SHIFT_END): break
            capacity-=float(x.amount_thb); delivered+=float(x.amount_thb) if x.action=="DELIVER" else 0; collected+=float(x.amount_thb) if x.action=="PICKUP" else 0
            rows.append(dict(service_date=SERVICE_DATE,plan_type="BASELINE",route_id=rid,vehicle_id=v.vehicle_id,depot_id=depot_id,stop_seq=seq,node_id=x.node_id,node_type=x.node_type,node_name=x.node_name,action=x.action,amount_thb=float(x.amount_thb),eta_min=start-int(x.service_min),lat=float(x.lat),lng=float(x.lng),cum_km=float(total)))
            cur=(x.lat,x.lng); chosen=chosen.drop(ix); picked.append(ix); seq+=1
        if picked:
            total+=hav(cur[0],cur[1],depot.lat,depot.lng); end=min(SHIFT_END,start+int(math.ceil(hav(cur[0],cur[1],depot.lat,depot.lng)/SPEED_KMH*60)))
            routes.append(dict(service_date=SERVICE_DATE,plan_type="BASELINE",route_id=rid,depot_id=depot_id,vehicle_id=v.vehicle_id,stops=seq-1,km=total,duration_min=end-SHIFT_START,cash_delivered_thb=delivered,cash_collected_thb=collected,cost_thb=total*float(v.cost_per_km_thb)+CREW_COST,start_min=SHIFT_START,end_min=end))
        vehicle_i+=1
    return rows,routes

hist=spark.table(f"{T}.gold_baseline_daily").where(f"service_date = DATE '{SERVICE_DATE}'").toPandas()
base_stops=[]; base_routes=[]
for depot_id in sorted(orders.depot_id.unique()):
    target=int(hist[hist.depot_id==depot_id].stops.sum()) if not hist[hist.depot_id==depot_id].empty else max(1,len(orders[orders.depot_id==depot_id])//2)
    s,r=baseline(depot_id,orders[orders.depot_id==depot_id],vehicles[vehicles.depot_id==depot_id],target); base_stops+=s;base_routes+=r

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write routes, CDF-enabled stop feed, and baseline-vs-optimized KPIs

# COMMAND ----------

route_pdf=pd.DataFrame(base_routes+opt_routes)
stop_pdf=pd.DataFrame(base_stops+opt_stops)
if route_pdf.empty or stop_pdf.empty: raise RuntimeError("No routes produced; inspect orders and fleet capacity.")
route_pdf.to_dict("records") # fail early on unsupported values
spark.createDataFrame(route_pdf).write.mode("overwrite").saveAsTable(f"{T}.gold_routes")
spark.createDataFrame(stop_pdf).write.mode("overwrite").saveAsTable(f"{T}.gold_route_stops")
spark.sql(f"ALTER TABLE {T}.gold_route_stops SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

forecast=spark.table(f"{T}.gold_demand_forecast").where("forecast_date = DATE '2026-10-01'").select("node_id","pred_p80_thb").toPandas()
risk=status.merge(forecast,on="node_id",how="left"); risk["days"]=(risk.current_cash_thb-risk.min_cash_thb)/risk.pred_p80_thb.clip(lower=1)
summaries=[]
for plan in ["BASELINE","OPTIMIZED"]:
    r=route_pdf[route_pdf.plan_type==plan]; visited=set(stop_pdf[stop_pdf.plan_type==plan].node_id)
    relevant=orders[orders.priority.isin(["CRITICAL","HIGH"])]
    sla=100*relevant.node_id.isin(visited).mean() if len(relevant) else 100.
    idle=float(np.maximum(0,risk.current_cash_thb-3*risk.pred_p80_thb.fillna(0)).sum())
    cashout=int(((risk.days<1)&~risk.node_id.isin(visited)).sum())
    summaries.append(dict(service_date=SERVICE_DATE,plan_type=plan,routes=len(r),vehicles_used=r.vehicle_id.nunique(),stops=int(r.stops.sum()),km=float(r.km.sum()),duration_hr=float(r.duration_min.sum()/60),cost_thb=float(r.cost_thb.sum()),idle_cash_thb=idle,cashout_risk_nodes=cashout,sla_pct=float(sla)))
summary=pd.DataFrame(summaries)
spark.createDataFrame(summary).write.mode("overwrite").saveAsTable(f"{T}.gold_route_summary")
print("ROUTE_SUMMARY")
print(summary.round(2).to_string(index=False))
base,op=summary.iloc[0],summary.iloc[1]
print(f"COST_SAVINGS_PCT={(base.cost_thb-op.cost_thb)/base.cost_thb*100:.1f}%")
