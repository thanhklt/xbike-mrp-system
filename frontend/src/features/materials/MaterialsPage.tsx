import React, { useState } from "react";
import { Plus, Search } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_MATERIALS = [
  {
    id: 1,
    part_number: "XB-RAW-RIM-700C",
    name: "Double-wall Alloy Rim 700c 36H",
    category: "WHEEL",
    type: "RAW_MATERIAL",
    unit: "PCS",
    safety_stock: 50,
    cost: "$18.50",
    lead_time: "10 days",
  },
  {
    id: 2,
    part_number: "XB-RAW-CHN-11S",
    name: "11-Speed Bicycle Chain with Quick Link",
    category: "DRIVETRAIN",
    type: "RAW_MATERIAL",
    unit: "PCS",
    safety_stock: 40,
    cost: "$14.00",
    lead_time: "7 days",
  },
  {
    id: 3,
    part_number: "XB-RAW-SPOKE-280",
    name: "Stainless Steel Spokes 280mm (Pack of 36)",
    category: "WHEEL",
    type: "RAW_MATERIAL",
    unit: "SET",
    safety_stock: 100,
    cost: "$8.20",
    lead_time: "5 days",
  },
  {
    id: 4,
    part_number: "XB-RAW-HYD-CAL",
    name: "Dual-Piston Hydraulic Disc Brake Caliper",
    category: "BRAKE",
    type: "RAW_MATERIAL",
    unit: "PCS",
    safety_stock: 30,
    cost: "$32.00",
    lead_time: "14 days",
  },
];

export const MaterialsPage: React.FC = () => {
  const [search, setSearch] = useState("");

  const filtered = MOCK_MATERIALS.filter(
    (m) =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.part_number.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div>
      <PageHeader
        title="Raw Materials & Components Catalog"
        subtitle="Master items list, engineering part numbers, stock parameters and supplier lead times"
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            New Material
          </Button>
        }
      />

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
          <div className="search-box">
            <Search size={16} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Search by part # or name..."
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
                <th>Category</th>
                <th>Item Type</th>
                <th>UoM</th>
                <th>Safety Stock</th>
                <th>Std Cost</th>
                <th>Lead Time</th>
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
                  <td>
                    <Badge color="purple">{item.category}</Badge>
                  </td>
                  <td>
                    <Badge color="cyan">{item.type}</Badge>
                  </td>
                  <td>{item.unit}</td>
                  <td>{item.safety_stock} {item.unit}</td>
                  <td>{item.cost}</td>
                  <td>{item.lead_time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
