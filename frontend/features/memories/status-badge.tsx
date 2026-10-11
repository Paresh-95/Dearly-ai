import { Badge } from "@/components/ui/badge";
import type { MemoryStatus } from "@/lib/types";

const LABEL: Record<MemoryStatus, string> = {
  draft: "Draft",
  awaiting_review: "Awaiting review",
  approved: "Approved",
  rejected: "Rejected",
};

const VARIANT: Record<MemoryStatus, "secondary" | "default" | "outline" | "destructive"> = {
  draft: "secondary",
  awaiting_review: "outline",
  approved: "default",
  rejected: "destructive",
};

export function StatusBadge({ status }: { status: MemoryStatus }) {
  return <Badge variant={VARIANT[status]}>{LABEL[status]}</Badge>;
}
