import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "@/components/ui/sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ALL_SERVICES } from "@/constants/services";
import { adminApi, clearAdminToken, getAdminToken } from "@/services/api";

const serviceOptions = [...ALL_SERVICES.map((item) => item.name), "Other"];

const statusTone = {
  pending: "bg-amber-100 text-amber-700",
  assigned: "bg-sky-100 text-sky-700",
  completed: "bg-green-100 text-green-700",
};

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingMap, setSavingMap] = useState({});
  const [suggestingMap, setSuggestingMap] = useState({});
  const [drafts, setDrafts] = useState({});
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [serviceFilter, setServiceFilter] = useState("all");

  const workers = overview?.workers || [];
  const bookings = overview?.bookings || [];

  const workerLookup = useMemo(
    () => workers.reduce((acc, worker) => ({ ...acc, [worker.id]: worker.full_name }), {}),
    [workers],
  );

  const filteredBookings = useMemo(() => {
    return bookings.filter((booking) => {
      const matchSearch =
        booking.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        booking.phone.toLowerCase().includes(searchTerm.toLowerCase()) ||
        booking.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        booking.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchStatus = statusFilter === "all" || booking.status === statusFilter;
      const matchService = serviceFilter === "all" || booking.service_type === serviceFilter;
      return matchSearch && matchStatus && matchService;
    });
  }, [bookings, searchTerm, statusFilter, serviceFilter]);

  const loadOverview = async () => {
    if (!getAdminToken()) {
      navigate("/admin");
      return;
    }

    try {
      const [overviewData, subscriptionData] = await Promise.all([
        adminApi.getOverview(),
        adminApi.getSubscriptions(),
      ]);
      setOverview(overviewData);
      setSubscriptions(subscriptionData);

      const nextDrafts = {};
      overviewData.bookings.forEach((booking) => {
        nextDrafts[booking.id] = {
          status: booking.status,
          assigned_worker_id: booking.assigned_worker_id || "none",
        };
      });
      setDrafts(nextDrafts);
    } catch {
      clearAdminToken();
      navigate("/admin");
      toast.error("Admin session expired. Please log in again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const updateDraft = (bookingId, field, value) => {
    setDrafts((prev) => ({
      ...prev,
      [bookingId]: { ...prev[bookingId], [field]: value },
    }));
  };

  const applyWorkerSuggestion = async (bookingId) => {
    setSuggestingMap((prev) => ({ ...prev, [bookingId]: true }));
    try {
      const suggestions = await adminApi.getWorkerSuggestions(bookingId);
      if (!suggestions.length) {
        toast.error("No workers available for suggestion.");
        return;
      }
      const recommended = suggestions[0];
      updateDraft(bookingId, "assigned_worker_id", recommended.worker_id);
      if ((drafts[bookingId]?.status || "pending") === "pending") {
        updateDraft(bookingId, "status", "assigned");
      }
      toast.success(`Suggested worker: ${recommended.full_name}`);
    } catch {
      toast.error("Could not fetch worker suggestions.");
    } finally {
      setSuggestingMap((prev) => ({ ...prev, [bookingId]: false }));
    }
  };

  const saveBooking = async (bookingId) => {
    const draft = drafts[bookingId];
    if (!draft) return;

    setSavingMap((prev) => ({ ...prev, [bookingId]: true }));
    try {
      await adminApi.updateBookingStatus(bookingId, {
        status: draft.status,
        assigned_worker_id: draft.assigned_worker_id === "none" ? null : draft.assigned_worker_id,
      });
      toast.success("Booking updated");
      await loadOverview();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Could not update booking");
    } finally {
      setSavingMap((prev) => ({ ...prev, [bookingId]: false }));
    }
  };

  const logout = async () => {
    try {
      await adminApi.logout();
    } catch {
      // Ignore and clear local token anyway.
    }
    clearAdminToken();
    navigate("/admin");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-stone-100 p-8" data-testid="admin-dashboard-loading">
        <p className="text-sm text-muted-foreground">Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-100 p-4 md:p-8" data-testid="admin-dashboard-page">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Admin Dashboard</p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-tight">Dial For Help Operations</h1>
          </div>
          <Button variant="outline" onClick={logout} data-testid="admin-logout-button">
            Logout
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-5">
          {[
            ["Pending", overview?.stats?.pending ?? 0],
            ["Assigned", overview?.stats?.assigned ?? 0],
            ["Completed", overview?.stats?.completed ?? 0],
            ["Workers", overview?.stats?.total_workers ?? 0],
            ["Contacts", overview?.stats?.total_contacts ?? 0],
          ].map(([label, value]) => (
            <Card key={label} className="rounded-2xl border-stone-200 bg-white">
              <CardContent className="space-y-1 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground" data-testid={`stat-label-${label.toLowerCase()}`}>
                  {label}
                </p>
                <p className="text-3xl font-semibold" data-testid={`stat-value-${label.toLowerCase()}`}>
                  {value}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="rounded-2xl border-stone-200 bg-white">
          <CardContent className="grid gap-3 p-4 md:grid-cols-3">
            <Input
              placeholder="Search by booking ID, name, phone, email"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              data-testid="admin-booking-search-input"
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger data-testid="admin-booking-status-filter">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="assigned">Assigned</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={serviceFilter} onValueChange={setServiceFilter}>
              <SelectTrigger data-testid="admin-booking-service-filter">
                <SelectValue placeholder="Filter by service" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Services</SelectItem>
                {serviceOptions.map((service) => (
                  <SelectItem key={service} value={service}>
                    {service}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        <Tabs defaultValue="bookings" className="space-y-4" data-testid="admin-dashboard-tabs">
          <TabsList>
            <TabsTrigger value="bookings" data-testid="tab-bookings">Bookings</TabsTrigger>
            <TabsTrigger value="subscriptions" data-testid="tab-subscriptions">Subscriptions</TabsTrigger>
            <TabsTrigger value="workers" data-testid="tab-workers">Workers</TabsTrigger>
            <TabsTrigger value="contacts" data-testid="tab-contacts">Contacts</TabsTrigger>
          </TabsList>

          <TabsContent value="bookings">
            <Card className="rounded-2xl border-stone-200 bg-white">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Customer</TableHead>
                      <TableHead>Service</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Assign Worker</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredBookings.map((booking) => (
                      <TableRow key={booking.id} data-testid={`booking-row-${booking.id}`}>
                        <TableCell>
                          <div>
                            <p className="font-medium" data-testid={`booking-customer-${booking.id}`}>{booking.full_name}</p>
                            <p className="text-xs text-muted-foreground" data-testid={`booking-contact-${booking.id}`}>
                              {booking.phone} • {booking.email}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell data-testid={`booking-service-${booking.id}`}>{booking.service_type}</TableCell>
                        <TableCell data-testid={`booking-charge-type-${booking.id}`}>{booking.charge_type}</TableCell>
                        <TableCell>
                          <div className="space-y-2">
                            <Badge className={statusTone[drafts[booking.id]?.status || booking.status]} data-testid={`booking-status-badge-${booking.id}`}>
                              {drafts[booking.id]?.status || booking.status}
                            </Badge>
                            <Select
                              value={drafts[booking.id]?.status || booking.status}
                              onValueChange={(value) => updateDraft(booking.id, "status", value)}
                            >
                              <SelectTrigger className="h-9 w-[140px]" data-testid={`booking-status-select-${booking.id}`}>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {["pending", "assigned", "completed"].map((statusOption) => (
                                  <SelectItem
                                    key={statusOption}
                                    value={statusOption}
                                    data-testid={`booking-status-option-${booking.id}-${statusOption}`}
                                  >
                                    {statusOption}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Select
                            value={drafts[booking.id]?.assigned_worker_id || "none"}
                            onValueChange={(value) => updateDraft(booking.id, "assigned_worker_id", value)}
                          >
                            <SelectTrigger className="h-9 w-[180px]" data-testid={`booking-worker-select-${booking.id}`}>
                              <SelectValue placeholder="Select worker" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none" data-testid={`booking-worker-option-${booking.id}-none`}>
                                Unassigned
                              </SelectItem>
                              {workers.map((worker) => (
                                <SelectItem key={worker.id} value={worker.id} data-testid={`booking-worker-option-${booking.id}-${worker.id}`}>
                                  {worker.full_name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {booking.assigned_worker_id && (
                            <p className="mt-1 text-xs text-muted-foreground" data-testid={`booking-assigned-worker-label-${booking.id}`}>
                              Current: {workerLookup[booking.assigned_worker_id] || "Unknown worker"}
                            </p>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => applyWorkerSuggestion(booking.id)}
                              disabled={Boolean(suggestingMap[booking.id])}
                              data-testid={`booking-suggest-button-${booking.id}`}
                            >
                              {suggestingMap[booking.id] ? "Suggesting..." : "Suggest"}
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => saveBooking(booking.id)}
                              disabled={Boolean(savingMap[booking.id])}
                              data-testid={`booking-save-button-${booking.id}`}
                            >
                              {savingMap[booking.id] ? "Saving..." : "Save"}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                    {filteredBookings.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6} className="py-8 text-center text-muted-foreground" data-testid="bookings-empty-message">
                          No bookings match current filters.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="subscriptions">
            <Card className="rounded-2xl border-stone-200 bg-white">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Subscriber</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Expires</TableHead>
                      <TableHead>Reminder</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {subscriptions.map((entry) => (
                      <TableRow key={entry.id} data-testid={`subscription-row-${entry.id}`}>
                        <TableCell>
                          <p data-testid={`subscription-name-${entry.id}`}>{entry.subscriber_name}</p>
                          <p className="text-xs text-muted-foreground" data-testid={`subscription-contact-${entry.id}`}>
                            {entry.email} • {entry.phone}
                          </p>
                        </TableCell>
                        <TableCell data-testid={`subscription-plan-${entry.id}`}>{entry.plan_type}</TableCell>
                        <TableCell data-testid={`subscription-status-${entry.id}`}>{entry.status}</TableCell>
                        <TableCell data-testid={`subscription-expiry-${entry.id}`}>
                          {new Date(entry.expires_at).toLocaleDateString()} ({entry.days_remaining} days)
                        </TableCell>
                        <TableCell>
                          <Badge
                            className={entry.renewal_reminder_due ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"}
                            data-testid={`subscription-reminder-${entry.id}`}
                          >
                            {entry.renewal_reminder_due ? "Reminder Due" : "Healthy"}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                    {subscriptions.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="py-8 text-center text-muted-foreground" data-testid="subscriptions-empty-message">
                          No subscriptions yet.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="workers">
            <Card className="rounded-2xl border-stone-200 bg-white">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Skill</TableHead>
                      <TableHead>City</TableHead>
                      <TableHead>Availability</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {overview.workers.map((worker) => (
                      <TableRow key={worker.id} data-testid={`worker-row-${worker.id}`}>
                        <TableCell data-testid={`worker-name-${worker.id}`}>{worker.full_name}</TableCell>
                        <TableCell data-testid={`worker-skill-${worker.id}`}>{worker.skill}</TableCell>
                        <TableCell data-testid={`worker-city-${worker.id}`}>{worker.city}</TableCell>
                        <TableCell data-testid={`worker-availability-${worker.id}`}>{worker.availability}</TableCell>
                      </TableRow>
                    ))}
                    {overview.workers.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={4} className="py-8 text-center text-muted-foreground" data-testid="workers-empty-message">
                          No workers signed up yet.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="contacts">
            <Card className="rounded-2xl border-stone-200 bg-white">
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Message</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {overview.contacts.map((contact) => (
                      <TableRow key={contact.id} data-testid={`contact-row-${contact.id}`}>
                        <TableCell data-testid={`contact-name-${contact.id}`}>{contact.name}</TableCell>
                        <TableCell data-testid={`contact-email-${contact.id}`}>{contact.email}</TableCell>
                        <TableCell data-testid={`contact-phone-${contact.id}`}>{contact.phone}</TableCell>
                        <TableCell data-testid={`contact-message-${contact.id}`}>{contact.message}</TableCell>
                      </TableRow>
                    ))}
                    {overview.contacts.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={4} className="py-8 text-center text-muted-foreground" data-testid="contacts-empty-message">
                          No contact messages yet.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
