import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ChatMessage } from "@/lib/types";
import { MessageBubble } from "./message-bubble";

const base: ChatMessage = {
  id: "1",
  role: "assistant",
  content: "She always made poha on Sundays.",
  cited_memories: [],
  created_at: "2026-01-01T00:00:00Z",
};

describe("MessageBubble", () => {
  it("renders the message content", () => {
    render(<MessageBubble message={base} profileId="p1" />);
    expect(screen.getByText(/poha on Sundays/)).toBeInTheDocument();
  });

  it("shows cited memories as links to the library, and nothing when there are none", () => {
    const { rerender } = render(<MessageBubble message={base} profileId="p1" />);
    expect(screen.queryByText("From:")).not.toBeInTheDocument();

    rerender(
      <MessageBubble
        message={{
          ...base,
          cited_memories: [
            { memory_id: "m1", title: "Sunday breakfast", category: "daily_life", provenance: "family_recollection" },
          ],
        }}
        profileId="p1"
      />,
    );
    const link = screen.getByRole("link", { name: "Sunday breakfast" });
    expect(link).toHaveAttribute("href", "/library?profile=p1");
  });
});
