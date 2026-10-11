"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { ApiError, post } from "@/lib/api";
import { CONSENT_POLICY_VERSION } from "@/lib/types";
import { consentSchema, type ConsentValues } from "./schemas";

export function ConsentForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const f = useForm<ConsentValues>({ resolver: zodResolver(consentSchema) });

  return (
    <form
      className="space-y-5"
      noValidate
      onSubmit={f.handleSubmit(async () => {
        setFormError(null);
        try {
          await post("/consents", {
            consent_type: "data_processing",
            granted: true,
            policy_version: CONSENT_POLICY_VERSION,
          });
          router.push("/onboarding/profile");
        } catch (e) {
          setFormError(e instanceof ApiError ? e.message : "Something went wrong.");
        }
      })}
    >
      <div className="space-y-3 text-sm leading-relaxed text-muted-foreground">
        <p>
          Anything you write, upload or record here is stored privately and used only to answer
          your own questions about the person you are preserving memories of.
        </p>
        <p>
          You can review, correct, export or delete any memory at any time from Settings.
          Nothing is shared outside your account. If this ever changes — for example, to use an
          outside AI provider for a new feature — you will be asked again before it happens.
        </p>
        <p>
          Voice recreation is not part of this app yet. If it is ever offered, it will need its
          own separate permission; simply having recordings of someone&apos;s voice does not grant
          that permission on its own.
        </p>
      </div>
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" className="mt-1" {...f.register("acknowledged")} />
        <span>I understand how my shared memories will be processed and stored.</span>
      </label>
      {f.formState.errors.acknowledged && (
        <p role="alert" className="text-sm text-destructive">
          {f.formState.errors.acknowledged.message}
        </p>
      )}
      {formError && (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      )}
      <Button type="submit" disabled={f.formState.isSubmitting}>
        {f.formState.isSubmitting ? "Saving…" : "Continue"}
      </Button>
    </form>
  );
}
