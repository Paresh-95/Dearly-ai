import { ConsentForm } from "@/features/consent/consent-form";

export default function OnboardingConsentPage() {
  return (
    <main className="mx-auto max-w-xl px-6 py-12">
      <h1 className="mb-2 text-2xl font-semibold">Before we begin</h1>
      <p className="mb-6 text-muted-foreground">
        A quick, plain-language note on how your memories are handled.
      </p>
      <ConsentForm />
    </main>
  );
}
