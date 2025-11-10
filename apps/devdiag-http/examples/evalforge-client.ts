// EvalForge integration example for DevDiag HTTP API
// 
// Server-side config (Node.js/Express):
//   process.env.DEVDIAG_BASE = "http://localhost:8080"  // or production URL
//
// Frontend usage:
//   Call this from your React/Next.js components

export interface DiagRequest {
  url: string;
  preset?: "chat" | "embed" | "app" | "full";
  suppress?: string[];
  extra_args?: string[];
}

export interface DiagResponse {
  ok: boolean;
  url: string;
  preset: string;
  result: {
    problems: string[];
    fixes: Record<string, string[]>;
    evidence: Record<string, any>;
    score?: number;
    severity?: "info" | "warn" | "error" | "critical";
  };
}

/**
 * Run DevDiag diagnostics on a URL
 * 
 * @param baseUrl - DevDiag HTTP server URL (from env)
 * @param request - Diagnostic request parameters
 * @param jwt - Optional JWT token (required if JWKS_URL is set)
 * @returns Diagnostic results with problems, fixes, and evidence
 */
export async function runDiagnostics(
  baseUrl: string,
  request: DiagRequest,
  jwt?: string
): Promise<DiagResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  
  if (jwt) {
    headers.Authorization = `Bearer ${jwt}`;
  }

  const response = await fetch(`${baseUrl}/diag/run`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      url: request.url,
      preset: request.preset || "app",
      suppress: request.suppress,
      extra_args: request.extra_args,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`DevDiag API error: ${error.detail || response.statusText}`);
  }

  return response.json();
}

/**
 * Check server health
 */
export async function checkHealth(baseUrl: string): Promise<{ ok: boolean; service: string; version: string }> {
  const response = await fetch(`${baseUrl}/healthz`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Get available probe presets
 */
export async function getProbePresets(baseUrl: string): Promise<{ presets: string[]; notes: string }> {
  const response = await fetch(`${baseUrl}/probes`);
  if (!response.ok) {
    throw new Error(`Failed to fetch presets: ${response.statusText}`);
  }
  return response.json();
}

// Example usage in EvalForge:
//
// const DEVDIAG_BASE = process.env.NEXT_PUBLIC_DEVDIAG_BASE || "http://localhost:8080";
//
// // In your component or API route:
// try {
//   const result = await runDiagnostics(DEVDIAG_BASE, {
//     url: "https://myapp.com/chat",
//     preset: "chat",
//     suppress: ["CSP_FRAME_ANCESTORS"],
//   });
//
//   if (!result.result.ok) {
//     console.error("Problems detected:", result.result.problems);
//     console.log("Suggested fixes:", result.result.fixes);
//   }
// } catch (error) {
//   console.error("DevDiag error:", error);
// }
