import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AuthProvider }      from "./context/AuthContext";
import { I18nProvider }      from "./context/I18nContext";
import { AnalyticsProvider } from "./context/AnalyticsContext";
import AuthCallback          from "./components/AuthCallback";
import Landing               from "./pages/Landing";
import Pricing               from "./pages/Pricing";
import Login                 from "./pages/Login";
import MemoryDashboard from './pages/MemoryDashboard';
import Dashboard             from "./pages/Dashboard";
import Jobs                  from "./pages/Jobs";
import JobDetail             from "./pages/JobDetail";
import Emails                from "./pages/Emails";
import Insights              from "./pages/Insights";
import CareerMap             from "./pages/CareerMap";
import Profile               from "./pages/Profile";
import Billing               from "./pages/Billing";
import BillingReturn         from "./pages/BillingReturn";
import Bookmarks             from "./pages/Bookmarks";
import CVTailor              from "./pages/CVTailor";
import Privacy               from "./pages/Privacy";
import DecisionEngine        from "./pages/DecisionEngine";
import CVVersions            from "./pages/CVVersions";
import InterviewPrep         from "./pages/InterviewPrep";
import SalaryIntel           from "./pages/SalaryIntel";
import ApplicationTimeline   from "./pages/ApplicationTimeline";
import Referral              from "./pages/Referral";
import Terms                 from "./pages/Terms";
import Layout                from "./components/Layout";
import CookieConsent         from "./components/CookieConsent";
import "./App.css";

function AppRouter() {
    const location = useLocation();
    if (location.hash?.includes("session_id=")) {
        return <AuthCallback />;
    }
    return (
        <Routes>
            <Route path="/"               element={<Landing />} />
            <Route path="/login"          element={<Login />} />
            <Route path="/pricing"        element={<Pricing />} />
            <Route path="/billing/return" element={<BillingReturn />} />
            <Route path="/terms"          element={<Terms />} />
            <Route element={<Layout />}>
                <Route path="/dashboard"          element={<Dashboard />} />
                <Route path="/jobs"               element={<Jobs />} />
                <Route path="/jobs/:id"           element={<JobDetail />} />
                <Route path="/emails"             element={<Emails />} />
                <Route path="/insights"           element={<Insights />} />
                <Route path="/memory" element={<MemoryDashboard />} />
          <Route path="/career-map"         element={<CareerMap />} />
                <Route path="/profile"            element={<Profile />} />
                <Route path="/billing"            element={<Billing />} />
                <Route path="/bookmarks"          element={<Bookmarks />} />
                <Route path="/cv-tailor"          element={<CVTailor />} />
                <Route path="/cv-versions"        element={<CVVersions />} />
                <Route path="/decision"           element={<DecisionEngine />} />
                <Route path="/privacy"            element={<Privacy />} />
                <Route path="/interview-prep"     element={<InterviewPrep />} />
                <Route path="/salary"             element={<SalaryIntel />} />
                <Route path="/timeline"           element={<ApplicationTimeline />} />
                <Route path="/referral"           element={<Referral />} />
            </Route>
        </Routes>
    );
}

function App() {
    return (
        <BrowserRouter>
            <I18nProvider>
                <AuthProvider>
                    <AnalyticsProvider>
                        <AppRouter />
                        <CookieConsent />
                    </AnalyticsProvider>
                </AuthProvider>
            </I18nProvider>
        </BrowserRouter>
    );
}

export default App;
