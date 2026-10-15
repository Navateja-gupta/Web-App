import SideNavLayout from "../../components/SideNavLayout";

const LINKS = [
  { to: "/admin/overview", label: "Overview" },
  { to: "/admin/vendors", label: "Vendors" },
  { to: "/admin/vendors/new", label: "Add vendor" },
  { to: "/admin/categories", label: "Categories" },
  { to: "/admin/users", label: "Users" },
  { to: "/admin/enquiries", label: "Enquiries" },
  { to: "/admin/bookings", label: "Bookings" },
  { to: "/admin/reviews", label: "Reviews" },
  { to: "/admin/reports", label: "Complaints" },
  { to: "/admin/audit-logs", label: "Audit log" },
];

export default function AdminLayout() {
  return <SideNavLayout title="Administration" links={LINKS} />;
}
