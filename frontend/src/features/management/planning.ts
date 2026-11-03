import type { Item, MaterialDemand, OrderKind, ProductionPlan } from "./types";

export const bikeBom = [
  ["frame", 1],
  ["fork", 1],
  ["wheel", 2],
  ["tires", 2],
  ["chain", 1],
  ["pedals", 2],
  ["brakes", 2],
  ["seat", 1],
] as const;
export const wheelBom = [
  ["rim", 1],
  ["hub", 1],
  ["spokes", 36],
] as const;

export function itemById(items: readonly Item[], id: string): Item {
  const item = items.find((entry) => entry.id === id);
  if (!item) throw new Error("Không tìm thấy mặt hàng.");
  return item;
}

export function materialDemand(
  items: readonly Item[],
  kind: OrderKind,
  quantity: number,
): MaterialDemand[] {
  return (kind === "bike" ? bikeBom : wheelBom).map(([itemId, perUnit]) => {
    const available = itemById(items, itemId).stock;
    const required = perUnit * quantity;
    return { itemId, perUnit, required, available, missing: Math.max(0, required - available) };
  });
}

export function calculatePlan(
  items: readonly Item[],
  productId: string,
  quantity: number,
): ProductionPlan {
  const availableProducts = itemById(items, productId).stock;
  const useProducts = Math.min(quantity, availableProducts);
  const bikesToMake = Math.max(0, quantity - useProducts);
  const wheelsRequired = bikesToMake * 2;
  const useWheels = Math.min(wheelsRequired, itemById(items, "wheel").stock);
  const wheelsToMake = wheelsRequired - useWheels;
  return {
    requested: quantity,
    availableProducts,
    useProducts,
    bikesToMake,
    wheelsRequired,
    useWheels,
    wheelsToMake,
    bikeMaterials: materialDemand(items, "bike", bikesToMake),
    wheelMaterials: materialDemand(items, "wheel", wheelsToMake),
  };
}

export const number = (value: number) => new Intl.NumberFormat("vi-VN").format(value);
export const money = (value: number) =>
  new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
export const documentTotal = (lines: readonly { quantity: number; price: number }[]) =>
  lines.reduce((total, line) => total + line.quantity * line.price, 0);
export const today = () => new Date().toLocaleDateString("en-CA");
