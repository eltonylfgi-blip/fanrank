import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const BUCKET = "fanrank-owner-feedback";
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const ORIGIN = "https://eltonylfgi-blip.github.io";
const ALLOWED_MIME: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

class RequestError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function headers(origin: string): HeadersInit {
  return {
    "Access-Control-Allow-Origin": origin || ORIGIN,
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Max-Age": "86400",
    "Cache-Control": "no-store",
    "Vary": "Origin",
  };
}

function reply(origin: string, status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...headers(origin), "Content-Type": "application/json; charset=utf-8" },
  });
}

function permittedOrigin(origin: string): boolean {
  return origin === ORIGIN || /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
}

function textField(form: FormData, name: string, max: number, required = false): string {
  const value = String(form.get(name) || "").trim();
  if (required && !value) throw new RequestError(400, `Falta ${name}.`);
  if (value.length > max) throw new RequestError(400, `${name} es demasiado largo.`);
  return value;
}

function imageMime(bytes: Uint8Array): string | null {
  const starts = (...values: number[]) => values.every((value, index) => bytes[index] === value);
  if (starts(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a)) return "image/png";
  if (starts(0xff, 0xd8, 0xff)) return "image/jpeg";
  if (
    String.fromCharCode(...bytes.slice(0, 4)) === "RIFF" &&
    String.fromCharCode(...bytes.slice(8, 12)) === "WEBP"
  ) return "image/webp";
  return null;
}

Deno.serve(async (request) => {
  const origin = request.headers.get("origin") || "";
  if (request.method === "OPTIONS") {
    return permittedOrigin(origin)
      ? new Response(null, { status: 204, headers: headers(origin) })
      : reply(ORIGIN, 403, { error: "Origen no permitido." });
  }
  if (!permittedOrigin(origin)) return reply(ORIGIN, 403, { error: "Origen no permitido." });
  if (request.method !== "POST") return reply(origin, 405, { error: "Método no permitido." });

  let uploadedPath = "";
  try {
    if (!request.headers.get("content-type")?.toLowerCase().startsWith("multipart/form-data")) {
      throw new RequestError(415, "Se esperaba un formulario de feedback.");
    }
    const url = Deno.env.get("SUPABASE_URL");
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!url || !serviceKey) throw new Error("Supabase server env incompleto");
    const admin = createClient(url, serviceKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const token = (request.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
    const { data: userData, error: userError } = await admin.auth.getUser(token);
    if (userError || !userData.user) throw new RequestError(401, "Inicia sesión para enviar feedback.");

    const form = await request.formData();
    const section = textField(form, "section", 120, true);
    const pagePath = textField(form, "page_path", 500, true);
    const zone = textField(form, "zone", 80, true);
    const message = textField(form, "message", 2000, true);
    const priority = textField(form, "priority", 10) || "normal";
    if (!/^\/[A-Za-z0-9_./?=&%-]*$/.test(pagePath)) throw new RequestError(400, "La página no es válida.");
    if (!/^[a-z0-9_]{2,80}$/i.test(zone)) throw new RequestError(400, "La zona no es válida.");
    if (message.length < 3) throw new RequestError(400, "Explica un poco más el cambio.");
    if (!["low", "normal", "high"].includes(priority)) throw new RequestError(400, "La prioridad no es válida.");

    const { data: profile, error: profileError } = await admin
      .from("fr_sections")
      .select("slug,verification_status")
      .eq("slug", section)
      .maybeSingle();
    if (profileError) throw profileError;
    if (!profile || profile.verification_status !== "verified") {
      throw new RequestError(403, "Este perfil aún no está verificado.");
    }
    const { data: member, error: memberError } = await admin
      .from("fr_profile_members")
      .select("role,status")
      .eq("user_id", userData.user.id)
      .eq("section", section)
      .eq("status", "active")
      .in("role", ["owner", "admin"])
      .maybeSingle();
    if (memberError) throw memberError;
    if (!member) throw new RequestError(403, "Solo el equipo autorizado puede enviar este feedback.");

    const file = form.get("screenshot");
    if (file instanceof File && file.size > 0) {
      if (file.size > MAX_IMAGE_BYTES) throw new RequestError(413, "La captura supera 8 MB.");
      if (!ALLOWED_MIME[file.type]) throw new RequestError(415, "La captura debe ser JPG, PNG o WebP.");
      const buffer = await file.arrayBuffer();
      const detected = imageMime(new Uint8Array(buffer.slice(0, 16)));
      if (!detected || detected !== file.type) throw new RequestError(415, "La captura no coincide con un formato permitido.");
      uploadedPath = `${userData.user.id}/${section}/${crypto.randomUUID()}.${ALLOWED_MIME[detected]}`;
      const { error: uploadError } = await admin.storage.from(BUCKET).upload(uploadedPath, buffer, {
        contentType: detected,
        cacheControl: "3600",
        upsert: false,
      });
      if (uploadError) throw uploadError;
    } else if (file && !(file instanceof File)) {
      throw new RequestError(400, "La captura no es válida.");
    }

    const { error: insertError } = await admin.from("fr_owner_feedback").insert({
      user_id: userData.user.id,
      section,
      page_path: pagePath,
      zone,
      priority,
      message,
      screenshot_path: uploadedPath || null,
    });
    if (insertError) throw insertError;

    return reply(origin, 202, { ok: true, status: "new", screenshot: Boolean(uploadedPath) });
  } catch (error) {
    if (uploadedPath) {
      const url = Deno.env.get("SUPABASE_URL");
      const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
      if (url && serviceKey) {
        await createClient(url, serviceKey).storage.from(BUCKET).remove([uploadedPath]);
      }
    }
    if (error instanceof RequestError) return reply(origin, error.status, { error: error.message });
    console.error(JSON.stringify({ event: "fanrank_creator_feedback_error", message: error instanceof Error ? error.message : "unknown" }));
    return reply(origin, 500, { error: "No se pudo guardar el feedback privado. No se publicó nada." });
  }
});
