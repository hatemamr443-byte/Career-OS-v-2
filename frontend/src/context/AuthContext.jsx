import { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { api } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const checkAuth = useCallback(async () => {
        try {
            const r = await api.get("/auth/me");
            setUser(r.data);
        } catch (err) {
            console.error("auth check failed:", err);
            setUser(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // CRITICAL: skip /me if returning from OAuth callback; AuthCallback handles it
        if (typeof window !== "undefined" && window.location.hash?.includes("session_id=")) {
            setLoading(false);
            return;
        }
        checkAuth();
    }, [checkAuth]);

    const logout = useCallback(async () => {
        try {
            await api.post("/auth/logout");
        } catch (err) {
            console.error("logout failed:", err);
        }
        setUser(null);
        window.location.href = "/";
    }, []);

    const value = useMemo(
        () => ({ user, setUser, loading, checkAuth, logout }),
        [user, loading, checkAuth, logout]
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
