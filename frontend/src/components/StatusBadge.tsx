import type { ReactNode } from "react";

import { APPROVAL_LABEL } from "../lib/format";
import type { ApprovalStatus } from "../types";

const approvalStyles: Record<ApprovalStatus, string> = {
  pending: "bg-amber-100 text-amber-900",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  suspended: "bg-stone-200 text-stone-800",
};

export function ApprovalBadge({ status }: { status: ApprovalStatus }) {
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${approvalStyles[status]}`}>{APPROVAL_LABEL[status]}</span>;
}

export function Badge({ tone, children }: { tone: "green" | "grey" | "blue" | "amber"; children: ReactNode }) {
  const styles = {
    green: "bg-green-100 text-green-800",
    grey: "bg-stone-200 text-stone-700",
    blue: "bg-sky-100 text-sky-800",
    amber: "bg-amber-100 text-amber-900",
  }[tone];
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${styles}`}>{children}</span>;
}
