import React from "react";
import { Plus, Shield, User } from "lucide-react";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { PageHeader } from "@/components/PageHeader";

const MOCK_USERS = [
  {
    id: 1,
    name: "System Administrator",
    email: "admin@xbike.local",
    roles: ["ADMIN", "MANAGER"],
    status: "ACTIVE",
    lastLogin: "2026-10-01 07:45",
  },
  {
    id: 2,
    name: "Jane Doe",
    email: "production.lead@xbike.local",
    roles: ["PRODUCTION"],
    status: "ACTIVE",
    lastLogin: "2026-10-01 06:10",
  },
  {
    id: 3,
    name: "Nguyen Van Binh",
    email: "warehouse@xbike.local",
    roles: ["WAREHOUSE"],
    status: "ACTIVE",
    lastLogin: "2026-09-30 18:20",
  },
];

export const UsersPage: React.FC = () => {
  return (
    <div>
      <PageHeader
        title="User Access & Role Management"
        subtitle="Manage operators, factory floor technicians, warehouse managers and role permissions"
        action={
          <Button variant="primary" icon={<Plus size={16} />}>
            Invite User
          </Button>
        }
      />

      <Card>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Operator Name</th>
                <th>Email Address</th>
                <th>Assigned Roles</th>
                <th>Account Status</th>
                <th>Last Active</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_USERS.map((u) => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 600 }}>{u.name}</td>
                  <td>{u.email}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6 }}>
                      {u.roles.map((r) => (
                        <Badge key={r} color={r === "ADMIN" ? "purple" : "cyan"}>
                          {r}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td>
                    <Badge color="emerald">{u.status}</Badge>
                  </td>
                  <td style={{ color: "var(--text-muted)" }}>{u.lastLogin}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
