import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/admin/vendors", label: "Vendors", end: true },
  { to: "/admin/vendors/new", label: "Add vendor", end: true },
  { to: "/admin/categories", label: "Categories", end: true },
  { to: "/admin/users", label: "Users", end: true },
];

export default function AdminLayout() {
  return (
    <div className="flex flex-col gap-6 md:flex-row">
      <nav aria-label="Admin" className="md:w-48 md:shrink-0">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">Administration</p>
        <ul className="flex flex-wrap gap-1 md:flex-col">
          {links.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `block rounded-md px-3 py-2 text-sm ${isActive ? "bg-maroon-700 text-white" : "text-stone-700 hover:bg-maroon-50"}`
                }
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}
