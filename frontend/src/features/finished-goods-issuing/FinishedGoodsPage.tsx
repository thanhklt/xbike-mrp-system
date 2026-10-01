import React from "react";
import { Plus, Send, Truck } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_DISPATCHES = [
  {
    id: 1,
    dispatch_number: "DSP-2026-0005",
    dealer: "EuroBike Hub Berlin Distribution",
    carrier_tracking: "DHL-EX-992819",
    product: "xBike Urban Commuter E-Bike",
    qty: 10,
    serial_range: "XB26-00101 to XB26-00110",
    status: "DISPATCHED",
    date: "2026-10-01",
  },
  {
    id: 2,
    dispatch_number: "DSP-2026-0006",
    dealer: "Pacific Cycle Dealers Sydney",
    carrier_tracking: "MAERSK-LOG-8120",
    product: "xBike Terra Gravel Carbon 11S",
    qty: 15,
    serial_range: "XB26-00201 to XB26-00215",
    status: "PREPARING",
    date: "2026-10-02",
  },
];

export const FinishedGoodsPage: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="Finished Goods Dispatch & Issuing"
        subtitle="Final packaging inspection, serial number assignments and shipment dispatch to dealerships"
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            Create Dispatch Order
          </Button>
        }
      />

      <Card>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Dispatch #</th>
                <th>Destination Partner</th>
                <th>Bicycle Model</th>
                <th>Qty</th>
                <th>Serial Number Range</th>
                <th>Carrier Tracking #</th>
                <th>Status</th>
                <th>Dispatch Date</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_DISPATCHES.map((d) => (
                <tr key={d.id}>
                  <td>
                    <code style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>
                      {d.dispatch_number}
                    </code>
                  </td>
                  <td style={{ fontWeight: 500 }}>{d.dealer}</td>
                  <td>{d.product}</td>
                  <td>
                    <strong>{d.qty} Units</strong>
                  </td>
                  <td>
                    <code style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                      {d.serial_range}
                    </code>
                  </td>
                  <td>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                      <Truck size={14} color="var(--text-muted)" /> {d.carrier_tracking}
                    </span>
                  </td>
                  <td>
                    <Badge color={d.status === "DISPATCHED" ? "emerald" : "amber"}>
                      {d.status}
                    </Badge>
                  </td>
                  <td style={{ color: "var(--text-muted)" }}>{d.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
