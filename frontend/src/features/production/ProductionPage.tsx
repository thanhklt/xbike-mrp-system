import React from "react";
import { CheckCircle, Clock, HardHat, Plus } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_WORK_ORDERS = [
  {
    id: 1,
    woNumber: "WO-2026-0012",
    bikeModel: "xBike Urban Commuter E-Bike",
    sku: "XB-BIKE-URBAN-01",
    qtyPlanned: 25,
    qtyCompleted: 10,
    qtyScrap: 0,
    status: "IN_PROGRESS",
    progressPct: 40,
    line: "Line A - Main Frame & Mechanicals",
    scheduledEnd: "2026-10-04",
  },
  {
    id: 2,
    woNumber: "WO-2026-0013",
    bikeModel: "xBike Terra Gravel Carbon 11S",
    sku: "XB-BIKE-GRAVEL-PRO",
    qtyPlanned: 15,
    qtyCompleted: 0,
    qtyScrap: 0,
    status: "PLANNED",
    progressPct: 0,
    line: "Line B - Precision Road/Gravel",
    scheduledEnd: "2026-10-08",
  },
  {
    id: 3,
    woNumber: "WO-2026-0010",
    bikeModel: "xBike Urban Commuter E-Bike",
    sku: "XB-BIKE-URBAN-01",
    qtyPlanned: 30,
    qtyCompleted: 30,
    qtyScrap: 1,
    status: "COMPLETED",
    progressPct: 100,
    line: "Line A - Main Frame & Mechanicals",
    scheduledEnd: "2026-09-28",
  },
];

export const ProductionPage: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="Production Work Orders & Assembly"
        subtitle="Manage shop floor assembly batches, workstation line dispatching and real-time completion tracking"
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            New Work Order
          </Button>
        }
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: 24 }}>
        {MOCK_WORK_ORDERS.map((wo) => (
          <Card key={wo.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                  {wo.line}
                </span>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 700 }}>{wo.woNumber}</h3>
              </div>
              <Badge
                color={
                  wo.status === "COMPLETED"
                    ? "emerald"
                    : wo.status === "IN_PROGRESS"
                    ? "cyan"
                    : "amber"
                }
              >
                {wo.status}
              </Badge>
            </div>

            <p style={{ fontWeight: 600, fontSize: "0.95rem", marginBottom: 2 }}>{wo.bikeModel}</p>
            <code style={{ fontSize: "0.8rem", color: "var(--accent-cyan)", display: "block", marginBottom: 16 }}>
              {wo.sku}
            </code>

            {/* Progress bar */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Completion Rate</span>
                <span style={{ fontWeight: 600 }}>{wo.qtyCompleted} / {wo.qtyPlanned} Units ({wo.progressPct}%)</span>
              </div>
              <div style={{ width: "100%", height: 8, background: "var(--bg-surface)", borderRadius: 4, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${wo.progressPct}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, var(--accent-cyan), var(--accent-emerald))",
                    borderRadius: 4,
                  }}
                />
              </div>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "0.82rem",
                color: "var(--text-secondary)",
                borderTop: "1px solid var(--bg-card-border)",
                paddingTop: 12,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <Clock size={14} color="var(--text-muted)" /> Due: {wo.scheduledEnd}
              </div>
              <div>
                Scrapped: <strong style={{ color: wo.qtyScrap > 0 ? "var(--accent-rose)" : "var(--text-secondary)" }}>{wo.qtyScrap}</strong>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
