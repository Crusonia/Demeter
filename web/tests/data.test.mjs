import assert from "node:assert/strict";
import { test } from "node:test";
import { chartRows, csv, experimentSignature } from "../lib/data.mjs";
test("tables preserve line values, missing values and heatmap coordinates", () => {
  assert.deepEqual(
    chartRows({ data: [{ name: "Test", x: [0, 1], y: [7, null] }] }),
    [
      { series: "Test", x: 0, y: 7, value: null },
      { series: "Test", x: 1, y: null, value: null },
    ],
  );
  assert.deepEqual(
    chartRows({ data: [{ name: "Age", x: [20, 21], y: [0], z: [[5, 6]] }] }),
    [
      { series: "Age", x: 20, y: 0, value: 5 },
      { series: "Age", x: 21, y: 0, value: 6 },
    ],
  );
});
test("CSV keeps numeric negatives, quotes labels, neutralizes spreadsheet formulas", () => {
  assert.equal(
    csv([{ series: '=run("x")', x: -3, y: null, value: "a,b" }]),
    'series,x,y,value\r\n"\'=run(""x"")","-3","","a,b"',
  );
});
test("editing notes does not mark calculated results stale but changing a seed does", () => {
  const a = {
    catalog_id: "core",
    scenario: { years: 3 },
    overrides: {},
    profile: "preview",
    seed: 42,
    reference_id: null,
  };
  assert.equal(
    experimentSignature(a),
    experimentSignature({ ...a, notes: "learned something" }),
  );
  assert.notEqual(
    experimentSignature(a),
    experimentSignature({ ...a, seed: 43 }),
  );
});
