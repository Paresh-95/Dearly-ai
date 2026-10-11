import { Badge } from "@/components/ui/badge";
import type { JobState } from "@/lib/types";

const LABEL: Record<JobState, string> = {
  queued: "Queued",
  running: "Processing",
  succeeded: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

const VARIANT: Record<JobState, "secondary" | "default" | "outline" | "destructive"> = {
  queued: "secondary",
  running: "outline",
  succeeded: "default",
  failed: "destructive",
  cancelled: "secondary",
};

export function JobStatusBadge({ state }: { state: JobState }) {
  return <Badge variant={VARIANT[state]}>{LABEL[state]}</Badge>;
}
