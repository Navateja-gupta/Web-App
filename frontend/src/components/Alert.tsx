import type { ReactNode } from "react";

const styles = {
  error: "border-red-200 bg-red-50 text-red-800",
  success: "border-green-200 bg-green-50 text-green-800",
  info: "border-amber-200 bg-amber-50 text-amber-900",
};

export default function Alert({ kind, children }: { kind: keyof typeof styles; children: ReactNode }) {
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`rounded-lg border px-4 py-3 text-sm ${styles[kind]}`}>
      {children}
    </div>
  );
}
