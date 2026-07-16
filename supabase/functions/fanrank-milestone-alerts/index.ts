import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const DEFAULT_ORIGINS = ["https://eltonylfgi-blip.github.io"];
const MAX_REQUEST_BYTES = 4096;
const ALLOWED_MILESTONES = new Set([
  "published", "hearts_100", "above_average", "ai_90", "official_star",
]);

type AlertRequest = {
  receipt: string;
  email: string;
  milestones: string[];
  language: string;
  website?: string;
};

class RequestError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function allowedOrigin(origin: string): boolean {
  if (!origin) return false;
  const configured = (Deno.env.get("FANRANK_ALLOWED_ORIGINS") || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  if ([...DEFAULT_ORIGINS, ...configured].includes(origin)) return true;
  return /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
}

function cors(origin: string): HeadersInit {
  return {
    "Access-Control-Allow-Origin": origin || DEFAULT_ORIGINS[0],
    "Access-Control-Allow-Headers": "apikey, content-type, x-client-info",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function json(origin: string, status: number, body: Record<string, unknown>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...cors(origin),
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function parseRequest(raw: string): AlertRequest {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new RequestError(400, "Solicitud no válida.");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new RequestError(400, "Solicitud no válida.");
  }

  const input = parsed as Record<string, unknown>;
  const receipt = String(input.receipt || "").trim();
  const email = String(input.email || "").trim().toLowerCase();
  const language = input.language === "es" ? "es" : input.language === "en" ? "en" : "";
  const website = String(input.website || "").trim();
  const milestones = Array.isArray(input.milestones)
    ? input.milestones.map((value) => String(value))
    : [];

  if (website) throw new RequestError(400, "No se pudo guardar la preferencia.");
  if (!/^[A-Za-z0-9_-]{43}$/.test(receipt)) throw new RequestError(400, "Recibo no válido.");
  if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new RequestError(400, "Correo no válido.");
  }
  if (!language) throw new RequestError(400, "Idioma no válido.");
  if (milestones.length < 1 || milestones.length > 5) {
    throw new RequestError(400, "Elige al menos un logro.");
  }
  const unique = new Set(milestones);
  if (unique.size !== milestones.length || milestones.some((value) => !ALLOWED_MILESTONES.has(value))) {
    throw new RequestError(400, "Logro no válido.");
  }

  return { receipt, email, milestones, language };
}

Deno.serve(async (request) => {
  const origin = request.headers.get("origin") || "";
  if (request.method === "OPTIONS") {
    if (!allowedOrigin(origin)) return json(DEFAULT_ORIGINS[0], 403, { error: "Origen no permitido." });
    return new Response(null, { status: 204, headers: cors(origin) });
  }
  if (!allowedOrigin(origin)) return json(DEFAULT_ORIGINS[0], 403, { error: "Origen no permitido." });
  if (request.method !== "POST") return json(origin, 405, { error: "Método no permitido." });
  if (!(request.headers.get("content-type") || "").toLowerCase().startsWith("application/json")) {
    return json(origin, 415, { error: "Se esperaba JSON." });
  }

  const declaredLength = Number(request.headers.get("content-length") || "0");
  if (declaredLength > MAX_REQUEST_BYTES) {
    return json(origin, 413, { error: "Solicitud demasiado grande." });
  }

  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_REQUEST_BYTES) {
      throw new RequestError(413, "Solicitud demasiado grande.");
    }
    const input = parseRequest(raw);
    const url = Deno.env.get("SUPABASE_URL");
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!url || !serviceKey) throw new Error("Server configuration unavailable");

    const admin = createClient(url, serviceKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const receiptHash = await sha256Hex(input.receipt);
    const { error } = await admin.rpc("fr_register_milestone_subscription", {
      p_receipt_hash: receiptHash,
      p_email: input.email,
      p_milestones: input.milestones,
      p_language: input.language,
    });
    if (error) throw error;

    // Unknown but syntactically valid receipts deliberately receive the same response.
    // This prevents the endpoint from becoming a submission-existence oracle.
    return json(origin, 202, { accepted: true, delivery: "pending_provider" });
  } catch (error) {
    if (error instanceof RequestError) return json(origin, error.status, { error: error.message });
    return json(origin, 503, { error: "No se pudo guardar la preferencia ahora." });
  }
});
