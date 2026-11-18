# Employee browser E2E with a real backend

This suite performs writes. Run only against a disposable PostgreSQL database, never the application/demo database. It deliberately uses a separate config and is excluded from the default fixture browser suite.

Required setup before each run:

1. Create a new empty database in a dedicated test PostgreSQL server, bootstrap `infra/postgres/init.sql` and then `seed.sql` exactly once. Do not reset an existing application database or reuse a partially executed test database.
2. Run current backend source on localhost **8002**, with its runtime YAML `database_url` pointing to that test database. Normal settings do not support environment overrides, so mount a separate config file; do not edit the tracked application config. Validate the target database/container before enabling writes.
3. Ensure localhost **5176** is free. The config starts Vite there and proxies API requests to 8002. Existing application ports 8000/5175 are not used.
4. From frontend in PowerShell: `$env:EMPLOYEE_E2E='1'; npx.cmd playwright test --config playwright.employee-e2e.config.js`.

The scenario uses demo identities `nhan_vien_sx`, `nhan_vien_lr`, `quan_ly_kho` and seed password `DemoXbike2026!`. It changes request 5 and must start from fresh seed. There are no route mocks or injected tokens: three separate browser contexts log in through the UI. The scenario covers preview, draft, reopening after refresh, sending, assignee isolation, manager approval, starting production, completion and finished goods export.

After the run, inspect the test DB read-only: request 5 completed, two approved issue types, completion quantity 7 approved, item 1 stock/held/available all 0; all inventory stock must equal ledger sums and held totals equal active holds. Preserve failure artifacts before another run. Stop test backend before PostgreSQL; only dispose resources positively identified as this run's test resources. No cleanup is applied to the application DB by this suite.

The 17/11 run used PostgreSQL test container `xbike-nv-e2e-20261117` on localhost:55465 and backend `xbike-nv-e2e-api-20261117` on 8002. Its database name and runtime config are recorded in the delivery report; this describes that run, not a dependency on those containers for future environments.
