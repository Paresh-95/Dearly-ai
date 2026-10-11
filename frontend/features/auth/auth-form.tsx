"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  loginSchema,
  registerSchema,
  type LoginValues,
  type RegisterValues,
} from "./schemas";

function Field({
  id,
  label,
  error,
  ...props
}: React.ComponentProps<typeof Input> & { id: string; label: string; error?: string }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined} {...props} />
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

function message(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return "Something went wrong. Please try again.";
}

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const f = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Welcome back</CardTitle>
        <CardDescription>Sign in to your private memory space.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-4"
          noValidate
          onSubmit={f.handleSubmit(async (v) => {
            setFormError(null);
            try {
              await login(v.email, v.password);
              router.push("/dashboard");
            } catch (e) {
              setFormError(message(e));
            }
          })}
        >
          <Field id="email" label="Email" type="email" autoComplete="email" error={f.formState.errors.email?.message} {...f.register("email")} />
          <Field id="password" label="Password" type="password" autoComplete="current-password" error={f.formState.errors.password?.message} {...f.register("password")} />
          {formError && <p role="alert" className="text-sm text-destructive">{formError}</p>}
          <Button type="submit" className="w-full" disabled={f.formState.isSubmitting}>
            {f.formState.isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            New here? <Link className="underline" href="/register">Create an account</Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}

export function RegisterForm() {
  const { register: signUp } = useAuth();
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const f = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });
  const errors = f.formState.errors;

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>Your memories stay private to you.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-4"
          noValidate
          onSubmit={f.handleSubmit(async (v) => {
            setFormError(null);
            try {
              await signUp(v.email, v.password, v.displayName);
              router.push("/dashboard");
            } catch (e) {
              setFormError(message(e));
            }
          })}
        >
          <Field id="displayName" label="Your name (optional)" autoComplete="name" error={errors.displayName?.message} {...f.register("displayName")} />
          <Field id="email" label="Email" type="email" autoComplete="email" error={errors.email?.message} {...f.register("email")} />
          <Field id="password" label="Password" type="password" autoComplete="new-password" error={errors.password?.message} {...f.register("password")} />
          <Field id="confirm" label="Confirm password" type="password" autoComplete="new-password" error={errors.confirm?.message} {...f.register("confirm")} />
          <div className="space-y-1.5">
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-1" {...f.register("acknowledged")} />
              <span>I understand this app creates an AI based on shared memories. It is not my loved one.</span>
            </label>
            {errors.acknowledged && <p className="text-sm text-destructive">{errors.acknowledged.message}</p>}
          </div>
          {formError && <p role="alert" className="text-sm text-destructive">{formError}</p>}
          <Button type="submit" className="w-full" disabled={f.formState.isSubmitting}>
            {f.formState.isSubmitting ? "Creating account…" : "Create account"}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Already have an account? <Link className="underline" href="/login">Sign in</Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
