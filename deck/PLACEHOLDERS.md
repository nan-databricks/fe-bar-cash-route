# Placeholders to fill

The integrator replaces each `{{...}}` token across `deck/deck.md`, `README.md`, `docs/submission_form_answers.md`, `docs/demo_script.md`, `docs/roleplay_prep.md` and `docs/talk_track.md` with the **real values from the end-to-end run**, then rebuilds the PDF with `bash deck/build_pdf.sh`.

Do not invent values. Every number must trace to a committed evidence file. Plan date: `service_date = 2026-10-01`. Write tokens **without units** where the surrounding text already has them: the deck writes `THB {{...}}`, `{{...}}%` and `−{{...}}%` itself.

| Placeholder | Meaning | Source (table / column) | Format example |
|---|---|---|---|
| `{{KPI_COST_PER_DAY_BASELINE}}` | Baseline CIT cost for the plan day (THB) | `gold_route_summary` BASELINE `cost_thb` | `186,000` |
| `{{KPI_COST_PER_DAY_OPT}}` | Optimized CIT cost for the plan day (THB) | `gold_route_summary` OPTIMIZED `cost_thb` | `128,000` |
| `{{KPI_COST_SAVING_PCT}}` | Cost reduction % | `1 − OPT/BASELINE` on `cost_thb` | `31` |
| `{{KPI_KM_SAVING_PCT}}` | Route km reduction % | `1 − OPT/BASELINE` on `km` | `27` |
| `{{KPI_VANS_BASELINE}}` | Vans used, baseline | `gold_route_summary` BASELINE `vehicles_used` | `26` |
| `{{KPI_VANS_OPT}}` | Vans used, optimized | `gold_route_summary` OPTIMIZED `vehicles_used` | `18` |
| `{{KPI_IDLE_CASH_REDUCTION_THB}}` | Idle cash released (THB) | BASELINE `idle_cash_thb` − OPTIMIZED `idle_cash_thb` | `42M` |
| `{{KPI_CASHOUT_RISK_BASELINE}}` | Nodes at cash-out risk, baseline | `gold_route_summary` BASELINE `cashout_risk_nodes` | `19` |
| `{{KPI_CASHOUT_RISK_OPT}}` | Nodes at cash-out risk, optimized | `gold_route_summary` OPTIMIZED `cashout_risk_nodes` | `2` |
| `{{KPI_SLA_OPT}}` | % of stops inside time windows, optimized | `gold_route_summary` OPTIMIZED `sla_pct` | `98` |
| `{{KPI_WAPE_MODEL}}` | Holdout WAPE, LightGBM, overall segment | `gold_model_metrics` `WAPE_model`, segment overall | `18%` |
| `{{KPI_WAPE_NAIVE}}` | Holdout WAPE, naive lag-7/roll-28, overall | `gold_model_metrics` `WAPE_naive`, segment overall | `31%` |
| `{{KPI_ANNUAL_SAVING_THB}}` | Annualised CIT saving (THB) | `(BASELINE − OPT cost_thb) × 365`; state the day count if different | `21.2M` |
| `{{GITHUB_URL}}` | Public repo URL | integrator after push | `https://github.com/<user>/fe-bar-cash-route` |
| `{{DEMO_VIDEO_URL}}` | Optional demo recording link (form only) | Nan | `https://…` |

Format examples show the **shape** only; they are not results.

Quick fill (from the repo root, after setting the shell variables):

```bash
grep -rl '{{KPI_' deck docs README.md | xargs sed -i '' \
  -e "s/{{KPI_COST_SAVING_PCT}}/$COST_PCT/g" \
  -e "s/{{KPI_COST_PER_DAY_BASELINE}}/$COST_BASE/g"   # …one -e per token
grep -rn '{{' deck docs README.md   # must return nothing except this file
bash deck/build_pdf.sh
```
