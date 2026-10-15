import { useCallback, useEffect, useState } from "react";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import { Badge } from "../../components/StatusBadge";
import { api, getErrorMessage } from "../../lib/api";

interface EmailStatus {
  enabled: boolean;
  configured: boolean;
  from_address: string;
  smtp_host: string;
  counts: Record<"pending" | "sent" | "failed" | "skipped", number>;
  recent_failures: { to_email: string; subject: string; last_error: string | null; attempts: number; created_at: string }[];
}

export default function EmailStatusCard() {
  const [status, setStatus] = useState<EmailStatus | null>(null);
  const [result, setResult] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [sending, setSending] = useState(false);

  const load = useCallback(() => {
    api.get<EmailStatus>("/admin/email/status").then((r) => setStatus(r.data)).catch(() => undefined);
  }, []);

  useEffect(load, [load]);

  async function sendTest() {
    setSending(true);
    setResult(null);
    try {
      const r = (await api.post<{ status: string; to_email: string; error: string | null }>("/admin/email/test", undefined, { timeout: 45_000 })).data;
      setResult(
        r.status === "sent"
          ? { kind: "success", text: `Test email sent to ${r.to_email}. Check your inbox (and spam folder).` }
          : { kind: "error", text: `Sending failed: ${r.error ?? "unknown error"}` },
      );
    } catch (err) {
      setResult({ kind: "error", text: getErrorMessage(err) });
    } finally {
      setSending(false);
      load();
    }
  }

  if (!status) return null;

  return (
    <div className="space-y-3 rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-semibold">
          Email notifications{" "}
          {status.enabled && status.configured ? <Badge tone="green">On</Badge> : <Badge tone="grey">Off</Badge>}
        </h2>
        <Button variant="secondary" loading={sending} disabled={!status.enabled} onClick={sendTest}>
          Send test email to me
        </Button>
      </div>
      {!status.enabled ? (
        <p className="text-sm text-stone-600">
          Emails are turned off, so only in-app notifications are delivered. To turn them on, set <code>EMAIL_ENABLED=true</code> and your
          SMTP details in <code>backend\.env</code>, then restart the API.
        </p>
      ) : !status.configured ? (
        <Alert kind="error">EMAIL_ENABLED is on but SMTP_USERNAME / SMTP_PASSWORD are missing in backend\.env.</Alert>
      ) : (
        <p className="text-sm text-stone-600">
          Sending from <strong>{status.from_address}</strong> via {status.smtp_host}.
        </p>
      )}
      <p className="text-sm text-stone-600">
        Sent {status.counts.sent} · waiting {status.counts.pending} · failed {status.counts.failed} · not sent while off {status.counts.skipped}
      </p>
      {result && <Alert kind={result.kind}>{result.text}</Alert>}
      {status.recent_failures.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-red-700">Recent sending problems ({status.recent_failures.length})</summary>
          <ul className="mt-2 space-y-1 text-stone-600">
            {status.recent_failures.map((f, i) => (
              <li key={i}>
                {f.to_email} · “{f.subject}” · {f.attempts} attempt(s): {f.last_error}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
