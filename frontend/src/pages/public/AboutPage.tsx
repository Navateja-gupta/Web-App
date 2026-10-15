import { Link } from "react-router-dom";

export default function AboutPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-5 text-stone-700">
      <h1 className="font-display text-3xl font-semibold text-maroon-800">About us</h1>
      <p>
        Planning a wedding usually means calling relatives for recommendations, searching online, and contacting photographers,
        decorators, caterers and DJs one by one. It takes time, and it is hard to compare prices and packages.
      </p>
      <p>
        Kamareddy Wedding Services brings local wedding vendors into one place. You can browse services, see real photos of past work,
        compare packages, and keep a shortlist of the vendors you like.
      </p>
      <h2 className="pt-2 text-xl font-semibold text-stone-900">How listings work</h2>
      <ul className="list-inside list-disc space-y-1">
        <li>Every vendor profile is reviewed by our team before it appears on the site.</li>
        <li>Prices and availability are published by the vendors themselves. If a vendor has not published a price, we show “Contact for pricing”.</li>
        <li>The “Verified” badge only appears after our team has checked the business in person or through documents.</li>
      </ul>
      <p>
        We are starting in Kamareddy, Telangana and will expand to nearby towns.{" "}
        <Link to="/vendor/register" className="text-maroon-700 underline">
          Are you a wedding vendor? List your business.
        </Link>
      </p>
    </article>
  );
}
