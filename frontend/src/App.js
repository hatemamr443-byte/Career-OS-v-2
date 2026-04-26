import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import AuthCallback from "./components/AuthCallback";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Jobs from "./pages/Jobs";
import JobDetail from "./pages/JobDetail";
import Emails from "./pages/Emails";
import Insights from "./pages/Insights";
import CareerMap from "./pages/CareerMap";
import Profile from "./pages/Profile";
import Layout from "./components/Layout";
import "./App.css";

function AppRouter() {
    const location = useLocation();
    if (location.hash?.includes("session_id=")) {
        return <AuthCallback />;
    }
    return (
        <Routes>
            <Route path="/" element={<Login />} />
            <Route path="/login" element={<Login />} />
            <Route element={<Layout />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/jobs" element={<Jobs />} />
                <Route path="/jobs/:id" element={<JobDetail />} />
                <Route path="/emails" element={<Emails />} />
                <Route path="/insights" element={<Insights />} />
                <Route path="/career-map" element={<CareerMap />} />
                <Route path="/profile" element={<Profile />} />
            </Route>
        </Routes>
    );
}

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <AppRouter />
            </AuthProvider>
        </BrowserRouter>
    );
}

export default App;
