import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  const auth = request.headers.get("Authorization") ?? "";
  const res = await fetch(`${BACKEND_URL}/conversations/${params.id}`, {
    headers: { Authorization: auth },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  const auth = request.headers.get("Authorization") ?? "";
  const res = await fetch(`${BACKEND_URL}/conversations/${params.id}`, {
    method: "DELETE",
    headers: { Authorization: auth },
  });
  if (res.status === 204) return new NextResponse(null, { status: 204 });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
