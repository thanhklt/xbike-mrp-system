# xBike MRP System Architecture

## 1. Executive Summary & Philosophy

The **xBike MRP System** is designed as a **Modular Monolith** optimized for bicycle assembly and manufacturing. The modular architecture provides high cohesion within manufacturing domains while keeping cognitive load and deployment friction low. If scale requires it, modules can be isolated into microservices along their clear domain boundaries.

```
       [ Client Applications (React SPA / Mobile) ]
                            │
                      [ Nginx Proxy ]
                            │
               [ FastAPI Modular Monolith ]
   ┌────────────────────────┼────────────────────────┐
   ▼                        ▼                        ▼
[Core & Cross-Cutting]  [Domain Modules]        [Shared Utilities]
- Config                - Catalog & Suppliers   - Enums & Units
- Security & JWT        - Multi-level BOM       - Pagination
- Logging & Tracing     - Inventory & Warehouse - DTO base models
- Exception handling    - Work Orders & Assembly
                        - Material Issuance
                        - Receiving & Audit
                            │
              [ PostgreSQL 16 (Relational DB) ]
```

---

## 2. Core Manufacturing & MRP Lifecycle

In bicycle manufacturing, a finished product (e.g., *xBike Urban E-Commuter*) is composed of complex sub-assemblies (e.g., *Front Wheel Assembly*, *Drivetrain System*, *Frame & Fork Kit*) which in turn comprise raw components (spokes, rims, hubs, bearings, bolts).

The manufacturing lifecycle executes in distinct, auditable phases:

```
[1. Demand & Sales Plan]
         │
         ▼
[2. BOM Explosion & MRP Run] ──▶ Identifies Gross vs. Net Component Requirements
         │
         ├───▶ [3a. Purchase Orders (PO)] ──▶ [Receiving & Inspection] ──▶ [Stock on Hand]
         │
         └───▶ [3b. Work Orders (WO)] ────▶ [Material Issuing / Pick] ──▶ [Shop Floor Assembly]
                                                                                │
                                                                                ▼
[5. Sales & Logistics] ◀── [Finished Goods Issuing] ◀── [Inspection & QA Pass]
```

### Domain Module Breakdown

| Module | Responsibility | Key Entities |
| :--- | :--- | :--- |
| **`auth`** | JWT issuance/validation and orchestration through the employee public service. Contains router.py, schema.py and service.py. | `AuthService` |
| **`nhan_vien`** | Owns employee credentials, profiles and roles; public authentication and atomic password-change operations. | `NhanVien`, `VaiTro`, `NhanVienService` |
| **`catalog`** | Bicycle models, sub-assemblies, raw parts, and unit of measures. | `Part`, `Assembly`, `Category`, `UnitOfMeasure` |
| **`suppliers`** | Approved vendor list (AVL), vendor lead times, pricing tiers. | `Supplier`, `SupplierPartPricing` |
| **`bom`** | Multi-level Bill of Materials trees with scrap factor and revisions. | `BOMHeader`, `BOMItem`, `BOMRevision` |
| **`inventory`** | Real-time stock levels across bins, lots, and movement ledger. | `StockLevel`, `Warehouse`, `BinLocation`, `StockMovement` |
| **`receiving`** | Inbound logistics, goods receipt notes (GRN), lot tracking. | `GoodsReceiptNote`, `ReceiptItem` |
| **`material_issuing`** | Staging and issuance of required components for active work orders. | `MaterialIssueRequest`, `PickList`, `IssueItem` |
| **`production`** | Production scheduling, routing, work stations, assembly steps. | `WorkOrder`, `ProductionRun`, `WorkStation` |
| **`finished_goods_issuing`** | Shipping / transferring completed bicycles to distribution. | `DispatchOrder`, `DispatchItem` |
| **`reporting`** | MRP calculation engines, inventory valuation, scrap & lead-time analytics. | `MRPRunRecord`, `MaterialShortageReport` |
| **`audit`** | Append/read history through its public service; SQL trigger rejects changes to persisted history. | `LichSuThaoTac`, `AuditService` |

---

## 3. Database & Transactional Integrity

### Auth, employee and audit boundary (30/10/2026)

`AuthService` imports the employee module's public service and exported DTOs. It never imports employee ORM/repositories. `NhanVienService` verifies credentials and current account/role/password version, returns a safe `AuthIdentity`, and owns the password-change transaction. The ORM objects and hashes remain inside the employee module.

Password changes call `AuditService.append` with the same request session; the audit service never commits independently. `SELECT FOR UPDATE` refreshes credentials under lock before verification, and password UPDATE plus audit INSERT commit together. Existing JWTs fail the keyed password-version check after a password change.

Only the three tables `"NhanVien"`, `"VaiTro"`, `"LichSuThaoTac"` have been renamed to PascalCase. Other models only receive FK target updates where necessary; their remaining SQL v4 drift is outside this task. Demo Docker uses bootstrap on a fresh data directory, without migrations. The manufacturing overview below describes broader architecture, not proof that every workflow/schema has been implemented or verified.

- **ACID Guarantee**: Inventory adjustments and material issuance are wrapped in strict database transactions with row-level locks (`SELECT FOR UPDATE`) to prevent negative inventory allocations.
- **Double-Entry Stock Ledger**: Physical stock changes are recorded as ledger movements (Credit from Location A, Debit to Location B) rather than arbitrary in-place mutations.
- **Audit Trails**: All status transitions (`DRAFT` -> `PLANNED` -> `RELEASED` -> `IN_PROGRESS` -> `COMPLETED`) generate immutable audit records.


### Employee administration (01/11/2026)

The employee module contains models.py, router.py, schemas.py, ports.py, repository.py and service.py, plus __init__.py. DTOs needed internally live in schemas.py; NhanVienService owns reads and mutations through NhanVienRepository. The former dto.py, write_service.py and module errors.py have been consolidated. Auth still calls only the public employee service; audit writes go through AuditService in the same transaction.

The eight employee/role endpoints are documented in [sequence diagrams](sequence/nhan_vien.md). DELETE reversibly blocks an account with a required JSON reason and replaces POST /vo_hieu_hoa. POST /mo_khoa restores activity. Documents, roles and history are retained; list queries still support blocked accounts and status filtering.

One administrator is provisioned by bootstrap. APIs reject creation/promotion of another admin, demotion of the existing admin and blocking that admin. Mutations lock and refresh the administrator row before locking the target and comparing If-Match. The API rechecks account/role/password version after waiting. No singleton-admin database constraint is added; direct SQL is outside this API policy.

Employee changes and audit commit/rollback together. Role changes append thu_hoi_quyen and cap_quyen; DELETE appends vo_hieu_hoa; unlock appends sua with reason and before/after data. Account/role errors use the contract-v2 error/meta envelope, matching auth. Other modules retain their existing error envelopes.
