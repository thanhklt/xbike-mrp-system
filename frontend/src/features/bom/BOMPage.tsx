import React, { useState } from "react";
import { ChevronDown, ChevronRight, Layers, Plus } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_BOM = {
  code: "BOM-XB-URBAN-01",
  product: "xBike Urban Commuter E-Bike",
  version: "1.0",
  status: "ACTIVE",
  items: [
    {
      level: 1,
      partNumber: "XB-SUB-WHEEL-F",
      name: "Front Wheel Assembly 700c",
      qty: 1,
      uom: "SET",
      scrap: "0%",
      notes: "Sub-assembly with Shimano Hub & disc rotor",
      subItems: [
        { partNumber: "XB-RAW-RIM-700C", name: "Double-wall Rim 700c", qty: 1, uom: "PCS" },
        { partNumber: "XB-RAW-SPOKE-280", name: "Spokes Stainless 280mm", qty: 36, uom: "PCS" },
        { partNumber: "XB-RAW-HUB-F", name: "Front Disc Hub 36H", qty: 1, uom: "PCS" },
      ],
    },
    {
      level: 1,
      partNumber: "XB-RAW-CHN-11S",
      name: "11-Speed Bicycle Chain with Quick Link",
      qty: 1,
      uom: "PCS",
      scrap: "2%",
      notes: "Trim to 114 links before installing",
    },
    {
      level: 1,
      partNumber: "XB-RAW-FRM-ALU",
      name: "Hydroformed 6061 Aluminum E-Frame",
      qty: 1,
      uom: "PCS",
      scrap: "0%",
      notes: "Integrated downtube battery compartment",
    },
    {
      level: 1,
      partNumber: "XB-RAW-HYD-CAL",
      name: "Dual-Piston Hydraulic Disc Caliper Set",
      qty: 2,
      uom: "SET",
      scrap: "0%",
      notes: "Front (160mm) & Rear (160mm)",
    },
  ],
};

export const BOMPage: React.FC = () => {
  const [expandedLevels, setExpandedLevels] = useState<{ [key: string]: boolean }>({
    "XB-SUB-WHEEL-F": true,
  });

  const toggleExpand = (key: string) => {
    setExpandedLevels((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div>
      <PageHeader
        title="Bill of Materials (BOM)"
        subtitle="Hierarchical multi-level engineering recipes and sub-assembly trees"
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            Create BOM Revision
          </Button>
        }
      />

      <Card
        title={`Recipe: ${MOCK_BOM.product} (${MOCK_BOM.code})`}
        action={
          <div style={{ display: "flex", gap: 8 }}>
            <Badge color="cyan">Rev {MOCK_BOM.version}</Badge>
            <Badge color="emerald">{MOCK_BOM.status}</Badge>
          </div>
        }
      >
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 40 }}>Level</th>
                <th>Component Part #</th>
                <th>Description</th>
                <th>Qty Required</th>
                <th>UoM</th>
                <th>Scrap Factor</th>
                <th>Assembly Instructions / Notes</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_BOM.items.map((item) => (
                <React.Fragment key={item.partNumber}>
                  <tr style={{ background: item.subItems ? "rgba(255, 255, 255, 0.02)" : "transparent" }}>
                    <td>
                      <span style={{ fontWeight: 700, color: "var(--accent-cyan)" }}>
                        .{item.level}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        {item.subItems ? (
                          <button
                            onClick={() => toggleExpand(item.partNumber)}
                            style={{ background: "none", border: "none", color: "var(--accent-cyan)", cursor: "pointer" }}
                          >
                            {expandedLevels[item.partNumber] ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                          </button>
                        ) : (
                          <span style={{ width: 16 }} />
                        )}
                        <code>{item.partNumber}</code>
                      </div>
                    </td>
                    <td style={{ fontWeight: item.subItems ? 600 : 400 }}>{item.name}</td>
                    <td>{item.qty}</td>
                    <td>{item.uom}</td>
                    <td>{item.scrap}</td>
                    <td style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>{item.notes}</td>
                  </tr>

                  {/* Sub-assembly nested children */}
                  {item.subItems && expandedLevels[item.partNumber] &&
                    item.subItems.map((sub) => (
                      <tr key={sub.partNumber} style={{ background: "rgba(6, 182, 212, 0.03)" }}>
                        <td>
                          <span style={{ color: "var(--text-muted)", paddingLeft: 12 }}>..2</span>
                        </td>
                        <td style={{ paddingLeft: 32 }}>
                          <code style={{ color: "var(--text-secondary)" }}>{sub.partNumber}</code>
                        </td>
                        <td style={{ color: "var(--text-secondary)" }}>{sub.name}</td>
                        <td>{sub.qty}</td>
                        <td>{sub.uom}</td>
                        <td>0%</td>
                        <td style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>Sub-assembly component</td>
                      </tr>
                    ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
