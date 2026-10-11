import Link from "next/link";
import type { ChatMessage } from "@/lib/types";

export function MessageBubble({ message, profileId }: { message: ChatMessage; profileId: string }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] space-y-2 rounded-2xl px-4 py-2.5 text-sm ${
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.cited_memories.length > 0 && (
          <div className="flex flex-wrap gap-1.5 border-t border-foreground/10 pt-2">
            <span className="text-xs text-muted-foreground">From:</span>
            {message.cited_memories.map((c) => (
              <Link
                key={c.memory_id}
                href={`/library?profile=${profileId}`}
                className="rounded-full bg-background/60 px-2 py-0.5 text-xs underline"
              >
                {c.title}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
