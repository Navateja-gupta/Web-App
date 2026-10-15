import { Link, NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm ${isActive ? "bg-maroon-50 text-maroon-800" : "text-stone-700 hover:text-maroon-700"}`;

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <header className="border-b border-maroon-100 bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3">
        <Link to="/" className="font-display text-xl font-semibold text-maroon-700">
          Kamareddy Wedding Services
        </Link>

        <nav className="flex flex-wrap items-center gap-1" aria-label="Main">
          {user ? (
            <>
              {user.role === "admin" && (
                <NavLink to="/admin" className={linkClass}>
                  Admin
                </NavLink>
              )}
              {user.role === "vendor" && (
                <NavLink to="/vendor" className={linkClass}>
                  My business
                </NavLink>
              )}
              <NavLink to="/account" className={linkClass}>
                My account
              </NavLink>
              <button onClick={handleLogout} className="rounded-md px-3 py-2 text-sm text-stone-700 hover:text-maroon-700">
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={linkClass}>
                Log in
              </NavLink>
              <NavLink to="/register" className={linkClass}>
                Sign up
              </NavLink>
              <NavLink to="/vendor/register" className={linkClass}>
                List your business
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
