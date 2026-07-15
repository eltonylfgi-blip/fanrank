import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const BUCKET = "fanrank-feedback-private";
const MAX_FILES = 3;
const MAX_FILE_BYTES = 5 * 1024 * 1024;
const MAX_TOTAL_BYTES = 15 * 1024 * 1024;
const MAX_REQUEST_BYTES = MAX_TOTAL_BYTES + 2 * 1024 * 1024;
const DEFAULT_ORIGINS = ["https://eltonylfgi-blip.github.io"];

const MIME_EXT: Record<string, string> = {
  "image/png": "png",
  "image/jpeg": "jpg",
  "image/webp": "webp",
};

class IntakeError extends Error {
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
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
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

function textField(form: FormData, name: string, max: number, required = false): string {
  const value = String(form.get(name) || "").trim();
  if (required && !value) throw new IntakeError(400, `Falta ${name}.`);
  if (value.length > max) throw new IntakeError(400, `${name} es demasiado largo.`);
  return value;
}

function boolField(form: FormData, name: string): boolean {
  return String(form.get(name) || "false") === "true";
}

function bytesEqual(bytes: Uint8Array, offset: number, expected: number[]): boolean {
  if (bytes.length < offset + expected.length) return false;
  return expected.every((value, index) => bytes[offset + index] === value);
}

function ascii(bytes: Uint8Array, offset: number, length: number): string {
  return String.fromCharCode(...bytes.slice(offset, offset + length));
}

function detectMime(bytes: Uint8Array): string | null {
  if (bytesEqual(bytes, 0, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return "image/png";
  if (bytesEqual(bytes, 0, [0xff, 0xd8, 0xff])) return "image/jpeg";
  if (ascii(bytes, 0, 4) === "RIFF" && ascii(bytes, 8, 4) === "WEBP") return "image/webp";
  return null;
}

function safeName(name: string): string {
  const cleaned = name.replace(/[\u0000-\u001f\u007f]/g, "").replace(/[\\/]/g, "-").trim();
  return (cleaned || "archivo").slice(0, 220);
}

async function sha256Hex(value: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", value);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

type PreparedFile = {
  file: File;
  buffer: ArrayBuffer;
  detectedMime: string;
  sha256: string;
};

Deno.serve(async (request) => {
  const origin = request.headers.get("origin") || "";
  if (request.method === "OPTIONS") {
    if (!allowedOrigin(origin)) return json(DEFAULT_ORIGINS[0], 403, { error: "Origen no permitido." });
    return new Response(null, { status: 204, headers: cors(origin) });
  }
  if (!allowedOrigin(origin)) return json(DEFAULT_ORIGINS[0], 403, { error: "Origen no permitido." });
  if (request.method !== "POST") return json(origin, 405, { error: "Método no permitido." });

  try {
    const contentType = request.headers.get("content-type") || "";
    if (!contentType.toLowerCase().startsWith("multipart/form-data")) {
      throw new IntakeError(415, "Se esperaba multipart/form-data.");
    }

    const lengthHeader = request.headers.get("content-length") || "";
    let accountedRequestBytes = MAX_REQUEST_BYTES;
    if (lengthHeader) {
      const declaredLength = Number(lengthHeader);
      if (!/^\d+$/.test(lengthHeader) || !Number.isSafeInteger(declaredLength) || declaredLength <= 0) {
        throw new IntakeError(400, "El tamaño declarado del envío no es válido.");
      }
      if (declaredLength > MAX_REQUEST_BYTES) throw new IntakeError(413, "El envío supera 15 MB.");
      accountedRequestBytes = declaredLength;
    }

    const url = Deno.env.get("SUPABASE_URL");
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!url || !serviceKey) throw new Error("Supabase server env incompleto");
    const admin = createClient(url, serviceKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });

    const authorization = request.headers.get("authorization") || "";
    const token = authorization.replace(/^Bearer\s+/i, "");
    if (!token || token === authorization) throw new IntakeError(401, "Inicia sesión para adjuntar archivos.");
    const { data: userData, error: userError } = await admin.auth.getUser(token);
    if (userError || !userData.user) throw new IntakeError(401, "La sesión ya no es válida.");

    const { data: rateAllowed, error: rateError } = await admin.rpc("fr_register_media_intake", {
      p_user_id: userData.user.id,
      // Browsers normally send Content-Length. If a proxy strips it, charge the
      // maximum request size so compatibility never weakens the abuse budget.
      p_bytes: accountedRequestBytes,
    });
    if (rateError) throw rateError;
    if (!rateAllowed) throw new IntakeError(429, "Demasiados archivos seguidos. Prueba más tarde.");

    const form = await request.formData();
    if (textField(form, "website", 200)) throw new IntakeError(400, "No se pudo enviar.");

    const section = textField(form, "section", 120, true);
    const title = textField(form, "title", 140, true);
    const details = textField(form, "details", 1000);
    const author = textField(form, "author", 80);
    const contact = textField(form, "contact", 180);
    const languageRaw = textField(form, "language", 5) || "en";
    const language = languageRaw === "es" ? "es" : "en";
    const attributionRaw = textField(form, "attribution_mode", 20) || "anonymous";
    const attributionMode = attributionRaw === "account" ? "account" : "anonymous";
    const allowContact = boolField(form, "allow_contact");
    const aiTrainingConsent = boolField(form, "ai_training_consent");
    const receiptHash = textField(form, "receipt_hash", 64, true);
    if (!/^[0-9a-f]{64}$/.test(receiptHash)) throw new IntakeError(400, "El recibo no es válido.");
    if (title.length < 3) throw new IntakeError(400, "La sugerencia es demasiado corta.");
    if (contact && !allowContact) throw new IntakeError(400, "Falta permiso para contacto privado.");

    const allowedCategories = new Set([
      "auto", "bug", "idea", "accessibility", "performance", "safety", "content", "other",
    ]);
    const categoryRaw = textField(form, "category_requested", 30) || "auto";
    const categoryRequested = allowedCategories.has(categoryRaw) ? categoryRaw : "auto";

    const files = form.getAll("files").filter(
      (entry): entry is File => entry instanceof File && entry.size > 0,
    );
    if (!files.length) throw new IntakeError(400, "No se recibió ningún archivo.");
    if (files.length > MAX_FILES) throw new IntakeError(413, "Solo se permiten 3 archivos.");
    const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
    if (totalBytes > MAX_TOTAL_BYTES) throw new IntakeError(413, "Las imágenes superan 15 MB en total.");

    const declaredAllowed = /^image\/(png|jpeg|webp)$/;
    for (const file of files) {
      if (file.size > MAX_FILE_BYTES) throw new IntakeError(413, `${safeName(file.name)} supera 5 MB.`);
      if (!declaredAllowed.test((file.type || "").toLowerCase())) {
        throw new IntakeError(415, `${safeName(file.name)} no tiene un formato permitido.`);
      }
    }

    const prepared: PreparedFile[] = [];
    for (const file of files) {
      const buffer = await file.arrayBuffer();
      const detectedMime = detectMime(new Uint8Array(buffer.slice(0, 32)));
      if (!detectedMime || !MIME_EXT[detectedMime]) {
        throw new IntakeError(415, `${safeName(file.name)} no coincide con una imagen permitida.`);
      }
      prepared.push({ file, buffer, detectedMime, sha256: await sha256Hex(buffer) });
    }

    const { data: submission, error: submissionError } = await admin
      .from("fr_submissions")
      .insert({
        section,
        title,
        details: details || null,
        author: author || null,
        contact: contact || null,
        language,
        user_id: userData.user.id,
        attribution_mode: attributionMode,
        allow_contact: Boolean(contact) && allowContact,
        receipt_hash: receiptHash,
        category_requested: categoryRequested,
        ai_training_consent: aiTrainingConsent,
        attachment_count: prepared.length,
      })
      .select("id,category_final,classification_method")
      .single();
    if (submissionError || !submission) throw submissionError || new Error("No se creó la sugerencia");

    const uploadedPaths: string[] = [];
    try {
      for (const item of prepared) {
        const attachmentId = crypto.randomUUID();
        const objectPath = `${userData.user.id}/${submission.id}/${attachmentId}.${MIME_EXT[item.detectedMime]}`;
        const { data: duplicate } = await admin
          .from("fr_submission_attachments")
          .select("id")
          .eq("sha256", item.sha256)
          .eq("bytes", item.file.size)
          .limit(1)
          .maybeSingle();
        const { error: uploadError } = await admin.storage.from(BUCKET).upload(objectPath, item.buffer, {
          contentType: item.detectedMime,
          cacheControl: "3600",
          upsert: false,
        });
        if (uploadError) throw uploadError;
        uploadedPaths.push(objectPath);
        const { error: fileError } = await admin.from("fr_submission_attachments").insert({
          id: attachmentId,
          submission_id: submission.id,
          owner_user_id: userData.user.id,
          object_path: objectPath,
          original_name: safeName(item.file.name),
          declared_mime: (item.file.type || "").slice(0, 100),
          detected_mime: item.detectedMime,
          media_kind: "image",
          bytes: item.file.size,
          sha256: item.sha256,
          review_status: duplicate ? "duplicate" : "quarantined",
          duplicate_of: duplicate?.id || null,
        });
        if (fileError) throw fileError;
      }
    } catch (error) {
      if (uploadedPaths.length) await admin.storage.from(BUCKET).remove(uploadedPaths);
      await admin.from("fr_submissions").delete().eq("id", submission.id);
      throw error;
    }

    console.log(JSON.stringify({
      event: "fanrank_media_accepted",
      submission_id: submission.id,
      files: prepared.length,
      bytes: totalBytes,
    }));
    return json(origin, 202, {
      ok: true,
      submission_id: submission.id,
      category: submission.category_final,
      classification_method: submission.classification_method,
      attachments: prepared.length,
      status: "quarantined",
      public: false,
    });
  } catch (error) {
    if (error instanceof IntakeError) return json(origin, error.status, { error: error.message });
    console.error(JSON.stringify({
      event: "fanrank_media_error",
      message: error instanceof Error ? error.message : "unknown",
    }));
    return json(origin, 500, { error: "No se pudo guardar de forma segura. No se publicó nada." });
  }
});
