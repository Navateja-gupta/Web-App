import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="border-t border-maroon-100 bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-6 text-sm text-stone-600">
        <p>Kamareddy Wedding Services · Kamareddy, Telangana</p>
        <nav aria-label="Footer" className="flex flex-wrap gap-4">
          <Link to="/categories" className="hover:text-maroon-700">
            Services
          </Link>
          <Link to="/about" className="hover:text-maroon-700">
            About
          </Link>
          <Link to="/contact" className="hover:text-maroon-700">
            Contact
          </Link>
          <Link to="/vendor/register" className="hover:text-maroon-700">
            List your business
          </Link>
        </nav>
      </div>
    </footer>
  );
}
