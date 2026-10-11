import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, tokenStore } from "./api";

const json = (status: number, body?: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), { status });

describe("api client", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    tokenStore.set(null);
  });
  afterEach(() => fetchMock.mockReset());

  it("maps the backend error envelope to ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      json(409, { error: { code: "conflict", message: "Already exists", details: null } }),
    );
    await expect(api("/x")).rejects.toMatchObject({ status: 409, code: "conflict", message: "Already exists" });
  });

  it("falls back for non-JSON errors", async () => {
    fetchMock.mockResolvedValueOnce(new Response("<html>", { status: 502 }));
    const err = (await api("/x").catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(502);
  });

  it("sends the bearer token", async () => {
    tokenStore.set("tok");
    fetchMock.mockResolvedValueOnce(json(200, { ok: true }));
    await api("/x");
    expect(new Headers(fetchMock.mock.calls[0][1].headers).get("Authorization")).toBe("Bearer tok");
  });

  it("refreshes once on 401 and retries", async () => {
    tokenStore.set("old");
    fetchMock
      .mockResolvedValueOnce(json(401, { error: { code: "unauthenticated", message: "x" } }))
      .mockResolvedValueOnce(json(200, { access_token: "new" }))
      .mockResolvedValueOnce(json(200, { ok: 1 }));
    await expect(api("/x")).resolves.toEqual({ ok: 1 });
    expect(tokenStore.get()).toBe("new");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("does not loop if refresh fails", async () => {
    tokenStore.set("old");
    fetchMock
      .mockResolvedValueOnce(json(401, { error: { code: "unauthenticated", message: "x" } }))
      .mockResolvedValueOnce(json(401, { error: { code: "unauthenticated", message: "x" } }));
    await expect(api("/x")).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(tokenStore.get()).toBeNull();
  });
});
