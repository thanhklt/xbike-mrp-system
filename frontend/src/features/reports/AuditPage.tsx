import React from "react";
import { ShieldCheck } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_AUDIT = [
  {
    id: 1,
    user: "admin@xbike.local",
    action: "CREATE_WORK_ORDER",
    resource: "WO-2026-0012",
    details: "Authorized batch production of 25 Urban Commuter bikes",
    ip: "192.168.1.50",
    timestamp: "2026-10-01 08:00:12",
  },
  {
    id: 2,
    user: "warehouse@xbike.local",
    action: "POST_GOODS_RECEIPT",
    resource: "GRN-2026-0089",
    details: "Received 50 units of 11-speed bicycle chains from Shimano",
    ip: "192.168.1.62",
    timestamp: "2026-10-01 09:15:44",
  },
  {
    id: 3,
    user: "admin@xbike.local",
    action: "RUN_MRP_EXPLOSION",
    resource: "MRP-2026-X88",
    details: "Ran net material requirements calculation across 142 parts",
    ip: "192.168.1.50",
    timestamp: "2026-10-01 10:20:00",
  },
];

export const AuditPage: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="Compliance & Audit Trail"
        subtitle="Immutable event logs capturing all transactional state transitions, approvals and inventory adjustments"
      />

      <Card>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Operator</th>
                <th>Action</th>
                <th>Resource Reference</th>
                <th>Change Description</th>
                <th>IP Address</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_AUDIT.map((log) => (
                <tr key={log.id}>
                  <td style={{ color: "var(--text-muted)", whiteSpace: "nowrap" }}>{log.timestamp}</td>
                  <td style={{ fontWeight: 600 }}>{log.user}</td>
                  <td>
                    <Badge color="cyan">{log.action}</Badge>
                  </td>
                  <td>
                    <code>{log.resource}</code>
                  </td>
                  <td>{log.details}</td>
                  <td style={{ color: "var(--text-muted)" }}>{log.ip}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
