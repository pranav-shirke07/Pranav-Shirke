import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "@/components/ui/sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getUserToken, userApi } from "@/services/api";

export default function UserNotificationsPage() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadNotifications = async () => {
    if (!getUserToken()) {
      navigate("/account/auth");
      return;
    }

    try {
      const data = await userApi.getNotifications();
      setNotifications(data);
    } catch {
      toast.error("Could not load notifications.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  const markRead = async (id) => {
    try {
      await userApi.markNotificationRead(id);
      setNotifications((prev) => prev.map((item) => (item.id === id ? { ...item, read: true } : item)));
    } catch {
      toast.error("Failed to mark notification as read.");
    }
  };

  if (loading) {
    return <div data-testid="user-notifications-loading">Loading notifications...</div>;
  }

  return (
    <div className="space-y-6" data-testid="user-notifications-page">
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Notification Inbox</p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-tight">Your booking and service alerts</h1>
      </div>

      <div className="space-y-3">
        {notifications.map((item) => (
          <Card key={item.id} className="rounded-2xl border-stone-200 bg-white" data-testid={`user-notification-item-${item.id}`}>
            <CardContent className="space-y-2 p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold" data-testid={`user-notification-title-${item.id}`}>{item.title}</p>
                <Badge data-testid={`user-notification-read-badge-${item.id}`}>{item.read ? "Read" : "Unread"}</Badge>
              </div>
              <p className="text-sm text-muted-foreground" data-testid={`user-notification-message-${item.id}`}>{item.message}</p>
              <p className="text-xs text-muted-foreground" data-testid={`user-notification-created-at-${item.id}`}>
                {new Date(item.created_at).toLocaleString()}
              </p>
              {!item.read && (
                <Button size="sm" variant="outline" onClick={() => markRead(item.id)} data-testid={`user-notification-mark-read-${item.id}`}>
                  Mark as Read
                </Button>
              )}
            </CardContent>
          </Card>
        ))}

        {notifications.length === 0 && (
          <p data-testid="user-notifications-empty" className="text-sm text-muted-foreground">
            No notifications yet.
          </p>
        )}
      </div>
    </div>
  );
}
