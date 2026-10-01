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
| **`catalog`** | Bicycle models, sub-assemblies, raw parts, and unit of measures. | `Part`, `Assembly`, `Category`, `UnitOfMeasure` |
| **`suppliers`** | Approved vendor list (AVL), vendor lead times, pricing tiers. | `Supplier`, `SupplierPartPricing` |
| **`bom`** | Multi-level Bill of Materials trees with scrap factor and revisions. | `BOMHeader`, `BOMItem`, `BOMRevision` |
| **`inventory`** | Real-time stock levels across bins, lots, and movement ledger. | `StockLevel`, `Warehouse`, `BinLocation`, `StockMovement` |
| **`receiving`** | Inbound logistics, goods receipt notes (GRN), lot tracking. | `GoodsReceiptNote`, `ReceiptItem` |
| **`material_issuing`** | Staging and issuance of required components for active work orders. | `MaterialIssueRequest`, `PickList`, `IssueItem` |
| **`production`** | Production scheduling, routing, work stations, assembly steps. | `WorkOrder`, `ProductionRun`, `WorkStation` |
| **`finished_goods_issuing`** | Shipping / transferring completed bicycles to distribution. | `DispatchOrder`, `DispatchItem` |
| **`reporting`** | MRP calculation engines, inventory valuation, scrap & lead-time analytics. | `MRPRunRecord`, `MaterialShortageReport` |
| **`audit`** | Tamper-proof event logs for compliance and traceability. | `AuditTrailLog` |

---

## 3. Database & Transactional Integrity

- **ACID Guarantee**: Inventory adjustments and material issuance are wrapped in strict database transactions with row-level locks (`SELECT FOR UPDATE`) to prevent negative inventory allocations.
- **Double-Entry Stock Ledger**: Physical stock changes are recorded as ledger movements (Credit from Location A, Debit to Location B) rather than arbitrary in-place mutations.
- **Audit Trails**: All status transitions (`DRAFT` -> `PLANNED` -> `RELEASED` -> `IN_PROGRESS` -> `COMPLETED`) generate immutable audit records.
