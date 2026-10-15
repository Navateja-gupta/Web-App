import { Link, Route, Routes } from "react-router-dom";

import HomePage from "./pages/HomePage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-maroon-100 bg-white">
        <div className="mx-auto flex max-w-6xl items-center px-4 py-4">
          <Link to="/" className="font-display text-xl font-semibold text-maroon-700">
            Kamareddy Wedding Services
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>

      <footer className="border-t border-maroon-100 bg-white py-4 text-center text-sm text-stone-500">
        Kamareddy, Telangana
      </footer>
    </div>
  );
}
