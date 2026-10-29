# SNB Cash Logistics — ML

Four serverless notebooks, run in order by the `snb_cash_ops_e2e` job:

1. `01_train_register.py` trains one global LightGBM (L1 point forecast) plus a quantile model (alpha 0.8) on `gold_demand_features`, with `node_type` as a categorical feature. It trains before 2026-08-01 and validates on 2026-08-01..09-30. Both models are wrapped in one MLflow pyfunc (returns `pred_net_outflow_thb`, `pred_p80_thb`), registered as `cash_demand_forecast` with the alias `champion`. Metrics go to `gold_model_metrics`.
2. `02_deploy_endpoint.py` idempotently points the `snb-cash-forecast` endpoint (Small, scale-to-zero) at the champion version, waits for READY, and runs a smoke-test query. The app request shape is in `endpoint_query_example.json`.
3. `03_score_orders.py` makes a recursive 7-day forecast (1–7 Oct) for all 679 nodes, then builds DELIVER/PICKUP orders for 2026-10-01. Days to cash-out are computed from the P80 forecast. Deliveries cover 5 days of P80 demand, and pickups collect cash above 85% of capacity.
4. `04_optimize_routes.py` solves a per-depot CVRP-TW with OR-Tools: capacity in THB, branch/machine time windows, a 07:00–18:00 shift, haversine distance ×1.3 at 40 km/h, km cost plus THB 2,500 per van, guided local search for 25 s per depot, and high drop penalties for CRITICAL stops. It also writes a fixed 5-day-cycle nearest-neighbor BASELINE in the same tables.

Results (validation): the model's WAPE is 0.248 vs 0.387 for the naive forecast (ATM 0.13 vs 0.25, RCM 0.27 vs 0.41, branch 0.44 vs 0.62). P80 coverage is 0.81.
Routes on 2026-10-01: cost falls 7.8% (THB 75.4k → 69.6k), km fall 22.7%, and crew-hours fall 33%. Cash-out-risk nodes go from 64 to 0, and CRITICAL SLA rises from 14.7% to 100%.

Trade-offs:
- A global model is robust for sparse, noisy node series and needs only one model to serve. Per-node models could capture site quirks but multiply training and serving cost.
- Branch demand is the noisiest segment, because vault flows are lumpy.
- OR-Tools is free, transparent, and solves about 50 stops in seconds. A commercial solver (Gurobi/Hexaly) would matter for multi-day inventory-routing or real-time re-plans at a much larger scale.
- The optimized plan uses more vans (13 vs 11) to reach every urgent node inside its window, but still costs less because it drives far fewer km.
- Idle cash only drops by 2.8%, because branch vault balances dominate it. Lowering branch vault targets is the next lever.
