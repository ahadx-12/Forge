import assert from "node:assert/strict";
import { test } from "node:test";

async function loadApiModule(baseUrl: string) {
  process.env.NEXT_PUBLIC_API_BASE_URL = baseUrl;
  const moduleUrl = new URL("../src/lib/api.ts", import.meta.url);
  moduleUrl.searchParams.set("cachebust", Math.random().toString());
  return await import(moduleUrl.href);
}

test("apiUrl joins base URL and path without double slashes", async () => {
  const { apiUrl } = await loadApiModule("https://api.example.com/");
  assert.equal(apiUrl("/v1/documents/123"), "https://api.example.com/v1/documents/123");
  assert.equal(apiUrl("v1/documents/123"), "https://api.example.com/v1/documents/123");
});
