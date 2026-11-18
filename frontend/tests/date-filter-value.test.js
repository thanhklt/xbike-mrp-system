import assert from "node:assert/strict";
import test from "node:test";
import { dateFilterDisplayValue, dateFilterIsoValue } from "../src/components/dateFilterValue.js";

test("date filters show day/month/year and send ISO dates without timezone shifts", () => {
  for (const [display, iso] of [
    ["01/02/2026", "2026-02-01"],
    ["13/11/2026", "2026-11-13"],
    ["31/12/2026", "2026-12-31"],
    ["01/01/0001", "0001-01-01"],
  ]) {
    assert.equal(dateFilterIsoValue(display), iso);
    assert.equal(dateFilterIsoValue(iso), iso);
    assert.equal(dateFilterDisplayValue(iso), display);
    assert.equal(dateFilterDisplayValue(display), display);
  }
});

test("date filters validate real calendar days including leap years", () => {
  assert.equal(dateFilterIsoValue("29/02/2024"), "2024-02-29");
  assert.equal(dateFilterIsoValue("29/02/2000"), "2000-02-29");
  for (const value of [
    "29/02/2026",
    "29/02/1900",
    "31/04/2026",
    "00/11/2026",
    "01/13/2026",
    "01/01/0000",
    "2026-02-31",
  ]) {
    assert.equal(dateFilterIsoValue(value), null, value);
  }
});

test("partial or malformed dates stay editable but are not valid query dates", () => {
  for (const value of ["1", "13/", "13/11/", "1/2/2026", "13-Feb-2026", "13/11/26"]) {
    assert.equal(dateFilterIsoValue(value), null);
    assert.equal(dateFilterDisplayValue(value), value);
  }
  assert.equal(dateFilterIsoValue(""), "");
  assert.equal(dateFilterDisplayValue(""), "");
  assert.equal(dateFilterDisplayValue(undefined), "");
});
