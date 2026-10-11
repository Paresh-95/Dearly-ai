"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api";
import { MEMORY_CATEGORIES, type MemoryStatus } from "@/lib/types";
import { memoryFormSchema, type MemoryFormOutput, type MemoryFormValues } from "./schemas";

type TargetStatus = "draft" | "awaiting_review" | undefined;

interface Action {
  label: string;
  /** Status to send in the PATCH/POST body. `undefined` omits the field, leaving the backend
   * to decide (e.g. editing an approved memory auto-reverts it to awaiting_review). */
  status: TargetStatus;
  variant?: "outline";
}

/** Which save actions make sense from the memory's current status — mirrors the backend's
 * allowed transitions in `app/domain/memory_rules.py` so we never offer a button that would
 * just come back as a 409. */
function actionsFor(mode: "create" | MemoryStatus): Action[] {
  switch (mode) {
    case "create":
    case "draft":
      return [
        { label: "Save as draft", status: "draft", variant: "outline" },
        { label: "Submit for review", status: "awaiting_review" },
      ];
    case "awaiting_review":
      return [
        { label: "Withdraw to draft", status: "draft", variant: "outline" },
        { label: "Save changes", status: undefined },
      ];
    case "approved":
      return [{ label: "Save changes (sends back for review)", status: undefined }];
    case "rejected":
      return [{ label: "Revise and save as draft", status: "draft" }];
  }
}

function Field({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function MemoryForm({
  mode = "create",
  defaultValues,
  onSave,
}: {
  /** The memory's current status, or "create" for a brand-new memory. Determines which save
   * actions are offered. */
  mode?: "create" | MemoryStatus;
  defaultValues?: Partial<MemoryFormValues>;
  /** Called with the validated values and the status to send (undefined = omit the field). */
  onSave: (values: MemoryFormOutput, status: TargetStatus) => Promise<void>;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const f = useForm<MemoryFormValues, unknown, MemoryFormOutput>({
    resolver: zodResolver(memoryFormSchema),
    defaultValues: { people: [], ...defaultValues },
  });
  const people = useFieldArray({ control: f.control, name: "people" });
  const errors = f.formState.errors;

  const save = (status: TargetStatus) =>
    f.handleSubmit(async (values) => {
      setFormError(null);
      try {
        await onSave(values, status);
      } catch (e) {
        setFormError(e instanceof ApiError ? e.message : "Could not save. Please try again.");
      }
    });

  return (
    <form className="space-y-5" noValidate>
      <Field id="title" label="Title" error={errors.title?.message}>
        <Input id="title" placeholder="e.g. Sunday breakfast" {...f.register("title")} />
      </Field>
      <Field id="description" label="What happened" error={errors.description?.message}>
        <Textarea
          id="description"
          rows={5}
          placeholder="Write it the way you remember it — her own words if you can recall them."
          {...f.register("description")}
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="category">Category (optional)</Label>
          <Select
            defaultValue={defaultValues?.category}
            onValueChange={(v) => f.setValue("category", v ?? undefined, { shouldDirty: true })}
          >
            <SelectTrigger id="category" className="w-full">
              <SelectValue placeholder="Choose a category" />
            </SelectTrigger>
            <SelectContent>
              {MEMORY_CATEGORIES.map((c) => (
                <SelectItem key={c} value={c}>
                  {c.replaceAll("_", " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Field id="location" label="Location (optional)">
          <Input id="location" {...f.register("location")} />
        </Field>
        <Field id="date_text" label="Approximate date (optional)">
          <Input id="date_text" placeholder="e.g. sometime in the 1990s" {...f.register("date_text")} />
        </Field>
        <Field id="date_start" label="Exact date, if known (optional)">
          <Input id="date_start" type="date" {...f.register("date_start")} />
        </Field>
      </div>

      <div className="space-y-2">
        <Label>People in this memory (optional)</Label>
        {people.fields.map((field, i) => (
          <div key={field.id} className="flex gap-2">
            <Input placeholder="Name" {...f.register(`people.${i}.name`)} />
            <Input placeholder="Relationship" {...f.register(`people.${i}.relationship`)} />
            <Button type="button" variant="outline" onClick={() => people.remove(i)}>
              Remove
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          onClick={() => people.append({ name: "", relationship: "" })}
        >
          Add a person
        </Button>
      </div>

      {formError && (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      )}
      <div className="flex gap-3">
        {actionsFor(mode).map((action) => (
          <Button
            key={action.label}
            type="button"
            variant={action.variant}
            disabled={f.formState.isSubmitting}
            onClick={save(action.status)}
          >
            {action.label}
          </Button>
        ))}
      </div>
    </form>
  );
}
