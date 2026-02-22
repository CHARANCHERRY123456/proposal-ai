import React, { createContext, useContext, useState, useCallback, useEffect } from "react";

interface AuthState {
  token: string | null;
  companyId: string | null;
  isAuthenticated: boolean;
  login: (token: string, companyId: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("access_token"));
  const [companyId, setCompanyId] = useState<string | null>(() => localStorage.getItem("company_id"));

  const login = useCallback((t: string, c: string) => {
    localStorage.setItem("access_token", t);
    localStorage.setItem("company_id", c);
    setToken(t);
    setCompanyId(c);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("company_id");
    setToken(null);
    setCompanyId(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, companyId, isAuthenticated: !!token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
