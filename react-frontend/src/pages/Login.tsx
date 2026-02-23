import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FileText, ArrowRight, Shield } from "lucide-react";

const Login = () => {
  const [companyId, setCompanyId] = useState("sg-security-001");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyId.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.login(companyId.trim());
      login(res.access_token, res.companyId);
      navigate("/opportunities");
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your Company ID.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md fade-in">
        {/* Logo / Brand */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary mb-5">
            <FileText className="w-7 h-7 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-bold text-foreground mb-2">ProposalAI</h1>
          <p className="text-muted-foreground text-base">
            Win more government contracts with AI-powered proposals
          </p>
        </div>

        {/* Login Card */}
        <div className="glass-card p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="companyId" className="block text-sm font-medium text-foreground mb-2">
                Company ID
              </label>
              <Input
                id="companyId"
                type="text"
                placeholder="Enter your company ID"
                value={companyId}
                onChange={(e) => setCompanyId(e.target.value)}
                className="h-11"
                autoFocus
              />
            </div>

            {error && (
              <div className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-11 text-sm font-medium"
              disabled={loading || !companyId.trim()}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                  Signing in…
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  Continue <ArrowRight className="w-4 h-4" />
                </span>
              )}
            </Button>
          </form>
        </div>

        {/* Trust footer */}
        <div className="flex items-center justify-center gap-2 mt-6 text-xs text-muted-foreground">
          <Shield className="w-3.5 h-3.5" />
          <span>Secure, encrypted connection</span>
        </div>
      </div>
    </div>
  );
};

export default Login;
