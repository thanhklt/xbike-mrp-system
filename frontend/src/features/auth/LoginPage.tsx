import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bike, Lock, Mail } from "lucide-react";
import { Button } from "@/components/Button";

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState("admin@xbike.local");
  const [password, setPassword] = useState("admin123");
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem("xbike_access_token", "mock-token-admin");
    navigate("/");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "radial-gradient(circle at 50% 50%, #1e293b 0%, #0a0f1d 100%)",
        padding: 20,
      }}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: 420,
          padding: 36,
          border: "1px solid rgba(255, 255, 255, 0.1)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            className="brand-icon"
            style={{ width: 48, height: 48, margin: "0 auto 12px auto" }}
          >
            <Bike size={28} />
          </div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 700 }}>xBike MRP System</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginTop: 4 }}>
            Sign in to access manufacturing control & MRP
          </p>
        </div>

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", marginBottom: 6, color: "var(--text-secondary)" }}>
              Email Address
            </label>
            <div className="search-box" style={{ width: "100%" }}>
              <Mail size={16} color="var(--text-muted)" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", marginBottom: 6, color: "var(--text-secondary)" }}>
              Password
            </label>
            <div className="search-box" style={{ width: "100%" }}>
              <Lock size={16} color="var(--text-muted)" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <Button type="submit" variant="primary" style={{ width: "100%", marginTop: 8 }}>
            Sign In to Dashboard
          </Button>
        </form>
      </div>
    </div>
  );
};
