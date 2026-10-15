import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { AuthProvider } from "./auth/AuthContext";
import "./index.css";
import { ShortlistProvider } from "./shortlist/ShortlistContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ShortlistProvider>
          <App />
        </ShortlistProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
