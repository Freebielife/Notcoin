"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const text = fs.readFileSync("web/app.js", "utf8");
const source = text.match(/function serviceRole\(wallet\)\{[\s\S]*?\n\}/);
assert.ok(source, "Service-role filter is present");
const snapshot = {identity:{byWallet:{
  "contract":{role:"unclassified_contract"},
  "exchange":{role:"Bitget12"},
  "dex":{role:"STON.fi DEX"},
  "vault":{role:"Storm Trade Vault"},
  "blank":{role:""}
}}};
const role = new Function("snapshot", "lang", source[0]+";return serviceRole;")(snapshot, "ru");
test("unclassified contract has an explicit generic label in service/contract ranking", () => {
  assert.equal(role("contract"), "Смарт-контракт");
  assert.equal(role("unknown"), null);
  assert.equal(role("blank"), null);
});
test("verified exchange and protocol names remain service identities", () => {
  assert.equal(role("exchange"), "Bitget12");
  assert.equal(role("dex"), "STON.fi DEX");
  assert.equal(role("vault"), "Storm Trade Vault");
});
