"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge } from "@/features/memories/status-badge";
import { ApiError, get, post } from "@/lib/api";
import type { Memory, MemoryList } from "@/lib/types";

function ReviewCard({ memory, profileId }: { memory: Memory; profileId: string }) {
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [noteOpen, setNoteOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => qc.invalidateQueries({ queryKey: ["memories", "review", profileId] });

  async function approve() {
    setError(null);
    try {
      await post(`/memories/${memory.id}/approve`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not approve this memory.");
    }
  }

  async function reject() {
    setError(null);
    try {
      await post(`/memories/${memory.id}/reject`, { note: note || undefined });
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reject this memory.");
    }
  }

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <CardTitle>{memory.title}</CardTitle>
          <p className="text-sm text-muted-foreground">
            {[memory.date_text, memory.location].filter(Boolean).join(" · ") || "No date or location given"}
          </p>
        </div>
        <StatusBadge status={memory.status} />
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="whitespace-pre-wrap text-sm">{memory.description}</p>
        {memory.people.length > 0 && (
          <p className="text-sm text-muted-foreground">
            With: {memory.people.map((p) => p.name).join(", ")}
          </p>
        )}
        {memory.origin === "extracted" && (
          <p className="text-sm text-muted-foreground">
            Suggested from an uploaded file — not yet confirmed as accurate.
          </p>
        )}
        {memory.is_uncertain && (
          <p className="rounded-md bg-muted/40 p-2 text-sm">
            ⚠ {memory.uncertainty_note || "This detail is uncertain and worth double-checking."}
          </p>
        )}
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={approve}>Approve</Button>
          <Button variant="outline" onClick={() => setNoteOpen((v) => !v)}>
            Reject
          </Button>
          <Button
            variant="outline"
            render={<Link href={`/memories/${memory.id}/edit?profile=${profileId}`} />}
          >
            Edit
          </Button>
        </div>
        {noteOpen && (
          <div className="space-y-2 rounded-md border p-3">
            <Textarea
              placeholder="Why is this being rejected? (optional)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
            />
            <Button variant="outline" onClick={reject}>
              Confirm rejection
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ReviewPageInner() {
  const profileId = useSearchParams().get("profile");
  const query = useQuery({
    queryKey: ["memories", "review", profileId],
    queryFn: () =>
      get<MemoryList>("/memories", {
        person_profile_id: profileId ?? undefined,
        status: "awaiting_review",
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
    <main className="mx-auto max-w-2xl space-y-4 px-6 py-10">
      <h1 className="text-2xl font-semibold">Review memories</h1>
      <p className="text-muted-foreground">
        These memories are waiting for your approval before they can be used to answer
        questions.
      </p>
      {query.isPending && <p className="text-muted-foreground">Loading…</p>}
      {query.data?.items.length === 0 && (
        <p className="text-muted-foreground">Nothing is waiting for review right now.</p>
      )}
      {query.data?.items.map((m) => (
        <ReviewCard key={m.id} memory={m} profileId={profileId} />
      ))}
    </main>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Loading…</main>}>
      <ReviewPageInner />
    </Suspense>
  );
}
