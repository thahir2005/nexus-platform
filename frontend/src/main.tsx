import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ClerkProvider, SignIn, useAuth } from "@clerk/react";
import "./index.css";
import App from "./App";
import { setTokenProvider } from "./services/api";

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function AuthenticatedApp() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  useEffect(() => {
    setTokenProvider(() => getToken());
  }, [getToken]);

  if (!isLoaded) return <div className="loading">Loading secure NEXUS session…</div>;
  if (!isSignedIn) {
    return <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24 }}>
      <SignIn routing="hash" />
    </div>;
  }
  return <App />;
}

function MissingClerkConfiguration() {
  return <main style={{ padding: 32, fontFamily: "system-ui" }}>
    <h1>NEXUS authentication is not configured</h1>
    <p>Set VITE_CLERK_PUBLISHABLE_KEY in frontend/.env.local, then restart the frontend.</p>
  </main>;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {publishableKey ? (
      <ClerkProvider publishableKey={publishableKey}>
        <BrowserRouter><AuthenticatedApp /></BrowserRouter>
      </ClerkProvider>
    ) : <MissingClerkConfiguration />}
  </StrictMode>,
);
