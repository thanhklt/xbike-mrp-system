import React from "react";
import { Bike, Layers, Plus } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_PRODUCTS = [
  {
    id: 1,
    sku: "XB-BIKE-URBAN-01",
    name: "xBike Urban Commuter E-Bike",
    category: "COMMUTER / URBAN",
    bomCode: "BOM-XB-URBAN-01",
    standardCost: "$1,250.00",
    retailPrice: "$2,199.00",
    status: "ACTIVE",
  },
  {
    id: 2,
    sku: "XB-BIKE-GRAVEL-PRO",
    name: "xBike Terra Gravel Carbon 11S",
    category: "GRAVEL / ADVENTURE",
    bomCode: "BOM-XB-GRAVEL-V2",
    standardCost: "$1,850.00",
    retailPrice: "$3,499.00",
    status: "ACTIVE",
  },
  {
    id: 3,
    sku: "XB-BIKE-CARGO-LONG",
    name: "xBike Hauler Cargo Longtail",
    category: "CARGO / UTILITY",
    bomCode: "BOM-XB-CARGO-01",
    standardCost: "$2,100.00",
    retailPrice: "$3,899.00",
    status: "PLANNED",
  },
];

export const ProductsPage: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="Finished Bicycle Models"
        subtitle="Catalog of finished goods, bike specifications and standard assembly configurations"
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            New Bike Model
          </Button>
        }
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 24 }}>
        {MOCK_PRODUCTS.map((prod) => (
          <Card key={prod.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div className="brand-icon" style={{ width: 42, height: 42 }}>
                <Bike size={22} />
              </div>
              <Badge color={prod.status === "ACTIVE" ? "emerald" : "amber"}>{prod.status}</Badge>
            </div>

            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: 4 }}>{prod.name}</h3>
            <code style={{ fontSize: "0.8rem", color: "var(--accent-cyan)", display: "block", marginBottom: 16 }}>
              {prod.sku}
            </code>

            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: "0.85rem", borderTop: "1px solid var(--bg-card-border)", paddingTop: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Category:</span>
                <span style={{ fontWeight: 500 }}>{prod.category}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Default BOM:</span>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "var(--accent-cyan)" }}>
                  <Layers size={13} /> {prod.bomCode}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>BOM Standard Cost:</span>
                <span style={{ fontWeight: 600 }}>{prod.standardCost}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>MSRP Price:</span>
                <span style={{ fontWeight: 700, color: "var(--accent-emerald)" }}>{prod.retailPrice}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
