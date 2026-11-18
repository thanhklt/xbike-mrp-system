import assert from "node:assert/strict";
import test from "node:test";
import { pricedIssue } from "../src/features/material-issuing/issuePricing.js";

test("unapproved issues use catalog prices to calculate line and issue totals", () => {
  const firstLine = { mat_hang_id: 1, so_luong: 2, don_gia_thuc: null, tong_gia: null };
  const secondLine = { mat_hang_id: 2, so_luong: 3, don_gia_thuc: null, tong_gia: null };
  const record = { chi_tiet: [firstLine, secondLine], tong_tien: null };
  const items = [{ id: 2, don_gia: 3000 }, { id: 1, don_gia: "12500.50" }];

  assert.deepEqual(pricedIssue(record, items), {
    lines: [
      { ...firstLine, don_gia_thuc: "12500.50", tong_gia: 25001 },
      { ...secondLine, don_gia_thuc: 3000, tong_gia: 9000 },
    ],
    total: 34001,
  });
});

test("approved issues preserve frozen prices and totals when catalog prices differ", () => {
  const line = { mat_hang_id: 1, so_luong: 2, don_gia_thuc: 0, tong_gia: "0.00" };
  const record = { chi_tiet: [line], tong_tien: "0.00" };

  assert.deepEqual(pricedIssue(record, [{ id: 1, don_gia: 15000 }]), {
    lines: [line],
    total: "0.00",
  });
});

test("one missing catalog price leaves the affected line and issue total unpriced", () => {
  const knownLine = { mat_hang_id: 1, so_luong: 2, don_gia_thuc: null, tong_gia: null };
  const missingLine = { mat_hang_id: 3, so_luong: 4, don_gia_thuc: null, tong_gia: null };
  const record = { chi_tiet: [knownLine, missingLine], tong_tien: null };

  assert.deepEqual(pricedIssue(record, [{ id: 1, don_gia: 5000 }]), {
    lines: [{ ...knownLine, don_gia_thuc: 5000, tong_gia: 10000 }, missingLine],
    total: null,
  });
});
