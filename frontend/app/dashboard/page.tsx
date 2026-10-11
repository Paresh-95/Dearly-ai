"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { get } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { MemoryList, MemoryStatus, Profile } from "@/lib/types";

const STATUS_LABEL: Record<MemoryStatus, string> = {
  draft: "Drafts",
  awaiting_review: "Awaiting review",
  approved: "Approved",
  rejected: "Rejected",
};

function DashboardPageInner() {
  const { status, user, logout } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  const profiles = useQuery({
    queryKey: ["profiles"],
    queryFn: () => get<{ items: Profile[] }>("/profiles"),
    enabled: status === "authenticated",
  });

  const profileId = searchParams.get("profile") ?? profiles.data?.items[0]?.id ?? null;
  const selectedProfile = profiles.data?.items.find((p) => p.id === profileId) ?? null;

  const memories = useQuery({
    queryKey: ["memories", "dashboard", profileId],
    queryFn: () => get<MemoryList>("/memories", { person_profile_id: profileId!, limit: 200 }),
    enabled: !!profileId,
  });

  const counts = useMemo(() => {
    const base: Record<MemoryStatus, number> = {
      draft: 0,
      awaiting_review: 0,
      approved: 0,
      rejected: 0,
    };
    for (const m of memories.data?.items ?? []) base[m.status]++;
    return base;
  }, [memories.data]);

  const recent = useMemo(
    () => [...(memories.data?.items ?? [])].slice(-5).reverse(),
    [memories.data],
  );

  if (status !== "authenticated") {
    return <main className="p-8 text-muted-foreground">Loading…</main>;
  }

  return (
    <main className="mx-auto max-w-3xl space-y-6 px-6 py-10">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">
          Hello{user?.display_name ? `, ${user.display_name}` : ""}
        </h1>
        <Button variant="outline" onClick={() => logout().then(() => router.replace("/welcome"))}>
          Sign out
        </Button>
      </header>

      {profiles.isPending && <p className="text-muted-foreground">Loading…</p>}

      {profiles.data?.items.length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Create your first profile</CardTitle>
            <CardDescription>
              Start by telling us a little about the person you want to remember.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button render={<Link href="/onboarding/profile" />}>Create a profile</Button>
          </CardContent>
        </Card>
      )}

      {profiles.data && profiles.data.items.length > 0 && selectedProfile && (
        <>
          {profiles.data.items.length > 1 && (
            <Select
              value={profileId ?? undefined}
              onValueChange={(v) => router.push(`/dashboard?profile=${v}`)}
            >
              <SelectTrigger className="w-64">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {profiles.data.items.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.preferred_name || p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Card>
            <CardHeader>
              <CardTitle>{selectedProfile.preferred_name || selectedProfile.name}</CardTitle>
              <CardDescription>{selectedProfile.relationship}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {Object.entries(counts).map(([key, count]) => (
                  <div key={key} className="rounded-md border p-3 text-center">
                    <p className="text-2xl font-semibold">{count}</p>
                    <p className="text-xs text-muted-foreground">
                      {STATUS_LABEL[key as MemoryStatus]}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-3">
            <Button render={<Link href={`/ask?profile=${profileId}`} />}>Ask AI</Button>
            <Button
              variant="outline"
              render={<Link href={`/memories/new?profile=${profileId}`} />}
            >
              Write a memory
            </Button>
            <Button
              variant="outline"
              render={<Link href={`/review?profile=${profileId}`} />}
            >
              Review{counts.awaiting_review > 0 ? ` (${counts.awaiting_review})` : ""}
            </Button>
            <Button variant="outline" render={<Link href={`/library?profile=${profileId}`} />}>
              Memory library
            </Button>
            <Button variant="outline" render={<Link href={`/uploads?profile=${profileId}`} />}>
              Upload files
            </Button>
          </div>

          {recent.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Recently added</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {recent.map((m) => (
                  <Link
                    key={m.id}
                    href={`/memories/${m.id}/edit?profile=${profileId}`}
                    className="block rounded-md p-2 hover:bg-muted/50"
                  >
                    <span className="font-medium">{m.title}</span>{" "}
                    <span className="text-sm text-muted-foreground">({m.status})</span>
                  </Link>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </main>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Loading…</main>}>
      <DashboardPageInner />
    </Suspense>
  );
}
