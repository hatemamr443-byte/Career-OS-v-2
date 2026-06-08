/**
 * App.js — Main router with protected routes + lazy loading
 */
import React, { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AuthProvider }      from "./context/AuthContext";
import { I18nProvider }      from "./context/I18nContext";
import { AnalyticsProvider } from "./context/AnalyticsContext";
import AuthCallback          from "./components/AuthCallback";
import ProtectedRoute        from "./components/ProtectedRoute";
import "./App.css";

// ── Public pages (eagerly loaded — small, no auth needed) ────────
import Landing  from "./pages/Landing";
import Login    from "./pages/Login";
import Pricing  from "./pages/Pricing";
import Terms    from "./pages/Terms";
import Privacy  from "./pages/Privacy";

// ── Authenticated pages (lazy loaded — reduces initial bundle) ───
const Dashboard          = lazy(() => import("./pages/Dashboard"));
const Jobs               = lazy(() => import("./pages/Jobs"));
const JobDetail          = lazy(() => import("./pages/JobDetail"));
const Emails             = lazy(() => import("./pages/Emails"));
const Insights           = lazy(() => import("./pages/Insights"));
const CareerMap          = lazy(() => import("./pages/CareerMap"));
const Profile            = lazy(() => import("./pages/Profile"));
const Billing            = lazy(() => import("./pages/Billing"));
const BillingReturn      = lazy(() => import("./pages/BillingReturn"));
const Bookmarks          = lazy(() => import("./pages/Bookmarks"));
const CVTailor           = lazy(() => import("./pages/CVTailor"));
const CVVersions         = lazy(() => import("./pages/CVVersions"));
const DecisionEngine     = lazy(() => import("./pages/DecisionEngine"));
const InterviewPrep      = lazy(() => import("./pages/InterviewPrep"));
const SalaryIntel        = lazy(() => import("./pages/SalaryIntel"));
const ApplicationTimeline = lazy(() => import("./pages/ApplicationTimeline"));
const Referral           = lazy(() => import("./pages/Referral"));
const MemoryDashboard    = lazy(() => import("./pages/MemoryDashboard"));
const Layout             = lazy(() => import("./components/Layout"));

// ── Loading spinner for lazy routes ──────────────────────────────
function PageLoader() {
  return (
    <div style={{
      display: "flex", alignItems: "center",
      justifyContent: "center", height: "100vh",
      background: "#0f172a",
    }}>
      <div style={{
        width: 40, height: 40,
        border: "3px solid #334155",
        borderTopColor: "#6366f1",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── Wrapper: lazy + auth guard ────────────────────────────────────
function Protected({ children }) {
  return (
    <ProtectedRoute>
      <Suspense fallback={<PageLoader />}>
        {children}
      </Suspense>
    </ProtectedRoute>
  );
}

function AppRouter() {
  const location = useLocation();

  // OAuth callback via URL hash
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      {/* ── Public routes ──────────────────────────────────────── */}
      <Route path="/"               element={<Landing />} />
      <Route path="/login"          element={<Login />} />
      <Route path="/pricing"        element={<Pricing />} />
      <Route path="/terms"          element={<Terms />} />
      <Route path="/privacy"        element={<Privacy />} />
      <Route path="/billing/return" element={<BillingReturn />} />

      {/* ── Authenticated routes (lazy + protected) ────────────── */}
      <Route element={
        <Protected>
          <Suspense fallback={<PageLoader />}>
            <Layout />
          </Suspense>
        </Protected>
      }>
        <Route path="/dashboard"           element={<Protected><Dashboard /></Protected>} />
        <Route path="/jobs"                element={<Protected><Jobs /></Protected>} />
        <Route path="/jobs/:id"            element={<Protected><JobDetail /></Protected>} />
        <Route path="/emails"             element={<Protected><Emails /></Protected>} />
        <Route path="/insights"           element={<Protected><Insights /></Protected>} />
        <Route path="/career-map"         element={<Protected><CareerMap /></Protected>} />
        <Route path="/profile"            element={<Protected><Profile /></Protected>} />
        <Route path="/billing"            element={<Protected><Billing /></Protected>} />
        <Route path="/bookmarks"          element={<Protected><Bookmarks /></Protected>} />
        <Route path="/cv-tailor"          element={<Protected><CVTailor /></Protected>} />
        <Route path="/cv-tailor/:jobId"   element={<Protected><CVTailor /></Protected>} />
        <Route path="/cv-versions"        element={<Protected><CVVersions /></Protected>} />
        <Route path="/decision-engine"    element={<Protected><DecisionEngine /></Protected>} />
        <Route path="/interview-prep"     element={<Protected><InterviewPrep /></Protected>} />
        <Route path="/salary-intel"       element={<Protected><SalaryIntel /></Protected>} />
        <Route path="/applications"       element={<Protected><ApplicationTimeline /></Protected>} />
        <Route path="/referral"           element={<Protected><Referral /></Protected>} />
        <Route path="/memory"             element={<Protected><MemoryDashboard /></Protected>} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <I18nProvider>
          <AnalyticsProvider>
            <AppRouter />
          </AnalyticsProvider>
        </I18nProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
