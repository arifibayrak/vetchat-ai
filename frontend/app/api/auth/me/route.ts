import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(request: NextRequest) {
  const auth = request.headers.get("Authorization") ?? "";
  const res = await fetch(`${BACKEND_URL}/auth/me`, {
    headers: { Authorization: auth },
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  return NextResponse.json(data, { status: res.status });
}
