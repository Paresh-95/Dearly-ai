"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusBadge } from "@/features/memories/status-badge";
import { ApiError, del, get } from "@/lib/api";
import { MEMORY_CATEGORIES, type Memory, type MemoryList, type MemoryStatus } from "@/lib/types";

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "awaiting_review", label: "Awaiting review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

function DeleteButton({ memory, onDeleted }: { memory: Memory; onDeleted: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!confirming) {
    return (
      <Button variant="outline" onClick={() => setConfirming(true)}>
        Delete
      </Button>
    );
  }
  return (
    <span className="flex items-center gap-2 text-sm">
      Delete this memory?
      <Button
        variant="destructive"
        onClick={async () => {
          try {
            await del(`/memories/${memory.id}`);
            onDeleted();
          } catch (e) {
            setError(e instanceof ApiError ? e.message : "Could not delete this memory.");
          }
        }}
      >
        Yes, delete
      </Button>
      <Button variant="outline" onClick={() => setConfirming(false)}>
        Cancel
      </Button>
      {error && <span className="text-destructive">{error}</span>}
    </span>
  );
}

function LibraryPageInner() {
  const profileId = useSearchParams().get("profile");
  const qc = useQueryClient();
  const [status, setStatus] = useState<string>("all");
  const [category, setCategory] = useState<string>("all");
  const [q, setQ] = useState("");

  const queryKey = ["memories", "library", profileId, status, category, q];
  const query = useQuery({
    queryKey,
    queryFn: () =>
      get<MemoryList>("/memories", {
        person_profile_id: profileId ?? undefined,
        status: status === "all" ? undefined : status,
        category: category === "all" ? undefined : category,
        q: q || undefined,
        limit: 50,
      }),
    enabled: !!profileId,
  });

  if (!profileId) {
    return (
      <main className="p-8 text-muted-foreground">
        Choose a family member profile from the dashboard first.
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl space-y-4 px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Memory library</h1>
        <Button render={<Link href={`/memories/new?profile=${profileId}`} />}>
          Write a memory
        </Button>
      </div>

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Search title and description…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <Select value={status} onValueChange={(v) => setStatus(v ?? "all")}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_FILTERS.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={category} onValueChange={(v) => setCategory(v ?? "all")}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {MEMORY_CATEGORIES.map((c) => (
              <SelectItem key={c} value={c}>
                {c.replaceAll("_", " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {query.isPending && <p className="text-muted-foreground">Loading…</p>}
      {query.data?.items.length === 0 && (
        <p className="text-muted-foreground">No memories match these filters yet.</p>
      )}
      {query.data?.items.map((m) => (
        <Card key={m.id}>
          <CardHeader className="flex-row items-start justify-between">
            <div>
              <CardTitle>{m.title}</CardTitle>
              <p className="text-sm text-muted-foreground">
                {[m.category?.replaceAll("_", " "), m.date_text, m.location]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
            <StatusBadge status={m.status as MemoryStatus} />
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="whitespace-pre-wrap text-sm">{m.description}</p>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                render={<Link href={`/memories/${m.id}/edit?profile=${profileId}`} />}
              >
                Edit
              </Button>
              <DeleteButton memory={m} onDeleted={() => qc.invalidateQueries({ queryKey })} />
            </div>
          </CardContent>
        </Card>
      ))}
    </main>
  );
}

export default function LibraryPage() {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Loading…</main>}>
      <LibraryPageInner />
    </Suspense>
  );
}
