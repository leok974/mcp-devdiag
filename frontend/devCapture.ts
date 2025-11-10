/**
 * Production-safe frontend telemetry capture with sampling and privacy controls.
 * Sends telemetry via sendBeacon() for reliability across page navigation/crashes.
 */

interface DevCaptureConfig {
  samplingRate: number; // 0.0-1.0
  endpoint: string; // e.g., "/api/telemetry"
  redactParams: string[]; // Query params to scrub
  redactHeaders: string[]; // Headers to filter
  maxBatchSize: number;
  flushIntervalMs: number;
}

interface NetworkSpan {
  timestamp: number;
  method: string;
  url: string;
  status?: number;
  latencyMs?: number;
  error?: string;
}

interface FrontendEvent {
  timestamp: number;
  level: "debug" | "info" | "warn" | "error";
  message: string;
  context?: Record<string, unknown>;
}

class DevCapture {
  private config: DevCaptureConfig;
  private networkBuffer: NetworkSpan[] = [];
  private eventBuffer: FrontendEvent[] = [];
  private flushTimer?: number;
  private sessionSample: boolean; // Session-level sampling decision

  constructor(config: Partial<DevCaptureConfig> = {}) {
    this.config = {
      samplingRate: config.samplingRate ?? 0.02, // Default 2%
      endpoint: config.endpoint ?? "/api/telemetry",
      redactParams: config.redactParams ?? ["token", "key", "code", "session"],
      redactHeaders: config.redactHeaders ?? [
        "authorization",
        "cookie",
        "x-api-key",
      ],
      maxBatchSize: config.maxBatchSize ?? 50,
      flushIntervalMs: config.flushIntervalMs ?? 5000,
    };

    // Session-level sampling: decide once per session
    this.sessionSample = Math.random() < this.config.samplingRate;

    if (this.sessionSample) {
      this.setupInterceptors();
      this.startFlushTimer();
    }
  }

  private setupInterceptors() {
    // Intercept fetch()
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const startTime = performance.now();
      const [resource, init] = args;
      const url =
        typeof resource === "string" ? resource : (resource as Request).url;
      const method =
        init?.method || (resource as Request).method || "GET";

      try {
        const response = await originalFetch(...args);
        const latencyMs = performance.now() - startTime;

        this.captureNetwork({
          timestamp: Date.now(),
          method,
          url: this.scrubUrl(url),
          status: response.status,
          latencyMs: Math.round(latencyMs),
        });

        return response;
      } catch (error) {
        const latencyMs = performance.now() - startTime;
        this.captureNetwork({
          timestamp: Date.now(),
          method,
          url: this.scrubUrl(url),
          latencyMs: Math.round(latencyMs),
          error: error instanceof Error ? error.message : String(error),
        });
        throw error;
      }
    };

    // Intercept console errors
    const originalError = console.error;
    console.error = (...args) => {
      this.captureEvent({
        timestamp: Date.now(),
        level: "error",
        message: args.map((a) => String(a)).join(" "),
      });
      originalError.apply(console, args);
    };

    // Global error handler
    window.addEventListener("error", (event) => {
      this.captureEvent({
        timestamp: Date.now(),
        level: "error",
        message: event.message,
        context: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
      });
    });

    // Unhandled promise rejections
    window.addEventListener("unhandledrejection", (event) => {
      this.captureEvent({
        timestamp: Date.now(),
        level: "error",
        message: `Unhandled rejection: ${event.reason}`,
      });
    });
  }

  private scrubUrl(url: string): string {
    try {
      const parsed = new URL(url, window.location.origin);

      // Redact sensitive query params
      for (const param of this.config.redactParams) {
        if (parsed.searchParams.has(param)) {
          parsed.searchParams.set(param, "[REDACTED]");
        }
      }

      return parsed.toString();
    } catch {
      // Invalid URL, return as-is
      return url;
    }
  }

  public captureNetwork(span: NetworkSpan) {
    if (!this.sessionSample) return;

    this.networkBuffer.push(span);
    if (this.networkBuffer.length >= this.config.maxBatchSize) {
      this.flush();
    }
  }

  public captureEvent(event: FrontendEvent) {
    if (!this.sessionSample) return;

    this.eventBuffer.push(event);
    if (this.eventBuffer.length >= this.config.maxBatchSize) {
      this.flush();
    }
  }

  private startFlushTimer() {
    this.flushTimer = window.setInterval(() => {
      this.flush();
    }, this.config.flushIntervalMs);
  }

  public flush() {
    if (this.networkBuffer.length === 0 && this.eventBuffer.length === 0) {
      return;
    }

    const payload = {
      network: this.networkBuffer.splice(0),
      events: this.eventBuffer.splice(0),
    };

    // Use sendBeacon for reliability (works even during page unload)
    const blob = new Blob([JSON.stringify(payload)], {
      type: "application/json",
    });
    navigator.sendBeacon(this.config.endpoint, blob);
  }

  public destroy() {
    if (this.flushTimer !== undefined) {
      clearInterval(this.flushTimer);
    }
    this.flush(); // Final flush
  }
}

// Singleton instance
let devCaptureInstance: DevCapture | null = null;

export function initDevCapture(
  config: Partial<DevCaptureConfig> = {}
): DevCapture {
  if (devCaptureInstance) {
    devCaptureInstance.destroy();
  }
  devCaptureInstance = new DevCapture(config);
  return devCaptureInstance;
}

export function getDevCapture(): DevCapture | null {
  return devCaptureInstance;
}

// Auto-flush on page unload
if (typeof window !== "undefined") {
  window.addEventListener("beforeunload", () => {
    devCaptureInstance?.flush();
  });
}
