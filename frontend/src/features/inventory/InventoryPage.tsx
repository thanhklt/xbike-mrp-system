import React, { useState } from "react";
import { ArrowDownRight, ArrowUpRight, Search } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_STOCK = [
  {
    id: 1,
    part_number: "XB-SUB-WHEEL-F",
    name: "Front Wheel Assembly 700c",
    warehouse: "WH-MAIN",
    bin: "B-04-12",
    on_hand: 45,
    allocated: 10,
    reserved: 5,
    available: 30,
    status: "HEALTHY",
  },
  {
    id: 2,
    part_number: "XB-RAW-RIM-700C",
    name: "Double-wall Alloy Rim 700c",
    warehouse: "WH-MAIN",
    bin: "A-01-05",
    on_hand: 120,
    allocated: 40,
    reserved: 0,
    available: 80,
    status: "HEALTHY",
  },
  {
    id: 3,
    part_number: "XB-RAW-CHN-11S",
    name: "11-Speed Bicycle Chain",
    warehouse: "WH-MAIN",
    bin: "C-02-18",
    on_hand: 88,
    allocated: 15,
    reserved: 0,
    available: 73,
    status: "HEALTHY",
  },
  {
    id: 4,
    part_number: "XB-RAW-BATTERY-500",
    name: "Lithium Ion Battery Pack 36V 14Ah",
    warehouse: "WH-HAZMAT",
    bin: "H-01-02",
    on_hand: 8,
    allocated: 6,
    reserved: 0,
    available: 2,
    status: "LOW_STOCK",
  },
];

export const InventoryPage: React.FC = () => {
  const [search, setSearch] = useState("");

  const filtered = MOCK_STOCK.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.part_number.toLowerCase().includes(search.toLowerCase()) ||
      s.bin.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div>
      <PageHeader
        title="Warehouse Inventory & Stock Control"
        subtitle="Real-time physical inventory, warehouse bin allocations and net available stock"
        action={
          <div style={{ display: "flex", gap: 10 }}>
            <Button variant="secondary" icon={<ArrowDownRight size={16} />}>
              Transfer Bin
            </Button>
            <Button variant="primary" icon={<ArrowUpRight size={16} />}>
              Manual Adjustment
            </Button>
          </div>
        }
      />

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
          <div className="search-box">
            <Search size={16} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Filter by part, name, or bin location..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Part Number</th>
                <th>Description</th>
                <th>Warehouse</th>
                <th>Bin</th>
                <th>On Hand</th>
                <th>Allocated (W.O.)</th>
                <th>Reserved</th>
                <th>Net Available</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td>
                    <code style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>
                      {item.part_number}
                    </code>
                  </td>
                  <td style={{ fontWeight: 500 }}>{item.name}</td>
                  <td>{item.warehouse}</td>
                  <td>
                    <Badge color="purple">{item.bin}</Badge>
                  </td>
                  <td style={{ fontWeight: 600 }}>{item.on_hand}</td>
                  <td style={{ color: "var(--accent-amber)" }}>{item.allocated}</td>
                  <td>{item.reserved}</td>
                  <td>
                    <span
                      style={{
                        fontWeight: 700,
                        color: item.available < 10 ? "var(--accent-rose)" : "var(--accent-emerald)",
                      }}
                    >
                      {item.available}
                    </span>
                  </td>
                  <td>
                    <Badge color={item.status === "HEALTHY" ? "emerald" : "rose"}>
                      {item.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
