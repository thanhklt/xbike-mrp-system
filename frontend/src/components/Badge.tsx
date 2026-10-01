import React from "react";

interface BadgeProps {
  color?: "cyan" | "emerald" | "amber" | "rose" | "purple";
  children: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({ color = "cyan", children }) => {
  return <span className={`badge badge-${color}`}>{children}</span>;
};
