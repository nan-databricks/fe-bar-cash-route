# SNB Cash Logistics ML

1. `01_train_register.py` trains global point and P80 LightGBM models from the frozen demand-feature contract.
2. Validation is a time split: train before 2026-08-01 and validate through 2026-09-30.
3. It reports WAPE and MAPE against a lag-7/rolling-28 naive baseline, overall and by node type.
4. The dual-output pyfunc is logged to MLflow and registered as `cash_demand_forecast` with alias `champion`.
5. `02_deploy_endpoint.py` reconciles the `snb-cash-forecast` serverless endpoint to champion.
6. `03_score_orders.py` recursively scores 1–7 October and creates cash delivery/pickup orders.
7. Orders use P80 demand for a conservative five-day cover target and explicit service windows.
8. `04_optimize_routes.py` runs per-depot CVRP-TW with OR-Tools and a high critical-stop drop penalty.
9. The output includes a fixed-cycle nearest-neighbor baseline for an operationally meaningful comparison.
10. Costs are distance cost plus THB 2,500 per van-day; road distance is haversine × 1.3.
11. A global model is intentionally simpler and more robust than hundreds of sparse per-node models.
12. OR-Tools is an explainable open-source heuristic; a commercial solver could improve very large or dynamic dispatches.
