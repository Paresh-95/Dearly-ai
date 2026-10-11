"use client";

import { Suspense } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { MemoryForm } from "@/features/memories/memory-form";
import type { MemoryFormOutput } from "@/features/memories/schemas";
import { get, patch } from "@/lib/api";
import type { Memory } from "@/lib/types";

function EditMemoryPageInner() {
  const { id } = useParams<{ id: string }>();
  const profileId = useSearchParams().get("profile");
  const router = useRouter();
  const qc = useQueryClient();

  const memory = useQuery({
    queryKey: ["memory", id],
    queryFn: () => get<Memory>(`/memories/${id}`),
  });

  if (memory.isPending) return <main className="p-8 text-muted-foreground">Loading…</main>;
  if (memory.isError || !memory.data) {
    return <main className="p-8 text-destructive">This memory could not be found.</main>;
  }
  const m = memory.data;

  async function save(values: MemoryFormOutput, status: "draft" | "awaiting_review" | undefined) {
    await patch<Memory>(`/memories/${id}`, { ...values, ...(status ? { status } : {}) });
    await qc.invalidateQueries({ queryKey: ["memory", id] });
    router.push(`/library?profile=${profileId ?? m.person_profile_id}`);
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="mb-2 text-2xl font-semibold">Edit memory</h1>
      {m.status === "approved" && (
        <p className="mb-4 rounded-md bg-muted/40 p-3 text-sm text-muted-foreground">
          This memory is currently approved. Saving a change will send it back for review before
          it is used to answer questions again.
        </p>
      )}
      <MemoryForm
        mode={m.status}
        defaultValues={{
          title: m.title,
          description: m.description,
          category: m.category ?? undefined,
          date_text: m.date_text ?? undefined,
          date_start: m.date_start ?? undefined,
          location: m.location ?? undefined,
          people: m.people.map((p) => ({ name: p.name, relationship: p.relationship ?? "" })),
        }}
        onSave={save}
      />
    </main>
  );
}

export default function EditMemoryPage() {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Loading…</main>}>
      <EditMemoryPageInner />
    </Suspense>
  );
}
