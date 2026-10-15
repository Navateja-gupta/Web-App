import { NavLink, Outlet } from "react-router-dom";

/** Sidebar layout shared by the customer and administrator workspaces. */
export default function SideNavLayout({ title, links }: { title: string; links: { to: string; label: string }[] }) {
  return (
    <div className="flex flex-col gap-6 md:flex-row">
      <nav aria-label={title} className="md:w-48 md:shrink-0">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">{title}</p>
        <ul className="flex flex-wrap gap-1 md:flex-col">
          {links.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                end
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
