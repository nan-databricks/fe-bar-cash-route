# SNB Unity Catalog controls

`01_apply_governance.py` is idempotent and runs after the Lakeflow pipeline.
It creates `snb_mask_custodian`, which returns PII only to `snb_pii_readers`,
workspace admins, or the demo owner; all other users receive `***`.
It creates `snb_depot_filter` for central-depot operations users.
Pipeline tables receive layer and cash-logistics domain tags.
Vehicle custodian columns are tagged PII/confidential and receive the UC mask.
The script attempts to attach the depot row filter directly to `silver_cit_trips`.
If a pipeline-managed table rejects that alteration, it creates
`silver_cit_trips_governed`, an equivalent governed view, and prints the fallback.
All gold tables receive SELECT grants for `account users`; bronze and silver remain restricted.
The raw volume grants READ VOLUME to the demo owner.
The script prints tags, function definitions, and a masked vehicle sample as evidence.
All records are synthetic and belong to the fictional Siam Northeast Bank demo.
