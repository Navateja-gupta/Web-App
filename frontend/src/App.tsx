import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import ProtectedRoute from "./auth/ProtectedRoute";
import Footer from "./components/Footer";
import Header from "./components/Header";
import AccountPage from "./pages/AccountPage";
import AdminCategoriesPage from "./pages/admin/AdminCategoriesPage";
import AdminLayout from "./pages/admin/AdminLayout";
import AdminUsersPage from "./pages/admin/AdminUsersPage";
import AdminVendorDetailPage from "./pages/admin/AdminVendorDetailPage";
import AdminVendorNewPage from "./pages/admin/AdminVendorNewPage";
import AdminVendorsPage from "./pages/admin/AdminVendorsPage";
import ShortlistPage from "./pages/customer/ShortlistPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import AboutPage from "./pages/public/AboutPage";
import CategoriesPage from "./pages/public/CategoriesPage";
import CategoryPage from "./pages/public/CategoryPage";
import ContactPage from "./pages/public/ContactPage";
import SearchPage from "./pages/public/SearchPage";
import VendorProfilePage from "./pages/public/VendorProfilePage";
import RegisterPage from "./pages/RegisterPage";
import VendorDashboardPage from "./pages/vendor/VendorDashboardPage";

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => window.scrollTo(0, 0), [pathname]);
  return null;
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <ScrollToTop />
      <Header />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:py-10">
        <Routes>
          {/* Public marketplace */}
          <Route path="/" element={<HomePage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/categories/:slug" element={<CategoryPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/vendors/:slug" element={<VendorProfilePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />

          {/* Accounts */}
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

          {/* Customer */}
          <Route
            path="/shortlist"
            element={
              <ProtectedRoute roles={["customer"]}>
                <ShortlistPage />
              </ProtectedRoute>
            }
          />

          {/* Vendor */}
          <Route
            path="/vendor"
            element={
              <ProtectedRoute roles={["vendor"]}>
                <VendorDashboardPage />
              </ProtectedRoute>
            }
          />

          {/* Administrator */}
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

      <Footer />
    </div>
  );
}
