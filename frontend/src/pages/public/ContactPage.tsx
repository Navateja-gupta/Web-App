import { Link } from "react-router-dom";

import { SUPPORT_EMAIL, SUPPORT_PHONE } from "../../lib/config";

export default function ContactPage() {
  const hasContact = Boolean(SUPPORT_EMAIL || SUPPORT_PHONE);
  return (
    <article className="mx-auto max-w-2xl space-y-5 text-stone-700">
      <h1 className="font-display text-3xl font-semibold text-maroon-800">Contact us</h1>
      <p>Questions about a vendor, your listing, or the platform? We are happy to help.</p>
      {hasContact ? (
        <ul className="space-y-2 rounded-xl border border-maroon-100 bg-white p-6 shadow-sm">
          {SUPPORT_PHONE && (
            <li>
              Phone:{" "}
              <a href={`tel:${SUPPORT_PHONE}`} className="text-maroon-700 underline">
                {SUPPORT_PHONE}
              </a>
            </li>
          )}
          {SUPPORT_EMAIL && (
            <li>
              Email:{" "}
              <a href={`mailto:${SUPPORT_EMAIL}`} className="text-maroon-700 underline">
                {SUPPORT_EMAIL}
              </a>
            </li>
          )}
        </ul>
      ) : (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-6 text-stone-600">Contact details will be published here soon.</p>
      )}
      <p>
        Wedding vendors can{" "}
        <Link to="/vendor/register" className="text-maroon-700 underline">
          register their business
        </Link>{" "}
        directly. Every profile is reviewed before it is published.
      </p>
    </article>
  );
}
