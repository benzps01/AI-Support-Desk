import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

const decodeToken = (token) => {
    try {
        const base64Url = token.split(".")[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            atob(base64)
                .split('')
                .map((c) => '%' + ('00' + c.charAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(jsonPayload);
    } catch (error) {
        return null;
    }
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const access_token = localStorage.getItem("access_token");
        if (access_token) {
            const token = decodeToken(access_token);
            if (token != null) {
                setUser({
                    id: token.sub,
                    role: token.role,
                    org_id: token.org_id
                });
            } else {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
                setUser(null);
            }
        } else {
            setUser(null);
        };
        setLoading(false);
    }, []);

    const login = async (email, password) => {
        const response = await api.post("/auth/login", { email, password });
        localStorage.setItem("access_token", response.data.access_token);
        localStorage.setItem("refresh_token", response.data.refresh_token);
        const token = decodeToken(response.data.access_token);
        setUser({
            id: token.sub,
            role: token.role,
            org_id: token.org_id
        });
    };

    const register = async (name, email, password, role, org_name) => {
        const response = await api.post("/auth/register", { name, email, password, role, org_name });
        localStorage.setItem("access_token", response.data.access_token);
        localStorage.setItem("refresh_token", response.data.refresh_token);
        const token = decodeToken(response.data.access_token);
        setUser({
            id: token.sub,
            role: token.role,
            org_id: token.org_id
        });
    };

    const logout = () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        setUser(null);
        window.location.href = "/login";
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used with AuthProvider")
    }
    return context;
};
