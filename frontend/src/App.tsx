import { Route, Routes } from "react-router-dom";

import ProtectedRoute from "./auth/ProtectedRoute";
import Header from "./components/Header";
import AccountPage from "./pages/AccountPage";
import AdminUsersPage from "./pages/admin/AdminUsersPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import RegisterPage from "./pages/RegisterPage";

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
            path="/admin/users"
            element={
              <ProtectedRoute roles={["admin"]}>
                <AdminUsersPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>

      <footer className="border-t border-maroon-100 bg-white py-4 text-center text-sm text-stone-500">
        Kamareddy, Telangana
      </footer>
    </div>
  );
}
