import crypto from "node:crypto";

const json = (statusCode, body) => ({
  statusCode,
  headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  body: JSON.stringify(body)
});

function sameSecret(provided, expected) {
  const left = Buffer.from(String(provided || ""));
  const right = Buffer.from(String(expected || ""));
  return left.length === right.length && crypto.timingSafeEqual(left, right);
}

function validate(input) {
  if (!input || typeof input !== "object") throw new Error("Invalid control data");
  const labels = new Set(["negotiating", "real", "termed"]);
  if (!labels.has(input.war_label)) throw new Error("Invalid war status");
  const notes = String(input.notes || "").trim().slice(0, 300);
  if (!Array.isArray(input.events) || input.events.length > 30) throw new Error("Invalid event list");
  const events = input.events.map((event, index) => {
    const title = String(event?.title || "").trim().slice(0, 80);
    if (!title) throw new Error(`Event ${index + 1} needs a title`);
    const start = new Date(event.starts_at);
    const end = event.ends_at ? new Date(event.ends_at) : null;
    if (Number.isNaN(start.valueOf())) throw new Error(`Event ${index + 1} has an invalid start`);
    if (end && (Number.isNaN(end.valueOf()) || end < start)) throw new Error(`Event ${index + 1} has an invalid end`);
    return {
      title,
      starts_at: start.toISOString().replace(".000Z", "Z"),
      ends_at: end ? end.toISOString().replace(".000Z", "Z") : null,
      description: String(event.description || "").trim().slice(0, 300)
    };
  });
  events.sort((a, b) => a.starts_at.localeCompare(b.starts_at));
  return { war_label: input.war_label, notes, events };
}

export async function handler(event) {
  if (event.httpMethod !== "POST") return json(405, { error: "Method not allowed" });
  const expectedPassword = process.env.ADMIN_PASSWORD;
  const token = process.env.DA_GITHUB_TOKEN;
  const repository = process.env.DA_GITHUB_REPOSITORY;
  const branch = process.env.DA_GITHUB_BRANCH || "main";
  const path = process.env.LEADERSHIP_PATH || "announcement_automation/leadership.json";
  if (!expectedPassword || !token || !repository) return json(503, { error: "Server configuration is incomplete" });

  let request;
  try { request = JSON.parse(event.body || "{}"); }
  catch { return json(400, { error: "Invalid request" }); }
  if (!sameSecret(request.password, expectedPassword)) return json(401, { error: "Incorrect password" });

  const url = `https://api.github.com/repos/${repository}/contents/${path}?ref=${encodeURIComponent(branch)}`;
  const headers = {
    Accept: "application/vnd.github+json",
    Authorization: `Bearer ${token}`,
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "DA-announcement-controls"
  };
  try {
    const currentResponse = await fetch(url, { headers });
    if (!currentResponse.ok) throw new Error(`GitHub read failed (${currentResponse.status})`);
    const current = await currentResponse.json();
    const existing = validate(JSON.parse(Buffer.from(current.content, "base64").toString("utf8")));
    if (request.action === "read") return json(200, { data: existing });
    if (request.action !== "write") return json(400, { error: "Unknown action" });

    const updated = validate(request.data);
    const writeResponse = await fetch(url.replace(/\?ref=.*/, ""), {
      method: "PUT",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "Update faction announcement controls",
        content: Buffer.from(`${JSON.stringify(updated, null, 2)}\n`).toString("base64"),
        sha: current.sha,
        branch
      })
    });
    if (!writeResponse.ok) {
      const detail = await writeResponse.json().catch(() => ({}));
      throw new Error(detail.message || `GitHub write failed (${writeResponse.status})`);
    }
    return json(200, { data: updated });
  } catch (error) {
    return json(502, { error: error.message || "Control storage failed" });
  }
}
