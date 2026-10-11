"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { JobStatusBadge } from "@/features/uploads/job-status-badge";
import { ApiError, get, postForm } from "@/lib/api";
import type { IngestionJob, IngestionJobList, Source, SourceList } from "@/lib/types";
import { UPLOAD_KINDS } from "@/lib/types";

function UploadForm({ profileId, onUploaded }: { profileId: string; onUploaded: () => void }) {
  const [kind, setKind] = useState<string>("text");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Please choose a file first.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const form = new FormData();
      form.set("person_profile_id", profileId);
      form.set("kind", kind);
      form.set("file", file);
      await postForm<IngestionJob>("/uploads", form);
      setFile(null);
      onUploaded();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not upload this file.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="kind">What kind of file is this?</Label>
          <Select value={kind} onValueChange={(v) => v && setKind(v)}>
            <SelectTrigger id="kind" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {UPLOAD_KINDS.map((k) => (
                <SelectItem key={k.value} value={k.value}>
                  {k.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="file">File</Label>
          <input
            id="file"
            type="file"
            className="block w-full text-sm"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Button type="submit" disabled={submitting}>
        {submitting ? "Uploading…" : "Upload"}
      </Button>
    </form>
  );
}

function UploadsPageInner() {
  const profileId = useSearchParams().get("profile");
  const qc = useQueryClient();

  const jobsQuery = useQuery({
    queryKey: ["ingestion-jobs", profileId],
    queryFn: () => get<IngestionJobList>("/ingestion-jobs", { person_profile_id: profileId! }),
    enabled: !!profileId,
    refetchInterval: (q) => {
      const items = q.state.data?.items ?? [];
      return items.some((j) => j.state === "queued" || j.state === "running") ? 3000 : false;
    },
  });

  const sourcesQuery = useQuery({
    queryKey: ["sources", profileId],
    queryFn: () => get<SourceList>("/sources", { person_profile_id: profileId! }),
    enabled: !!profileId,
  });

  if (!profileId) {
    return (
      <main className="p-8 text-muted-foreground">
        Choose a family member profile from the dashboard first.
      </main>
    );
  }

  const sourceById = new Map<string, Source>(
    (sourcesQuery.data?.items ?? []).map((s) => [s.id, s]),
  );
  const anySucceeded = jobsQuery.data?.items.some((j) => j.state === "succeeded");

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold">Upload centre</h1>
        <p className="text-muted-foreground">
          Upload documents, chat exports, photos, audio or video. We&apos;ll extract the text
          and, once that&apos;s configured, suggest memories for you to review — nothing is
          added to the library without your approval.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add a file</CardTitle>
        </CardHeader>
        <CardContent>
          <UploadForm
            profileId={profileId}
            onUploaded={() => {
              qc.invalidateQueries({ queryKey: ["ingestion-jobs", profileId] });
              qc.invalidateQueries({ queryKey: ["sources", profileId] });
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Uploads</CardTitle>
          <CardDescription>
            {anySucceeded && (
              <Link href={`/review?profile=${profileId}`} className="underline">
                Review extracted memories
              </Link>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {jobsQuery.data?.items.length === 0 && (
            <p className="text-muted-foreground">No uploads yet.</p>
          )}
          {jobsQuery.data?.items.map((job) => {
            const source = sourceById.get(job.source_id);
            return (
              <div key={job.id} className="flex items-start justify-between rounded-md border p-3">
                <div>
                  <p className="font-medium">{source?.filename ?? "File"}</p>
                  <p className="text-sm text-muted-foreground">
                    {source?.kind} · attempt {job.attempts}
                    {job.stage ? ` · ${job.stage.replaceAll("_", " ")}` : ""}
                  </p>
                  {job.error && <p className="mt-1 text-sm text-destructive">{job.error}</p>}
                </div>
                <JobStatusBadge state={job.state} />
              </div>
            );
          })}
        </CardContent>
      </Card>
    </main>
  );
}

export default function UploadsPage() {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Loading…</main>}>
      <UploadsPageInner />
    </Suspense>
  );
}
