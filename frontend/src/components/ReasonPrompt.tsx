import { useState } from "react";

import Button from "./Button";
import TextArea from "./TextArea";

/** Inline "give a reason" form used for cancellations, rejections and declines. */
export default function ReasonPrompt({
  label,
  confirmLabel,
  required = true,
  onConfirm,
  onCancel,
}: {
  label: string;
  confirmLabel: string;
  required?: boolean;
  onConfirm: (reason: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <div className="space-y-2 rounded-lg border border-stone-200 bg-stone-50 p-3">
      <TextArea label={label} rows={2} maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} />
      <div className="flex gap-2">
        <Button
          variant="danger"
          loading={busy}
          disabled={required && reason.trim().length < 3}
          onClick={async () => {
            setBusy(true);
            try {
              await onConfirm(reason.trim());
            } finally {
              setBusy(false);
            }
          }}
        >
          {confirmLabel}
        </Button>
        <Button variant="secondary" onClick={onCancel}>
          Back
        </Button>
      </div>
    </div>
  );
}
