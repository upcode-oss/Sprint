import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import ts from "typescript";

const source = readFileSync(new URL("../features/setup/validation.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { setupValidation } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`
);

test("an administrator error on the Email step points back to the account field", () => {
  const result = setupValidation({
    "admin.password": ["Value error, Password must contain a number"],
  });
  assert.equal(result.step, 2);
  assert.equal(result.message, "Administrator password: Password must contain a number");
});

test("invalid SMTP configuration identifies the sender field on the email step", () => {
  const result = setupValidation({ "smtp.from_address": ["Enter a valid email address"] });
  assert.equal(result.step, 3);
  assert.equal(result.message, "SMTP sender email: Enter a valid email address");
});

test("multiple server errors show all messages and select the first affected step", () => {
  const result = setupValidation({
    "database.host": ["Field required"],
    "admin.email": ["Enter a valid email address"],
  });
  assert.equal(result.step, 1);
  assert.match(result.message, /Database host: Field required/);
  assert.match(result.message, /Administrator email: Enter a valid email address/);
});

test("unknown request fields remain visible without forcing a different step", () => {
  assert.deepEqual(setupValidation({ request: ["Invalid configuration"] }), {
    step: undefined,
    message: "request: Invalid configuration",
  });
});
