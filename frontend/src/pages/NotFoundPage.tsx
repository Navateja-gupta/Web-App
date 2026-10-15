import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="text-center">
      <h1 className="font-display text-3xl text-maroon-800">Page not found</h1>
      <p className="mt-2 text-stone-600">The page you are looking for does not exist.</p>
      <Link to="/" className="mt-6 inline-block rounded-lg bg-maroon-700 px-5 py-2 text-white hover:bg-maroon-800">
        Go to home page
      </Link>
    </section>
  );
}
