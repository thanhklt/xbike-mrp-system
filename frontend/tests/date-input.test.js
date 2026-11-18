import assert from "node:assert/strict";
import { test } from "node:test";
import { dmyToIso, isoToDmy, maskDmy } from "../src/lib/dateInput.js";

test("ISO dates display as dd/mm/yyyy", () => {
  assert.equal(isoToDmy("2026-11-05"), "05/11/2026");
  assert.equal(isoToDmy("2024-02-29"), "29/02/2024");
  for (const value of ["", null, undefined, "invalid", "2026-2-05", "2026-02-31", "0000-01-01"])
    assert.equal(isoToDmy(value), "");
});

test("the date mask keeps eight digits and inserts separators", () => {
  for (const [text, expected] of [
    ["", ""], ["0", "0"], ["05", "05"], ["051", "05/1"],
    ["0511", "05/11"], ["05112026", "05/11/2026"],
    ["05/11/2026", "05/11/2026"], ["ab05-11-202699", "05/11/2026"],
  ]) assert.equal(maskDmy(text), expected);
});

test("only complete calendar dates convert to ISO", () => {
  assert.equal(dmyToIso("05/11/2026"), "2026-11-05");
  assert.equal(dmyToIso("29/02/2024"), "2024-02-29");
  assert.equal(dmyToIso("29/02/2000"), "2000-02-29");
  for (const value of ["", "05/11/202", "5/11/2026", "31/02/2026", "29/02/2026",
    "29/02/1900", "01/13/2026", "00/11/2026", "01/00/2026", "01/01/0000"])
    assert.equal(dmyToIso(value), null);
});

test("employee short year format dd/mm/yy", () => {
  assert.equal(isoToDmy("2026-11-05", true), "05/11/26");
  assert.equal(isoToDmy("2024-02-29", true), "29/02/24");
  assert.equal(isoToDmy("1999-11-05", true), "05/11/99");
  assert.equal(isoToDmy("2100-11-05", true), "05/11/00");
  assert.equal(isoToDmy("2026-02-29", true), "");
  assert.equal(isoToDmy("2026-02-31", true), "");
  assert.equal(maskDmy("051126", true), "05/11/26");
  assert.equal(dmyToIso("05/11/26", true), "2026-11-05");
  assert.equal(dmyToIso("29/02/24", true), "2024-02-29");
  assert.equal(dmyToIso("29/02/26", true), null);
  assert.equal(dmyToIso("31/02/26", true), null);
  assert.equal(dmyToIso("05/11/2026", true), null);
  // Manager four-digit dates unchanged
  assert.equal(isoToDmy("1999-11-05", false), "05/11/1999");
  assert.equal(isoToDmy("2100-11-05", false), "05/11/2100");
  assert.equal(isoToDmy("2026-11-05", false), "05/11/2026");
});
