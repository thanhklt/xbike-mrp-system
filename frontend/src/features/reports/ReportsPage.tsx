import React, { useState } from "react";
import { AlertTriangle, ArrowUpRight, CheckCircle2, Clock, PlayCircle, RefreshCw } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

export const ReportsPage: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [mrpResult, setMrpResult] = useState<any | null>(null);

  const handleRunMRP = () => {
    setIsRunning(true);
    setTimeout(() => {
      setIsRunning(false);
      setMrpResult({
        planId: "MRP-2026-X88",
        timestamp: "Just now",
        totalAnalyzed: 142,
        shortages: [
          {
            partNo: "XB-RAW-RIM-700C",
            name: "Double-wall Alloy Rim 700c",
            gross: 150,
            onHand: 120,
            allocated: 40,
            netShortage: 70,
            action: "Issue PO: 100 PCS to Apex Precision Alloy",
            leadTime: "10 Days",
            urgency: "HIGH",
          },
          {
            partNo: "XB-RAW-CHN-11S",
            name: "11-Speed Bicycle Chain",
            gross: 100,
            onHand: 88,
            allocated: 15,
            netShortage: 27,
            action: "Issue PO: 50 PCS to Shimano",
            leadTime: "7 Days",
            urgency: "MEDIUM",
          },
        ],
      });
    }, 1200);
  };

  return (
    <div>
      <PageHeader
        title="MRP Engine & Manufacturing Analytics"
        subtitle="Gross-to-net component explosion, lead time offset & procurement planning"
        action={
          <Button
            variant="primary"
            icon={isRunning ? <RefreshCw className="animate-spin" size={16} /> : <PlayCircle size={16} />}
            onClick={handleRunMRP}
            disabled={isRunning}
          >
            {isRunning ? "Running MRP Calculation..." : "Execute MRP Run"}
          </Button>
        }
      />

      {/* KPI Cards */}
      <div className="metrics-grid">
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Active Work Orders</span>
            <Badge color="cyan">Shop Floor</Badge>
          </div>
          <div className="metric-value">8</div>
          <div className="metric-trend trend-up">
            <ArrowUpRight size={14} /> 2 scheduled today
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Critical Shortages</span>
            <Badge color="rose">Attention</Badge>
          </div>
          <div className="metric-value" style={{ color: "var(--accent-rose)" }}>2</div>
          <div className="metric-trend trend-alert">
            <AlertTriangle size={14} /> Immediate PO required
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">BOM Components</span>
            <Badge color="purple">Catalog</Badge>
          </div>
          <div className="metric-value">142</div>
          <div className="metric-trend" style={{ color: "var(--text-muted)" }}>
            Across 12 bike assemblies
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-label">Warehouse Utilization</span>
            <Badge color="emerald">Optimal</Badge>
          </div>
          <div className="metric-value">73.5%</div>
          <div className="metric-trend trend-up">
            <CheckCircle2 size={14} /> Storage capacity healthy
          </div>
        </div>
      </div>

      {/* MRP Results Table */}
      <Card
        title="Material Requirements Plan (Net Shortages & Planned Orders)"
        action={
          mrpResult && (
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Run ID: <strong style={{ color: "var(--accent-cyan)" }}>{mrpResult.planId}</strong> ({mrpResult.timestamp})
            </span>
          )
        }
      >
        {mrpResult ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Part Number</th>
                  <th>Component Name</th>
                  <th>Gross Need</th>
                  <th>Stock On-Hand</th>
                  <th>Allocated</th>
                  <th>Net Shortage</th>
                  <th>Recommended Action</th>
                  <th>Vendor Lead Time</th>
                  <th>Priority</th>
                </tr>
              </thead>
              <tbody>
                {mrpResult.shortages.map((item: any) => (
                  <tr key={item.partNo}>
                    <td>
                      <code style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>{item.partNo}</code>
                    </td>
                    <td style={{ fontWeight: 500 }}>{item.name}</td>
                    <td>{item.gross} PCS</td>
                    <td>{item.onHand} PCS</td>
                    <td>{item.allocated} PCS</td>
                    <td style={{ color: "var(--accent-rose)", fontWeight: 700 }}>
                      -{item.netShortage} PCS
                    </td>
                    <td>
                      <span style={{ color: "var(--accent-emerald)", fontWeight: 500 }}>
                        {item.action}
                      </span>
                    </td>
                    <td>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                        <Clock size={14} color="var(--text-muted)" /> {item.leadTime}
                      </span>
                    </td>
                    <td>
                      <Badge color={item.urgency === "HIGH" ? "rose" : "amber"}>
                        {item.urgency}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
            <p>Click "Execute MRP Run" to explode active BOM demand and compute procurement recommendations.</p>
          </div>
        )}
      </Card>
    </div>
  );
};
