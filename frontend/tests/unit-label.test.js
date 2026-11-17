import test from "node:test";
import assert from "node:assert/strict";
import { unitLabel } from "../src/lib/format.js";

test("unit labels translate known API codes and use main's missing-value label", () => {
  assert.equal(unitLabel("cai"), "cái");
  assert.equal(unitLabel("bo"), "bộ");
  assert.equal(unitLabel("chiec"), "chiếc");
  assert.equal(unitLabel("chiếc"), "chiếc");
  assert.equal(unitLabel("kg"), "kg");
  assert.equal(unitLabel("constructor"), "constructor");
  assert.equal(unitLabel(null), "—");
  assert.equal(unitLabel(undefined), "—");
});
