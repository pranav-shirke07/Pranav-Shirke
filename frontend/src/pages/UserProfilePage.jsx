import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "@/components/ui/sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { clearUserToken, getUserToken, userApi } from "@/services/api";

export default function UserProfilePage() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadData = async () => {
    if (!getUserToken()) {
      navigate("/account/auth");
      return;
    }

    try {
      const [profileData, bookingData] = await Promise.all([userApi.getProfile(), userApi.getMyBookings()]);
      setProfile(profileData);
      setBookings(bookingData);
    } catch {
      clearUserToken();
      navigate("/account/auth");
      toast.error("Please login again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const saveProfile = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      const updated = await userApi.updateProfile({
        full_name: profile.full_name,
        phone: profile.phone,
        address: profile.address,
        notify_email: profile.notify_email,
        notify_sms: profile.notify_sms,
      });
      setProfile(updated);
      toast.success("Profile updated.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Update failed.");
    } finally {
      setSaving(false);
    }
  };

  const logout = async () => {
    try {
      await userApi.logout();
    } catch {
      // Ignore network failure and clear token.
    }
    clearUserToken();
    navigate("/account/auth");
  };

  if (loading) {
    return <div data-testid="user-profile-loading">Loading profile...</div>;
  }

  if (!profile) {
    return <div data-testid="user-profile-empty">Profile unavailable.</div>;
  }

  return (
    <div className="space-y-8" data-testid="user-profile-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">My Profile</p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-tight">Manage account settings</h1>
        </div>
        <Button variant="outline" onClick={logout} data-testid="user-logout-button">
          Logout
        </Button>
      </div>

      <Link to="/account/notifications" data-testid="user-profile-notifications-link">
        <Button variant="outline">Open Notifications Inbox</Button>
      </Link>

      <Card className="rounded-3xl border-stone-200 bg-white">
        <CardContent className="grid gap-4 p-6 md:grid-cols-2">
          <div className="space-y-1">
            <Label>Full Name</Label>
            <Input value={profile.full_name} onChange={(event) => setProfile((prev) => ({ ...prev, full_name: event.target.value }))} data-testid="user-profile-name-input" />
          </div>
          <div className="space-y-1">
            <Label>Email</Label>
            <Input value={profile.email} disabled data-testid="user-profile-email-input" />
          </div>
          <div className="space-y-1">
            <Label>Phone</Label>
            <Input value={profile.phone} onChange={(event) => setProfile((prev) => ({ ...prev, phone: event.target.value }))} data-testid="user-profile-phone-input" />
          </div>
          <div className="space-y-1">
            <Label>Address</Label>
            <Input value={profile.address || ""} onChange={(event) => setProfile((prev) => ({ ...prev, address: event.target.value }))} data-testid="user-profile-address-input" />
          </div>

          <div className="flex items-center justify-between rounded-xl bg-stone-50 p-3">
            <p data-testid="user-profile-notify-email-label">Email Notifications</p>
            <Switch
              checked={profile.notify_email}
              onCheckedChange={(checked) => setProfile((prev) => ({ ...prev, notify_email: checked }))}
              data-testid="user-profile-notify-email-switch"
            />
          </div>
          <div className="flex items-center justify-between rounded-xl bg-stone-50 p-3">
            <p data-testid="user-profile-notify-sms-label">SMS Notifications</p>
            <Switch
              checked={profile.notify_sms}
              onCheckedChange={(checked) => setProfile((prev) => ({ ...prev, notify_sms: checked }))}
              data-testid="user-profile-notify-sms-switch"
            />
          </div>

          <div className="md:col-span-2">
            <Button onClick={saveProfile} disabled={saving} data-testid="user-profile-save-button">
              {saving ? "Saving..." : "Save Profile"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-3xl border-stone-200 bg-white">
        <CardContent className="space-y-4 p-6">
          <h2 className="text-3xl" data-testid="user-booking-history-title">My Booking History</h2>
          <div className="space-y-2">
            {bookings.map((booking) => (
              <div key={booking.id} className="rounded-xl border border-stone-200 p-3" data-testid={`user-booking-item-${booking.id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-mono text-xs" data-testid={`user-booking-id-${booking.id}`}>{booking.id}</p>
                  <Badge data-testid={`user-booking-status-${booking.id}`}>{booking.status}</Badge>
                </div>
                <p data-testid={`user-booking-service-${booking.id}`}>{booking.service_type}</p>
                <p className="text-sm text-muted-foreground" data-testid={`user-booking-date-${booking.id}`}>
                  Preferred: {booking.preferred_date}
                </p>
              </div>
            ))}
            {bookings.length === 0 && <p data-testid="user-bookings-empty">No bookings yet.</p>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
