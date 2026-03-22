import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setUserToken, userApi } from "@/services/api";

const initialRegister = {
  full_name: "",
  email: "",
  password: "",
  phone: "",
  address: "",
};

export default function UserAuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [registerForm, setRegisterForm] = useState(initialRegister);
  const [loading, setLoading] = useState(false);

  const handleAuth = async () => {
    setLoading(true);
    try {
      const response =
        mode === "login"
          ? await userApi.login(loginForm)
          : await userApi.register({ ...registerForm, notify_email: true, notify_sms: true });

      setUserToken(response.token);
      toast.success(mode === "login" ? "Signed in successfully" : "Account created successfully");
      navigate("/account/profile");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8" data-testid="user-auth-page">
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">User Access</p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-tight">Sign in to manage your profile and bookings.</h1>
      </div>

      <Card className="rounded-3xl border-stone-200 bg-white/95">
        <CardContent className="space-y-4 p-6">
          <div className="flex gap-2">
            <Button variant={mode === "login" ? "default" : "outline"} onClick={() => setMode("login")} data-testid="user-auth-login-tab">
              Login
            </Button>
            <Button variant={mode === "register" ? "default" : "outline"} onClick={() => setMode("register")} data-testid="user-auth-register-tab">
              Register
            </Button>
          </div>

          {mode === "login" ? (
            <div className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="user_login_email">Email</Label>
                <Input
                  id="user_login_email"
                  type="email"
                  value={loginForm.email}
                  onChange={(event) => setLoginForm((prev) => ({ ...prev, email: event.target.value }))}
                  data-testid="user-login-email-input"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="user_login_password">Password</Label>
                <Input
                  id="user_login_password"
                  type="password"
                  value={loginForm.password}
                  onChange={(event) => setLoginForm((prev) => ({ ...prev, password: event.target.value }))}
                  data-testid="user-login-password-input"
                />
              </div>
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="user_register_name">Full Name</Label>
                <Input
                  id="user_register_name"
                  value={registerForm.full_name}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, full_name: event.target.value }))}
                  data-testid="user-register-name-input"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="user_register_phone">Phone</Label>
                <Input
                  id="user_register_phone"
                  value={registerForm.phone}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, phone: event.target.value }))}
                  data-testid="user-register-phone-input"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="user_register_email">Email</Label>
                <Input
                  id="user_register_email"
                  type="email"
                  value={registerForm.email}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, email: event.target.value }))}
                  data-testid="user-register-email-input"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="user_register_password">Password</Label>
                <Input
                  id="user_register_password"
                  type="password"
                  value={registerForm.password}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, password: event.target.value }))}
                  data-testid="user-register-password-input"
                />
              </div>
              <div className="space-y-1 md:col-span-2">
                <Label htmlFor="user_register_address">Address</Label>
                <Input
                  id="user_register_address"
                  value={registerForm.address}
                  onChange={(event) => setRegisterForm((prev) => ({ ...prev, address: event.target.value }))}
                  data-testid="user-register-address-input"
                />
              </div>
            </div>
          )}

          <Button onClick={handleAuth} disabled={loading} data-testid="user-auth-submit-button">
            {loading ? "Please wait..." : mode === "login" ? "Login" : "Create Account"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
