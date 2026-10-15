import SideNavLayout from "../../components/SideNavLayout";

const LINKS = [
  { to: "/dashboard", label: "Overview" },
  { to: "/plans", label: "Wedding plan & budget" },
  { to: "/shortlist", label: "Shortlist" },
  { to: "/enquiries", label: "Enquiries" },
  { to: "/quotations", label: "Compare quotations" },
  { to: "/bookings", label: "Bookings" },
  { to: "/account", label: "Account settings" },
];

export default function CustomerLayout() {
  return <SideNavLayout title="My wedding" links={LINKS} />;
}
