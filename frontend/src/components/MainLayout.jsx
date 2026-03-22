import { Home, PhoneCall, Shield, UserPlus2 } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { Button } from "@/components/ui/button";

const navItems = [
  { to: "/", label: "Home", icon: Home },
  { to: "/book", label: "Book Help", icon: PhoneCall },
  { to: "/services", label: "Services", icon: Shield },
  { to: "/track-booking", label: "Track Booking", icon: Shield },
  { to: "/worker-signup", label: "Worker Signup", icon: UserPlus2 },
  { to: "/contact", label: "Contact", icon: PhoneCall },
];

export const MainLayout = () => {
  return (
    <div className="relative min-h-screen">
      <div className="gradient-wash" />
      <div className="noise-layer" />

      <header className="sticky top-0 z-30 border-b border-stone-200/70 bg-background/80 backdrop-blur-xl">
        <div className="safe-container flex flex-wrap items-center justify-between gap-3 py-4">
          <div data-testid="brand-title" className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-full bg-primary/15 p-2">
              <PhoneCall className="h-5 w-5 text-primary" />
            </div>
            <span className="font-semibold text-lg">Dial For Help</span>
          </div>

          <nav className="flex flex-wrap items-center gap-2" data-testid="main-navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink key={item.to} to={item.to} data-testid={`nav-link-${item.label.toLowerCase().replace(/\s+/g, "-")}`}>
                  {({ isActive }) => (
                    <Button
                      variant="ghost"
                      className={`rounded-full px-5 py-2 text-sm transition-colors ${
                        isActive ? "bg-primary text-primary-foreground hover:bg-primary/90" : "hover:bg-stone-100"
                      }`}
                    >
                      <Icon className="mr-2 h-4 w-4" />
                      {item.label}
                    </Button>
                  )}
                </NavLink>
              );
            })}
            <NavLink to="/admin" data-testid="nav-link-admin-login">
              <Button className="rounded-full px-5 py-2" variant="outline">
                <Shield className="mr-2 h-4 w-4" />
                Admin Login
              </Button>
            </NavLink>
            <NavLink to="/account/auth" data-testid="nav-link-user-account">
              <Button className="rounded-full px-5 py-2" variant="outline">
                User Account
              </Button>
            </NavLink>
            <NavLink to="/account/notifications" data-testid="nav-link-user-notifications">
              <Button className="rounded-full px-5 py-2" variant="outline">
                Notifications
              </Button>
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="safe-container py-20 md:py-24">
        <Outlet />
      </main>
    </div>
  );
};
