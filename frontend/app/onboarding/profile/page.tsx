"use client";

import { useRouter } from "next/navigation";
import { post } from "@/lib/api";
import { ProfileForm } from "@/features/profiles/profile-form";
import type { Profile } from "@/lib/types";

export default function OnboardingProfilePage() {
  const router = useRouter();
  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="mb-2 text-2xl font-semibold">Tell us about her</h1>
      <p className="mb-6 text-muted-foreground">
        Only a name and relationship are required — add as much or as little else as feels
        right. You can always come back and add more later.
      </p>
      <ProfileForm
        submitLabel="Create profile"
        onSubmit={async (values) => {
          const profile = await post<Profile>("/profiles", values);
          router.push(`/dashboard?profile=${profile.id}`);
        }}
      />
    </main>
  );
}
