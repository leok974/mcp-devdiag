// devdiag.ts - TypeScript client SDK for mcp-devdiag
// Usage: Copy to your project and install: npm install zod

import { z } from "zod";

/**
 * ProbeResult schema - standardized diagnostic probe result
 */
export const ProbeResult = z.object({
  probe: z.string().optional(),
  problems: z.array(z.string()),
  remediation: z.array(z.string()).default([]),
  evidence: z.record(z.any()),
  severity: z.enum(["info", "warn", "error", "critical"]).optional(),
});
export type ProbeResult = z.infer<typeof ProbeResult>;

/**
 * StatusPlus response - aggregate diagnostics with scoring and fixes
 */
export const StatusPlus = z.object({
  ok: z.boolean(),
  score: z.number(),
  severity: z.enum(["info", "warn", "error", "critical"]).optional(),
  problems: z.array(z.string()),
  fixes: z.record(z.array(z.string())),
  evidence: z.record(z.any()),
});
export type StatusPlus = z.infer<typeof StatusPlus>;

/**
 * DevDiag client configuration
 */
export interface DevDiagConfig {
  baseUrl: string;
  jwt: string;
}

/**
 * Get aggregate diagnostics with scoring and fix recommendations
 *
 * @param config - Client configuration (baseUrl, jwt)
 * @param targetUrl - URL to diagnose
 * @param preset - Probe preset ("chat", "embed", "app", "full")
 * @returns StatusPlus response with ok, score, problems, fixes, evidence
 */
export async function statusPlus(
  config: DevDiagConfig,
  targetUrl: string,
  preset: string = "app"
): Promise<StatusPlus> {
  const url = new URL("/mcp/diag/status_plus", config.baseUrl);
  url.searchParams.set("base_url", targetUrl);
  url.searchParams.set("preset", preset);

  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${config.jwt}` },
  });

  if (!response.ok) {
    throw new Error(`DevDiag API error: ${response.status} ${response.statusText}`);
  }

  const json = await response.json();
  return StatusPlus.parse(json);
}

/**
 * Fast HTTP-only quickcheck (CI-safe, no browser)
 *
 * @param config - Client configuration (baseUrl, jwt)
 * @param targetUrl - URL to check
 * @returns Quickcheck result with CSP/iframe compatibility
 */
export async function quickcheck(
  config: DevDiagConfig,
  targetUrl: string
): Promise<any> {
  const url = new URL("/mcp/diag/quickcheck", config.baseUrl);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.jwt}`,
    },
    body: JSON.stringify({ url: targetUrl }),
  });

  if (!response.ok) {
    throw new Error(`DevDiag API error: ${response.status} ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Get remediation steps for specific problem codes
 *
 * @param config - Client configuration (baseUrl, jwt)
 * @param problems - Array of problem codes
 * @returns Remediation steps mapped by problem code
 */
export async function remediation(
  config: DevDiagConfig,
  problems: string[]
): Promise<Record<string, string[]>> {
  const url = new URL("/mcp/diag/remediation", config.baseUrl);

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.jwt}`,
    },
    body: JSON.stringify({ problems }),
  });

  if (!response.ok) {
    throw new Error(`DevDiag API error: ${response.status} ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Get ProbeResult JSON schema
 *
 * @param config - Client configuration (baseUrl, jwt)
 * @returns JSON schema for ProbeResult type
 */
export async function getSchema(config: DevDiagConfig): Promise<any> {
  const url = new URL("/mcp/diag/schema/probe_result", config.baseUrl);

  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${config.jwt}` },
  });

  if (!response.ok) {
    throw new Error(`DevDiag API error: ${response.status} ${response.statusText}`);
  }

  return await response.json();
}

// Example usage:
//
// const client = { baseUrl: "https://diag.example.com", jwt: process.env.DEVDIAG_JWT! };
//
// const result = await statusPlus(client, "https://app.example.com", "full");
// if (!result.ok) {
//   console.error("Problems detected:", result.problems);
//   console.log("Fixes:", result.fixes);
// }
