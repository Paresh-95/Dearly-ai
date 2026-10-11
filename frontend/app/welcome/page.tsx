import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function WelcomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">A quiet place to keep her memories</h1>
      <p className="text-lg text-muted-foreground">
        Memory Companion helps you gather the stories, sayings and details of someone you love,
        and lets you ask questions answered only from what you have shared.
      </p>
      <section
        aria-labelledby="not-real"
        className="rounded-lg border bg-muted/40 p-4 text-sm leading-relaxed"
      >
        <h2 id="not-real" className="mb-1 font-medium">
          Please know
        </h2>
        <p>
          This is an AI built from the memories you provide. It is <strong>not</strong> your loved
          one, and it will say so when it does not know something rather than guess. You stay in
          control: you can review, correct or delete anything at any time.
        </p>
      </section>
      <div className="flex gap-3">
        <Link href="/register" className={buttonVariants()}>
          Get started
        </Link>
        <Link href="/login" className={buttonVariants({ variant: "outline" })}>
          Sign in
        </Link>
      </div>
    </main>
  );
}
