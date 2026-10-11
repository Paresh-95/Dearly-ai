import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import WelcomePage from "./page";

describe("WelcomePage", () => {
  it("states clearly that the AI is not the real person", () => {
    render(<WelcomePage />);
    expect(screen.getByText(/not/, { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get started" })).toHaveAttribute("href", "/register");
  });
});
