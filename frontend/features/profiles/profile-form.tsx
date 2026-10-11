"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { profileSchema, type ProfileFormOutput, type ProfileFormValues } from "./schemas";

function Field({
  id,
  label,
  error,
  hint,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && !error && <p className="text-xs text-muted-foreground">{hint}</p>}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function ProfileForm({
  defaultValues,
  onSubmit,
  submitLabel = "Save",
}: {
  defaultValues?: Partial<ProfileFormValues>;
  onSubmit: (values: ProfileFormOutput) => Promise<void>;
  submitLabel?: string;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const f = useForm<ProfileFormValues, unknown, ProfileFormOutput>({
    resolver: zodResolver(profileSchema),
    defaultValues,
  });
  const errors = f.formState.errors;

  return (
    <form
      className="space-y-5"
      noValidate
      onSubmit={f.handleSubmit(async (v) => {
        setFormError(null);
        try {
          await onSubmit(v);
        } catch (e) {
          setFormError(e instanceof ApiError ? e.message : "Could not save. Please try again.");
        }
      })}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="name" label="Name" error={errors.name?.message}>
          <Input id="name" {...f.register("name")} />
        </Field>
        <Field id="relationship" label="Relationship to you" error={errors.relationship?.message}>
          <Input id="relationship" placeholder="e.g. mother" {...f.register("relationship")} />
        </Field>
        <Field id="preferred_name" label="Preferred name or nickname (optional)">
          <Input id="preferred_name" placeholder="e.g. Aai" {...f.register("preferred_name")} />
        </Field>
        <Field
          id="languages"
          label="Languages spoken (optional)"
          hint="Separate with commas"
        >
          <Input id="languages" placeholder="Marathi, English" {...f.register("languages")} />
        </Field>
        <Field id="birth_date" label="Birth date (optional)">
          <Input id="birth_date" type="date" {...f.register("birth_date")} />
        </Field>
        <Field
          id="death_date"
          label="Date of passing (optional)"
          error={errors.death_date?.message}
        >
          <Input id="death_date" type="date" {...f.register("death_date")} />
        </Field>
      </div>

      <Field id="biography" label="A little about her life (optional)">
        <Textarea id="biography" rows={3} {...f.register("biography")} />
      </Field>
      <Field id="personality" label="Her personality (optional)">
        <Textarea id="personality" rows={3} {...f.register("personality")} />
      </Field>
      <Field
        id="favourite_expressions"
        label="Favourite sayings or expressions (optional)"
        hint="Separate with commas"
      >
        <Input id="favourite_expressions" {...f.register("favourite_expressions")} />
      </Field>
      <Field id="hobbies" label="Hobbies and interests (optional)" hint="Separate with commas">
        <Input id="hobbies" {...f.register("hobbies")} />
      </Field>

      {formError && (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      )}
      <Button type="submit" disabled={f.formState.isSubmitting}>
        {f.formState.isSubmitting ? "Saving…" : submitLabel}
      </Button>
    </form>
  );
}
