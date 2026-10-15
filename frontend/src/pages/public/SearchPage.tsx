import VendorBrowser from "../../features/marketplace/VendorBrowser";

export default function SearchPage() {
  return (
    <section className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-maroon-800">Find wedding vendors</h1>
        <p className="text-stone-600">Search across all services and filter by location, price and date.</p>
      </div>
      <VendorBrowser />
    </section>
  );
}
