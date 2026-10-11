"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MessageBubble } from "@/features/chat/message-bubble";
import { ApiError, get, post } from "@/lib/api";
import type { ChatMessage, ChatMessageList, Conversation, ConversationList } from "@/lib/types";

function AskPageInner() {
  const profileId = useSearchParams().get("profile");
  const qc = useQueryClient();
  // undefined = "use the most recent existing conversation"; null = "start a new one";
  // a string = an explicit selection (e.g. one just created by sending the first message).
  const [explicitConversationId, setExplicitConversationId] = useState<string | null | undefined>(
    undefined,
  );
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const conversationsQuery = useQuery({
    queryKey: ["conversations", profileId],
    queryFn: () => get<ConversationList>("/conversations", { person_profile_id: profileId! }),
    enabled: !!profileId,
  });

  const conversationId =
    explicitConversationId !== undefined
      ? explicitConversationId
      : conversationsQuery.data?.items[0]?.id ?? null;

  const messagesQuery = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => get<ChatMessageList>(`/conversations/${conversationId}/messages`),
    enabled: !!conversationId,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messagesQuery.data]);

  async function send() {
    if (!input.trim() || !profileId) return;
    setError(null);
    setSending(true);
    const question = input.trim();
    setInput("");
    try {
      let cid = conversationId;
      if (!cid) {
        const created = await post<Conversation>("/conversations", {
          person_profile_id: profileId,
        });
        cid = created.id;
        setExplicitConversationId(cid);
        qc.invalidateQueries({ queryKey: ["conversations", profileId] });
      }
      await post<ChatMessage>(`/conversations/${cid}/messages`, { content: question });
      await qc.invalidateQueries({ queryKey: ["messages", cid] });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not send that. Please try again.");
      setInput(question);
    } finally {
      setSending(false);
    }
  }

  if (!profileId) {
    return (
      <main className="p-8 text-muted-foreground">
        Choose a family member profile from the dashboard first.
      </main>
    );
  }

  return (
    <main className="mx-auto flex h-screen max-w-2xl flex-col px-6 py-6">
      <div className="mb-4 space-y-2">
        <h1 className="text-2xl font-semibold">Ask AI</h1>
        <p className="text-sm text-muted-foreground">
          Answers come only from the memories you&apos;ve approved. This isn&apos;t her — it&apos;s
          an assistant reading what you&apos;ve shared, and it will say so when it doesn&apos;t
          know something.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setExplicitConversationId(null);
            setError(null);
          }}
        >
          Start a new conversation
        </Button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-lg border p-4">
        {conversationId && messagesQuery.data?.items.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">
            Ask a question to get started.
          </p>
        )}
        {!conversationId && (
          <p className="text-center text-sm text-muted-foreground">
            Ask a question below to begin a new conversation.
          </p>
        )}
        {messagesQuery.data?.items.map((m) => (
          <MessageBubble key={m.id} message={m} profileId={profileId} />
        ))}
        {sending && <p className="text-sm text-muted-foreground">Thinking…</p>}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}

      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a memory, a date, a saying…"
          rows={1}
          className="resize-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <Button type="submit" disabled={sending || !input.trim()}>
          Send
        </Button>
      </form>
    </main>
  );
}

export default function AskPage() {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Loading…</main>}>
      <AskPageInner />
    </Suspense>
  );
}
