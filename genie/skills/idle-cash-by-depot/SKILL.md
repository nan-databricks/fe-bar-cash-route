---
name: idle-cash-by-depot
description: Roll current cassette and vault cash to each SNB cash centre (depot). Use for "idle cash by depot", "how much cash is sitting", "vault utilisation".
---

# Idle cash by depot

`as_of_date` on `gold_node_status` is **2026-09-30**. Idle cash = `SUM(current_cash_thb)` at nodes, not CIT vans.

## Steps

```sql
SELECT depot_id, COUNT(*) AS nodes, SUM(current_cash_thb) AS idle_cash_thb
FROM {catalog}.{schema}.gold_node_status
WHERE as_of_date = DATE '2026-09-30'
GROUP BY depot_id
ORDER BY depot_id
```

## Answer shape

Idle cash as of **2026-09-30**:

| depot_id | nodes | idle_cash_thb |
|---|---|---|

State the total across depots. Depots are DEP-KKN-C (central), DEP-KKN-N (north), DEP-KKN-S (south).
