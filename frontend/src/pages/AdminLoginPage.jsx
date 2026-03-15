import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { adminApi, setAdminToken } from "@/services/api";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@dialforhelp.com");
  const [password, setPassword] = useState("Admin@123");
  const [loading, setLoading] = useState(false);

  const login = async () => {
    setLoading(true);
    try {
      const response = await adminApi.login({ email, password });
      setAdminToken(response.token);
      toast.success("Admin login successful");
      navigate("/admin/dashboard");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Invalid login");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-gradient-to-br from-orange-50 via-white to-stone-100 p-6 md:p-10" data-testid="admin-login-page">
      <div className="mx-auto grid max-w-6xl gap-8 rounded-3xl border border-stone-200 bg-white/90 p-6 shadow-xl md:grid-cols-2 md:p-10">
        <div className="space-y-6">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Admin Access</p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-tight">Manage bookings, workers, and customer updates.</h1>
          <Card className="rounded-2xl border-stone-200 bg-stone-50">
            <CardContent className="space-y-2 p-4 text-sm">
              <p data-testid="admin-default-credentials-label">Default login for first use:</p>
              <p className="font-mono" data-testid="admin-default-email">Email: admin@dialforhelp.com</p>
              <p className="font-mono" data-testid="admin-default-password">Password: Admin@123</p>
            </CardContent>
          </Card>
        </div>

        <Card className="rounded-2xl border-stone-200 bg-white">
          <CardContent className="space-y-4 p-6 md:p-8">
            <div className="space-y-2">
              <Label htmlFor="admin_email">Admin Email</Label>
              <Input id="admin_email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="admin-email-input" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="admin_password">Password</Label>
              <Input
                id="admin_password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="admin-password-input"
              />
            </div>
            <Button className="w-full" type="button" disabled={loading} onClick={login} data-testid="admin-login-submit-button">
              {loading ? "Logging in..." : "Open Dashboard"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
