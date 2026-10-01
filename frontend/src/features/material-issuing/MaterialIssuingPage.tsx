import React from "react";
import { CheckSquare, ClipboardList, Plus } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_ISSUES = [
  {
    id: 1,
    request_number: "MIR-2026-0034",
    work_order: "WO-2026-0012",
    product: "xBike Urban Commuter E-Bike",
    itemsCount: 6,
    status: "ISSUED",
    requestedBy: "Shop Floor Lead",
    sourceBin: "B-04-12, C-02-18",
    issuedAt: "2026-10-01 08:30",
  },
  {
    id: 2,
    request_number: "MIR-2026-0035",
    work_order: "WO-2026-0013",
    product: "xBike Terra Gravel Carbon",
    itemsCount: 8,
    status: "PICKING",
    requestedBy: "Assembly Station 2",
    sourceBin: "A-01-05, H-01-02",
    issuedAt: "In Progress",
  },
];

export const MaterialIssuingPage: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="Material Issuing & Picking Lists"
        subtitle="Warehouse kitting, component reservations, picking lists and hand-off to shop floor assembly lines"
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            Create Issue Request
          </Button>
        }
      />

      <Card>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Issue Request #</th>
                <th>Target Work Order</th>
                <th>Assembled Product</th>
                <th>BOM Items Count</th>
                <th>Source Bins</th>
                <th>Requested By</th>
                <th>Issue Status</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_ISSUES.map((issue) => (
                <tr key={issue.id}>
                  <td>
                    <code style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>
                      {issue.request_number}
                    </code>
                  </td>
                  <td>
                    <Badge color="cyan">{issue.work_order}</Badge>
                  </td>
                  <td style={{ fontWeight: 500 }}>{issue.product}</td>
                  <td>{issue.itemsCount} Parts</td>
                  <td>
                    <Badge color="purple">{issue.sourceBin}</Badge>
                  </td>
                  <td>{issue.requestedBy}</td>
                  <td>
                    <Badge color={issue.status === "ISSUED" ? "emerald" : "amber"}>
                      {issue.status}
                    </Badge>
                  </td>
                  <td style={{ color: "var(--text-muted)" }}>{issue.issuedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
