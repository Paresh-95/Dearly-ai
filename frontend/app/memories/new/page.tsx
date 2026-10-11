"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MemoryForm } from "@/features/memories/memory-form";
import type { MemoryFormOutput } from "@/features/memories/schemas";
import { post } from "@/lib/api";
import type { Memory } from "@/lib/types";

function NewMemoryPageInner() {
  const router = useRouter();
  const profileId = useSearchParams().get("profile");

  if (!profileId) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-muted-foreground">
          Choose a family member profile from the dashboard first.
        </p>
      </main>
    );
  }

  async function save(values: MemoryFormOutput, status: "draft" | "awaiting_review" | undefined) {
    await post<Memory>("/memories", {
      ...values,
      person_profile_id: profileId,
      status: status ?? "draft",
    });
    router.push(`/library?profile=${profileId}`);
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="mb-2 text-2xl font-semibold">Write a memory</h1>
      <p className="mb-6 text-muted-foreground">
        Write it the way it happened, in your own words — you can always come back and edit it.
      </p>
      <MemoryForm onSave={save} />
    </main>
  );
}

export default function NewMemoryPage() {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Loading…</main>}>
      <NewMemoryPageInner />
    </Suspense>
  );
}
