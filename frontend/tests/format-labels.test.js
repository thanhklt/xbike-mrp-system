import assert from "node:assert/strict";
import { test } from "node:test";
import { ITEM_LABELS, ITEM_TYPES, colorLabel, quantity, unitLabel } from "../src/lib/format.js";

test("unit labels display Vietnamese names in lowercase", () => {
  for (const [code, label] of Object.entries({
    cai: "cái",
    chiec: "chiếc",
    bo: "bộ",
    cap: "cặp",
    cuon: "cuộn",
    hop: "hộp",
    goi: "gói",
    tam: "tấm",
    thanh: "thanh",
    met: "mét",
    kg: "kg",
    lit: "lít",
  })) {
    assert.equal(unitLabel(code), label);
  }
});

test("color labels display capitalized Vietnamese names", () => {
  for (const [code, label] of Object.entries({
    den: "Đen",
    trang: "Trắng",
    bac: "Bạc",
    xam: "Xám",
    do: "Đỏ",
    vang: "Vàng",
    cam: "Cam",
    hong: "Hồng",
    tim: "Tím",
    nau: "Nâu",
    xanh_duong: "Xanh dương",
    xanh_la: "Xanh lá",
  })) {
    assert.equal(colorLabel(code), label);
  }
});

test("unknown codes replace underscores with spaces", () => {
  assert.equal(unitLabel("thung_lon"), "thung lon");
  assert.equal(colorLabel("xanh_da_troi"), "xanh da troi");
  assert.equal(unitLabel("chiếc"), "chiếc");
  assert.equal(unitLabel("constructor"), "constructor");
});

test("missing codes display a dash", () => {
  for (const code of [null, undefined, ""]) {
    assert.equal(unitLabel(code), "—");
    assert.equal(colorLabel(code), "—");
  }
});

test("quantities combine formatted numbers with optional unit labels", () => {
  assert.equal(quantity(3, "chiec"), "3 chiếc");
  assert.equal(quantity(1200, "bo"), "1.200 bộ");
  assert.equal(quantity(0, "cai"), "0 cái");
  assert.equal(quantity(3, "thung_lon"), "3 thung lon");
  for (const unit of [null, undefined, ""]) {
    assert.equal(quantity(3, unit), "3");
  }
});

test("item choices use two types and preserve legacy labels", () => {
  assert.deepEqual(ITEM_TYPES, ["linh_kien", "thanh_pham"]);
  assert.equal(ITEM_LABELS.nguyen_vat_lieu, "Nguyên vật liệu");
  assert.equal(ITEM_LABELS.ban_thanh_pham, "Bán thành phẩm");
});
