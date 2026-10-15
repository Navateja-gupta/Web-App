import { useState } from "react";

import Tabs from "../../components/Tabs";
import type { VendorInput, VendorPublic } from "../../types";
import AvailabilityManager from "./AvailabilityManager";
import PackagesManager from "./PackagesManager";
import PortfolioManager from "./PortfolioManager";
import VendorProfileForm from "./VendorProfileForm";

type TabId = "profile" | "packages" | "photos" | "availability";

const TABS = [
  { id: "profile" as const, label: "Profile" },
  { id: "packages" as const, label: "Packages & pricing" },
  { id: "photos" as const, label: "Photos" },
  { id: "availability" as const, label: "Availability" },
];

/** Shared by the vendor dashboard and the admin vendor editor. */
export default function VendorManageTabs({
  vendor,
  basePath,
  onSaveProfile,
}: {
  vendor: VendorPublic;
  basePath: string;
  onSaveProfile: (input: VendorInput) => Promise<void>;
}) {
  const [tab, setTab] = useState<TabId>("profile");

  return (
    <div className="space-y-6">
      <Tabs tabs={TABS} active={tab} onChange={setTab} />
      <div className="rounded-xl border border-maroon-100 bg-white p-6 shadow-sm">
        {tab === "profile" && (
          <VendorProfileForm key={vendor.id} initial={vendor} submitLabel="Save profile" successMessage="Profile saved." onSubmit={onSaveProfile} />
        )}
        {tab === "packages" && <PackagesManager basePath={basePath} />}
        {tab === "photos" && <PortfolioManager basePath={basePath} />}
        {tab === "availability" && <AvailabilityManager basePath={basePath} />}
      </div>
    </div>
  );
}
