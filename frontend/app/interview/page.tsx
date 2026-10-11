"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, post } from "@/lib/api";
import type {
  InterviewCompleteResponse,
  InterviewStartResponse,
  InterviewTurn,
} from "@/lib/types";

type Turn = { role: "assistant" | "user"; content: string };

function InterviewPageInner() {
  const profileId = useSearchParams().get("profile");
  const [interviewId, setInterviewId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [done, setDone] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<InterviewCompleteResponse["candidates"] | null>(
    null,
  );

  async function startInterview() {
    if (!profileId) return;
    setError(null);
    setBusy(true);
    try {
      const res = await post<InterviewStartResponse>("/interviews", {
        person_profile_id: profileId,
      });
      setInterviewId(res.conversation_id);
      setTurns([{ role: "assistant", content: res.message.content }]);
      setDone(res.message.done);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start the interview.");
    } finally {
      setBusy(false);
    }
  }

  async function sendAnswer() {
    if (!input.trim() || !interviewId) return;
    const text = input.trim();
    setInput("");
    setTurns((t) => [...t, { role: "user", content: text }]);
    setBusy(true);
    setError(null);
    try {
      const res = await post<InterviewTurn>(`/interviews/${interviewId}/messages`, {
        content: text,
      });
      setTurns((t) => [...t, { role: "assistant", content: res.content }]);
      setDone(res.done);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not send that answer.");
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    if (!interviewId) return;
    setBusy(true);
    setError(null);
    try {
      const res = await post<InterviewCompleteResponse>(`/interviews/${interviewId}/complete`);
      setCandidates(res.candidates);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not finish the interview.");
    } finally {
      setBusy(false);
    }
  }

  if (!profileId) {
    return (
      <main className="p-8 text-muted-foreground">
        Choose a family member profile from the dashboard first.
      </main>
    );
  }

  if (candidates) {
    return (
      <main className="mx-auto max-w-2xl space-y-4 px-6 py-10">
        <h1 className="text-2xl font-semibold">Thank you</h1>
        <p className="text-muted-foreground">
          {candidates.length === 0
            ? "Nothing came out of this conversation that seemed worth proposing as a memory — that's alright, nothing is lost."
            : `${candidates.length} memor${candidates.length === 1 ? "y" : "ies"} ready for your review. Nothing is added to the library until you approve it.`}
        </p>
        <div className="flex gap-3">
          <Button render={<Link href={`/review?profile=${profileId}`} />}>Review now</Button>
          <Button variant="outline" render={<Link href={`/dashboard?profile=${profileId}`} />}>
            Back to dashboard
          </Button>
        </div>
      </main>
    );
  }

  if (!interviewId) {
    return (
      <main className="mx-auto max-w-2xl space-y-4 px-6 py-10">
        <h1 className="text-2xl font-semibold">Memory interview</h1>
        <p className="text-muted-foreground">
          I&apos;ll ask a few gentle questions, one at a time. Answer as much or as little as
          you like, and say &quot;skip&quot; or &quot;stop&quot; any time you want to finish —
          nothing is saved to the library until you&apos;ve reviewed and approved it afterwards.
        </p>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Button onClick={startInterview} disabled={busy}>
          {busy ? "Starting…" : "Start the interview"}
        </Button>
      </main>
    );
  }

  return (
    <main className="mx-auto flex h-screen max-w-2xl flex-col px-6 py-6">
      <div className="mb-4">
        <h1 className="text-2xl font-semibold">Memory interview</h1>
        <p className="text-sm text-muted-foreground">
          Say &quot;skip&quot; or &quot;stop&quot; any time, or use the button below to finish
          whenever you&apos;re ready.
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-lg border p-4">
        {turns.map((t, i) => (
          <div key={i} className={`flex ${t.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                t.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
              }`}
            >
              {t.content}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {!done && (
        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            sendAnswer();
          }}
        >
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={1}
            className="resize-none"
            placeholder="Your answer…"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendAnswer();
              }
            }}
          />
          <Button type="submit" disabled={busy || !input.trim()}>
            Send
          </Button>
        </form>
      )}

      <div className="mt-4">
        <Button variant="outline" onClick={finish} disabled={busy}>
          {done ? "Review the memories from this conversation" : "Finish now and review"}
        </Button>
      </div>
    </main>
  );
}

export default function InterviewPage() {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Loading…</main>}>
      <InterviewPageInner />
    </Suspense>
  );
}
