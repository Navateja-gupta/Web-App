import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import Spinner from "../../components/Spinner";
import { ApprovalBadge, Badge } from "../../components/StatusBadge";
import TextArea from "../../components/TextArea";
import VendorManageTabs from "../../features/vendor/VendorManageTabs";
import { api, getErrorMessage } from "../../lib/api";
import { formatDate } from "../../lib/format";
import type { VendorAdmin } from "../../types";

type ReasonAction = "reject" | "suspend";

function ActionsPanel({ vendor, onChange }: { vendor: VendorAdmin; onChange: (v: VendorAdmin) => void }) {
  const [reasonFor, setReasonFor] = useState<ReasonAction | null>(null);
  const [reason, setReason] = useState("");
  const [verifyNotes, setVerifyNotes] = useState(vendor.verification_notes ?? "");
  const [claim, setClaim] = useState<{ code: string; expires_at: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const base = `/admin/vendors/${vendor.id}`;
  const s = vendor.approval_status;

  async function call(path: string, body: unknown, success: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      onChange((await api.request<VendorAdmin>({ url: `${base}${path}`, method: path ? "post" : "patch", data: body })).data);
      setNotice(success);
      setReasonFor(null);
      setReason("");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function issueClaimCode() {
    setBusy(true);
    setError(null);
    try {
      setClaim((await api.post<{ code: string; expires_at: string }>(`${base}/claim-code`)).data);
      onChange((await api.get<VendorAdmin>(base)).data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="space-y-4 rounded-xl border border-maroon-100 bg-white p-5 shadow-sm">
      <h2 className="font-semibold">Actions</h2>
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      <div className="flex flex-wrap gap-2">
        {s !== "approved" && (
          <Button loading={busy} onClick={() => call("/approve", undefined, "Vendor approved and now visible to customers.")}>
            {s === "suspended" ? "Reinstate" : "Approve"}
          </Button>
        )}
        {s === "pending" && (
          <Button variant="danger" disabled={busy} onClick={() => setReasonFor("reject")}>
            Reject
          </Button>
        )}
        {s === "approved" && (
          <Button variant="danger" disabled={busy} onClick={() => setReasonFor("suspend")}>
            Suspend
          </Button>
        )}
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() =>
            call("", { is_active: !vendor.is_active }, vendor.is_active ? "Listing deactivated." : "Listing activated.")
          }
        >
          {vendor.is_active ? "Deactivate" : "Activate"}
        </Button>
      </div>

      {reasonFor && (
        <div className="space-y-2">
          <TextArea
            label={reasonFor === "reject" ? "Reason for rejection" : "Reason for suspension"}
            hint="Shown to the vendor so they know what to fix."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            maxLength={1000}
          />
          <div className="flex gap-2">
            <Button
              variant="danger"
              loading={busy}
              disabled={reason.trim().length < 3}
              onClick={() => call(`/${reasonFor}`, { reason: reason.trim() }, reasonFor === "reject" ? "Vendor rejected." : "Vendor suspended.")}
            >
              Confirm {reasonFor}
            </Button>
            <Button variant="secondary" onClick={() => setReasonFor(null)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      <div className="space-y-2 border-t border-stone-100 pt-4">
        <h3 className="text-sm font-semibold">Verification</h3>
        <p className="text-xs text-stone-500">Mark as verified only after you have actually checked the business (met them, saw documents).</p>
        <TextArea label="Internal notes" value={verifyNotes} onChange={(e) => setVerifyNotes(e.target.value)} rows={2} maxLength={2000} />
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() =>
            call(
              "/verification",
              { is_verified: !vendor.is_verified, notes: verifyNotes },
              vendor.is_verified ? "Verification removed." : "Marked as verified.",
            )
          }
        >
          {vendor.is_verified ? "Remove verification" : "Mark as verified"}
        </Button>
      </div>

      <div className="space-y-2 border-t border-stone-100 pt-4">
        <h3 className="text-sm font-semibold">Vendor account</h3>
        {vendor.user ? (
          <p className="text-sm text-stone-700">
            Linked to {vendor.user.full_name} ({vendor.user.email})
          </p>
        ) : (
          <>
            <p className="text-sm text-stone-600">
              Not linked to a vendor account. Generate a one-time code and give it to the owner in person or by phone. They enter it after
              signing up as a vendor.
            </p>
            {claim ? (
              <Alert kind="success">
                Claim code: <strong className="font-mono text-base">{claim.code}</strong>
                <br />
                Valid until {formatDate(claim.expires_at)}. It is shown only once.
              </Alert>
            ) : (
              vendor.has_pending_claim_code && <p className="text-xs text-stone-500">A code was issued earlier. Generating a new one replaces it.</p>
            )}
            <Button variant="secondary" disabled={busy} onClick={issueClaimCode}>
              Generate claim code
            </Button>
          </>
        )}
      </div>
    </aside>
  );
}

export default function AdminVendorDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const justCreated = (location.state as { justCreated?: boolean } | null)?.justCreated;
  const [vendor, setVendor] = useState<VendorAdmin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const basePath = `/admin/vendors/${id}`;

  const load = useCallback(async () => {
    try {
      setVendor((await api.get<VendorAdmin>(basePath)).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [basePath]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) return <Alert kind="error">{error}</Alert>;
  if (!vendor) return <Spinner />;

  return (
    <section className="space-y-5">
      <Link to="/admin/vendors" className="text-sm text-maroon-700 underline">
        ← All vendors
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl font-semibold text-maroon-800">{vendor.business_name}</h1>
        <ApprovalBadge status={vendor.approval_status} />
        {!vendor.is_active && <Badge tone="grey">Inactive</Badge>}
        {vendor.is_verified && <Badge tone="blue">Verified</Badge>}
      </div>
      <p className="text-sm text-stone-600">
        {vendor.category.name} · {vendor.location} · added {formatDate(vendor.created_at)}
        {vendor.approved_at && ` · approved ${formatDate(vendor.approved_at)}`}
      </p>
      {justCreated && <Alert kind="success">Vendor saved as pending. Add packages and photos, then approve to publish.</Alert>}
      {vendor.status_reason && (vendor.approval_status === "rejected" || vendor.approval_status === "suspended") && (
        <Alert kind="error">Reason given: {vendor.status_reason}</Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <VendorManageTabs
          vendor={vendor}
          basePath={basePath}
          onSaveProfile={async (input) => {
            setVendor((await api.patch<VendorAdmin>(basePath, input)).data);
          }}
        />
        <ActionsPanel vendor={vendor} onChange={setVendor} />
      </div>
    </section>
  );
}
