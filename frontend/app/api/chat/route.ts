import { NextRequest } from "next/server";

// Note: maxDuration is a Vercel-only setting (ignored on Railway/self-hosted).
// Timeout resilience on Railway is handled via SSE heartbeat pings from the backend.
export const maxDuration = 800;

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const auth = request.headers.get("Authorization");
  if (auth) headers["Authorization"] = auth;

  const backendRes = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  // Pass SSE stream straight through to the browser
  return new Response(backendRes.body, {
    status: backendRes.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
