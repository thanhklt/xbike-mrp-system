import React from "react";
import { Mail, Phone, Plus, Truck } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_SUPPLIERS = [
  {
    id: 1,
    code: "SUP-SHIMANO-VN",
    name: "Shimano Global Bike Components",
    contact_name: "Kenji Sato",
    contact_email: "kenji.s@shimano-components.com",
    contact_phone: "+84-901-234-567",
    lead_time_days: 14,
    payment_terms_days: 30,
    status: "ACTIVE",
  },
  {
    id: 2,
    code: "SUP-ALUFRAME-CORP",
    name: "Apex Precision Alloy Frames",
    contact_name: "Le Van An",
    contact_email: "an.le@apex-frames.vn",
    contact_phone: "+84-918-765-432",
    lead_time_days: 21,
    payment_terms_days: 45,
    status: "ACTIVE",
  },
  {
    id: 3,
    code: "SUP-TEKTRO-BRAKES",
    name: "Tektro Hydraulic Braking Systems",
    contact_name: "Mei-Ling Chen",
    contact_email: "orders@tektro-systems.tw",
    contact_phone: "+886-4-2358-1234",
    lead_time_days: 18,
    payment_terms_days: 30,
    status: "ACTIVE",
  },
];

export const SuppliersPage: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="Approved Suppliers & Vendors"
        subtitle="Vendor directory, lead-time parameters and contractual payment terms"
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            Add Supplier
          </Button>
        }
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 24 }}>
        {MOCK_SUPPLIERS.map((s) => (
          <Card key={s.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div className="brand-icon" style={{ width: 40, height: 40 }}>
                <Truck size={20} />
              </div>
              <Badge color="emerald">{s.status}</Badge>
            </div>

            <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: 4 }}>{s.name}</h3>
            <code style={{ fontSize: "0.8rem", color: "var(--accent-cyan)", display: "block", marginBottom: 16 }}>
              {s.code}
            </code>

            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: "0.85rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)" }}>
                <Mail size={14} color="var(--text-muted)" /> {s.contact_email}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-secondary)" }}>
                <Phone size={14} color="var(--text-muted)" /> {s.contact_phone} ({s.contact_name})
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderTop: "1px solid var(--bg-card-border)",
                  paddingTop: 12,
                  marginTop: 6,
                }}
              >
                <div>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>
                    Avg Lead Time
                  </span>
                  <span style={{ fontWeight: 600, color: "var(--accent-amber)" }}>
                    {s.lead_time_days} Days
                  </span>
                </div>
                <div>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>
                    Terms
                  </span>
                  <span style={{ fontWeight: 600 }}>Net {s.payment_terms_days}</span>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
