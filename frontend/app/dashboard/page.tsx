"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Profile } from "@/lib/types";

export default function DashboardPage() {
  const { status, user, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  const profiles = useQuery({
    queryKey: ["profiles"],
    queryFn: () => api<{ items: Profile[] }>("/profiles"),
    enabled: status === "authenticated",
  });

  if (status !== "authenticated") return <main className="p-8 text-muted-foreground">Loading…</main>;

  return (
    <main className="mx-auto max-w-3xl space-y-6 px-6 py-10">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Hello{user?.display_name ? `, ${user.display_name}` : ""}</h1>
        <Button variant="outline" onClick={() => logout().then(() => router.replace("/welcome"))}>
          Sign out
        </Button>
      </header>
      <Card>
        <CardHeader>
          <CardTitle>Family member profiles</CardTitle>
          <CardDescription>Profile creation and memories arrive in the next milestone.</CardDescription>
        </CardHeader>
        <CardContent>
          {profiles.isPending && <p className="text-muted-foreground">Loading…</p>}
          {profiles.isError && <p role="alert" className="text-destructive">Could not load profiles.</p>}
          {profiles.data && (
            <p data-testid="profile-count">
              {profiles.data.items.length === 0
                ? "No profiles yet."
                : `${profiles.data.items.length} profile(s): ${profiles.data.items.map((p) => p.name).join(", ")}`}
            </p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
