import { useNavigate } from "react-router-dom";

import Alert from "../../components/Alert";
import VendorProfileForm from "../../features/vendor/VendorProfileForm";
import { api } from "../../lib/api";
import type { VendorAdmin } from "../../types";

export default function AdminVendorNewPage() {
  const navigate = useNavigate();

  return (
    <section className="max-w-3xl space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Add vendor</h1>
        <p className="text-stone-600">Create a profile on behalf of a business that has agreed to be listed.</p>
      </div>
      <Alert kind="info">
        The new profile starts as <strong>pending</strong>. After saving you can add packages and photos, then approve it to publish.
      </Alert>
      <div className="rounded-xl border border-maroon-100 bg-white p-6 shadow-sm">
        <VendorProfileForm
          submitLabel="Save vendor"
          onSubmit={async (input) => {
            const created = (await api.post<VendorAdmin>("/admin/vendors", input)).data;
            navigate(`/admin/vendors/${created.id}`, { state: { justCreated: true } });
          }}
        />
      </div>
    </section>
  );
}
