import React from "react";
import { CheckCircle2, FileCheck2, Plus } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_RECEIVING = [
  {
    id: 1,
    grn_number: "GRN-2026-0089",
    po_number: "PO-2026-004",
    supplier: "Shimano Global Bike Components",
    part: "11-Speed Bicycle Chain (XB-RAW-CHN-11S)",
    qtyShipped: 50,
    qtyAccepted: 50,
    lot: "LOT-SHM-2026-Q1",
    status: "ACCEPTED",
    date: "2026-10-01",
  },
  {
    id: 2,
    grn_number: "GRN-2026-0090",
    po_number: "PO-2026-009",
    supplier: "Apex Precision Alloy Frames",
    part: "Hydroformed 6061 Frame (XB-RAW-FRM-ALU)",
    qtyShipped: 25,
    qtyAccepted: 0,
    lot: "LOT-APX-091",
    status: "PENDING_INSPECTION",
    date: "2026-10-01",
  },
];

export const ReceivingPage: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="Receiving & Quality Inspection"
        subtitle="Inbound Goods Receipt Notes (GRN), PO verification, tolerance testing and lot traceability"
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            New Goods Receipt (GRN)
          </Button>
        }
      />

      <Card>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>GRN Number</th>
                <th>PO Reference</th>
                <th>Supplier</th>
                <th>Material / Part</th>
                <th>Qty Shipped</th>
                <th>Qty Accepted</th>
                <th>Traceability Lot #</th>
                <th>Inspection Status</th>
                <th>Received Date</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_RECEIVING.map((r) => (
                <tr key={r.id}>
                  <td>
                    <code style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>{r.grn_number}</code>
                  </td>
                  <td>
                    <Badge color="purple">{r.po_number}</Badge>
                  </td>
                  <td style={{ fontWeight: 500 }}>{r.supplier}</td>
                  <td>{r.part}</td>
                  <td>{r.qtyShipped}</td>
                  <td style={{ color: "var(--accent-emerald)", fontWeight: 600 }}>{r.qtyAccepted}</td>
                  <td>
                    <code style={{ fontSize: "0.78rem" }}>{r.lot}</code>
                  </td>
                  <td>
                    <Badge color={r.status === "ACCEPTED" ? "emerald" : "amber"}>
                      {r.status}
                    </Badge>
                  </td>
                  <td style={{ color: "var(--text-muted)" }}>{r.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
