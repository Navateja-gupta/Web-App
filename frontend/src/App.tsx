import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./auth/ProtectedRoute";
import Header from "./components/Header";
import AccountPage from "./pages/AccountPage";
import AdminCategoriesPage from "./pages/admin/AdminCategoriesPage";
import AdminLayout from "./pages/admin/AdminLayout";
import AdminUsersPage from "./pages/admin/AdminUsersPage";
import AdminVendorDetailPage from "./pages/admin/AdminVendorDetailPage";
import AdminVendorNewPage from "./pages/admin/AdminVendorNewPage";
import AdminVendorsPage from "./pages/admin/AdminVendorsPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import RegisterPage from "./pages/RegisterPage";
import VendorDashboardPage from "./pages/vendor/VendorDashboardPage";

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage role="customer" />} />
          <Route path="/vendor/register" element={<RegisterPage role="vendor" />} />
          <Route
            path="/account"
            element={
              <ProtectedRoute>
                <AccountPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/vendor"
            element={
              <ProtectedRoute roles={["vendor"]}>
                <VendorDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={["admin"]}>
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="vendors" replace />} />
            <Route path="vendors" element={<AdminVendorsPage />} />
            <Route path="vendors/new" element={<AdminVendorNewPage />} />
            <Route path="vendors/:id" element={<AdminVendorDetailPage />} />
            <Route path="categories" element={<AdminCategoriesPage />} />
            <Route path="users" element={<AdminUsersPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>

      <footer className="border-t border-maroon-100 bg-white py-4 text-center text-sm text-stone-500">
        Kamareddy, Telangana
      </footer>
    </div>
  );
}
