import assert from "node:assert/strict";
import test from "node:test";
import { itemPayload, itemUnitOptions } from "../src/features/materials/itemForm.js";
import { unitLabel } from "../src/lib/format.js";

const values = {
  sku: " FRAME ",
  ten_mat_hang: " Khung xe ",
  loai_mat_hang: "linh_kien",
  don_vi_tinh: "cai",
  mau_sac: "",
  mo_ta: " Mô tả ",
  don_gia: "12500",
  ma_mat_hang: "must-not-be-sent",
  is_active: true,
  so_luong_ton: 999,
};

test("UC-10: component creation sends only editable v4 fields, preserving integer VND", () => {
  assert.deepEqual(itemPayload(values), {
    sku: "FRAME",
    ten_mat_hang: "Khung xe",
    loai_mat_hang: "linh_kien",
    don_vi_tinh: "cai",
    mau_sac: null,
    mo_ta: "Mô tả",
    don_gia: 12500,
  });
});

test("UC-16: a new finished item includes the first formula without client IDs or lifecycle", () => {
  const payload = itemPayload(
    { ...values, loai_mat_hang: "thanh_pham", don_gia: "0" },
    { lines: [{ key: "local-only", id: 77, mat_hang_id: "2", so_luong: "3", don_gia_thuc: 999 }] },
  );
  assert.equal(payload.loai_mat_hang, "thanh_pham");
  assert.equal(payload.don_gia, 0);
  assert.deepEqual(payload.bom, { chi_tiet: [{ mat_hang_id: 2, so_luong: 3 }] });
  assert.equal("ma_mat_hang" in payload, false);
  assert.equal("is_active" in payload, false);
  assert.equal("so_luong_ton" in payload, false);
});

test("UC-11: editing a finished item omits immutable type, generated code and formula", () => {
  const record = {
    id: 4,
    sku: "FRAME",
    ten_mat_hang: "Khung xe",
    don_vi_tinh: "chiếc",
    mau_sac: null,
    mo_ta: "Mô tả",
    don_gia: 12500,
    loai_mat_hang: "thanh_pham",
  };
  assert.deepEqual(
    itemPayload(
      { ...record, ten_mat_hang: "Tên cập nhật", mau_sac: "", don_gia: "12500" },
      { record, lines: [{ mat_hang_id: 1, so_luong: 999 }] },
    ),
    { ten_mat_hang: "Tên cập nhật" },
  );
});

test("report unit labels are accented while unknown server units remain readable", () => {
  assert.deepEqual(["cai", "chiec", "bo", "kg", "met", "cuon", "thung_lon", null].map(unitLabel), [
    "cái",
    "chiếc",
    "bộ",
    "kg",
    "mét",
    "cuộn",
    "thung lon",
    "—",
  ]);
});

test("UC-10/11: unit choices display accents and keep database codes in item payloads", () => {
  const options = itemUnitOptions();
  assert.deepEqual(options, [
    { value: "cai", label: "cái" },
    { value: "chiec", label: "chiếc" },
    { value: "bo", label: "bộ" },
    { value: "cap", label: "cặp" },
    { value: "cuon", label: "cuộn" },
    { value: "hop", label: "hộp" },
    { value: "goi", label: "gói" },
    { value: "tam", label: "tấm" },
    { value: "thanh", label: "thanh" },
    { value: "met", label: "mét" },
    { value: "kg", label: "kg" },
    { value: "lit", label: "lít" },
  ]);
  for (const { value } of options) {
    assert.equal(itemPayload({ ...values, don_vi_tinh: value }).don_vi_tinh, value);
    assert.equal(itemUnitOptions(value).filter((option) => option.value === value).length, 1);
  }
});

test("UC-11: legacy units remain selectable and are omitted when unchanged", () => {
  for (const unit of ["chiếc", "thung_lon"]) {
    const record = { ...values, sku: "FRAME", ten_mat_hang: "Khung xe", don_vi_tinh: unit };
    const options = itemUnitOptions(unit);
    assert.ok(options.some((option) => option.value === unit));
    assert.equal(new Set(options.map((option) => option.label)).size, options.length);
    const payload = itemPayload({ ...record, ten_mat_hang: "Khung xe mới" }, { record });
    assert.equal(payload.ten_mat_hang, "Khung xe mới");
    assert.equal("don_vi_tinh" in payload, false);
  }
  assert.equal(itemUnitOptions().length, 12);
});
