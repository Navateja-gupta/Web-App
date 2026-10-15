import { AxiosError } from "axios";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import Spinner from "../../components/Spinner";
import { ApprovalBadge, Badge } from "../../components/StatusBadge";
import Tabs from "../../components/Tabs";
import VendorBookings from "../../features/vendor/VendorBookings";
import VendorEnquiries from "../../features/vendor/VendorEnquiries";
import VendorManageTabs from "../../features/vendor/VendorManageTabs";
import VendorProfileForm from "../../features/vendor/VendorProfileForm";
import { api, getErrorMessage } from "../../lib/api";
import type { VendorInput, VendorOwner } from "../../types";

const BASE = "/me/vendor";

function StatusBanner({ vendor }: { vendor: VendorOwner }) {
  if (!vendor.is_active) {
    return <Alert kind="error">Your listing has been deactivated by the administrator. Please contact support.</Alert>;
  }
  switch (vendor.approval_status) {
    case "pending":
      return <Alert kind="info">Your profile is waiting for administrator review. It will appear to customers once approved.</Alert>;
    case "approved":
      return <Alert kind="success">Your profile is live and visible to customers.</Alert>;
    case "rejected":
      return (
        <Alert kind="error">
          Your profile was not approved{vendor.status_reason ? `: ${vendor.status_reason}` : "."} Update your profile and save to send it for review again.
        </Alert>
      );
    case "suspended":
      return (
        <Alert kind="error">
          Your listing is suspended{vendor.status_reason ? `: ${vendor.status_reason}` : "."} Please contact the administrator.
        </Alert>
      );
  }
}

function ClaimForm({ onClaimed }: { onClaimed: (v: VendorOwner) => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      onClaimed((await api.post<VendorOwner>(`${BASE}/claim`, { code: code.trim() })).data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && <Alert kind="error">{error}</Alert>}
      <FormField label="Claim code" placeholder="ABCDE-FGHJK" value={code} onChange={(e) => setCode(e.target.value)} maxLength={20} />
      <Button type="submit" loading={saving} disabled={code.trim().length < 4}>
        Link my business
      </Button>
    </form>
  );
}

type Section = "enquiries" | "bookings" | "profile";
const SECTIONS = [
  { id: "enquiries" as const, label: "Enquiries" },
  { id: "bookings" as const, label: "Bookings" },
  { id: "profile" as const, label: "Business profile" },
];

export default function VendorDashboardPage() {
  // The section lives in the URL (?tab=bookings) so notification links open the right tab.
  const [params, setParams] = useSearchParams();
  const requested = params.get("tab");
  const section: Section = SECTIONS.some((s) => s.id === requested) ? (requested as Section) : "enquiries";
  const setSection = (id: Section) => setParams({ tab: id }, { replace: true });
  const [vendor, setVendor] = useState<VendorOwner | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "none" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setVendor((await api.get<VendorOwner>(BASE)).data);
      setState("ready");
    } catch (err) {
      if (err instanceof AxiosError && err.response?.status === 404) {
        setState("none");
      } else {
        setError(getErrorMessage(err));
        setState("error");
      }
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (state === "loading") return <Spinner />;
  if (state === "error") return <Alert kind="error">{error}</Alert>;

  if (state === "none" || !vendor) {
    return (
      <section className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="font-display text-3xl font-semibold text-maroon-800">Set up your business</h1>
          <p className="mt-1 text-stone-600">Create your business profile. An administrator reviews every new profile before it is shown to customers.</p>
        </div>
        <div className="rounded-xl border border-maroon-100 bg-white p-6 shadow-sm">
          <VendorProfileForm
            submitLabel="Create business profile"
            onSubmit={async (input: VendorInput) => {
              setVendor((await api.post<VendorOwner>(BASE, input)).data);
              setState("ready");
            }}
          />
        </div>
        <div className="rounded-xl border border-maroon-100 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Already listed by the administrator?</h2>
          <p className="mb-4 mt-1 text-sm text-stone-600">Enter the one-time claim code they gave you to link that profile to this account.</p>
          <ClaimForm
            onClaimed={(v) => {
              setVendor(v);
              setState("ready");
            }}
          />
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl font-semibold text-maroon-800">{vendor.business_name}</h1>
        <ApprovalBadge status={vendor.approval_status} />
        {vendor.is_verified && <Badge tone="blue">Verified</Badge>}
        <span className="text-sm text-stone-500">{vendor.category.name}</span>
      </div>
      <StatusBanner vendor={vendor} />
      <Tabs tabs={SECTIONS} active={section} onChange={setSection} />
      {section === "enquiries" && <VendorEnquiries />}
      {section === "bookings" && <VendorBookings />}
      {section === "profile" && (
        <VendorManageTabs
          vendor={vendor}
          basePath={BASE}
          onSaveProfile={async (input) => {
            setVendor((await api.patch<VendorOwner>(BASE, input)).data);
          }}
        />
      )}
    </section>
  );
}
