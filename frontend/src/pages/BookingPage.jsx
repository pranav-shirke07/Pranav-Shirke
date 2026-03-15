import { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { publicApi } from "@/services/api";

const services = ["Plumbing", "Electrical", "Cleaning", "General Handyman", "Other"];

const initialForm = {
  full_name: "",
  phone: "",
  email: "",
  service_type: "",
  address: "",
  preferred_date: "",
  notes: "",
};

export default function BookingPage() {
  const [form, setForm] = useState(initialForm);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [confirmationId, setConfirmationId] = useState("");

  const isStepOneValid = Boolean(form.full_name && form.phone && form.email);
  const isStepTwoValid = Boolean(form.service_type && form.address && form.preferred_date);
  const canGoNext = (step === 1 && isStepOneValid) || (step === 2 && isStepTwoValid);
  const canSubmit = isStepOneValid && isStepTwoValid;

  const onChange = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const submitBooking = async () => {
    setLoading(true);
    try {
      const payload = { ...form, notes: form.notes || "" };
      const response = await publicApi.createBooking(payload);
      setConfirmationId(response.id);
      setForm(initialForm);
      setStep(1);
      toast.success("Booking submitted successfully");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Booking failed. Please retry.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8" data-testid="booking-page">
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Book a Service</p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-tight">Tell us what you need, we’ll handle the rest.</h1>
        <p className="text-sm md:text-lg text-muted-foreground" data-testid="booking-page-subtitle">
          3-step booking flow with admin tracking and status updates.
        </p>
      </div>

      <Card className="rounded-3xl border-stone-200 bg-white/95">
        <CardHeader>
          <CardTitle data-testid="booking-step-title">Step {step} of 3</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {step === 1 && (
            <motion.div initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} className="grid gap-4">
              <div className="space-y-2">
                <Label htmlFor="full_name">Full Name</Label>
                <Input id="full_name" value={form.full_name} onChange={(e) => onChange("full_name", e.target.value)} data-testid="booking-full-name-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number</Label>
                <Input id="phone" value={form.phone} onChange={(e) => onChange("phone", e.target.value)} data-testid="booking-phone-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={form.email} onChange={(e) => onChange("email", e.target.value)} data-testid="booking-email-input" />
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} className="grid gap-4">
              <div className="space-y-2">
                <Label>Service Type</Label>
                <Select value={form.service_type} onValueChange={(value) => onChange("service_type", value)}>
                  <SelectTrigger data-testid="booking-service-select-trigger" className="h-12 rounded-xl bg-stone-50">
                    <SelectValue placeholder="Choose service" />
                  </SelectTrigger>
                  <SelectContent>
                    {services.map((service) => (
                      <SelectItem key={service} value={service} data-testid={`booking-service-option-${service.toLowerCase().replace(/\s+/g, "-")}`}>
                        {service}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="address">Address</Label>
                <Input id="address" value={form.address} onChange={(e) => onChange("address", e.target.value)} data-testid="booking-address-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="preferred_date">Preferred Date</Label>
                <Input
                  id="preferred_date"
                  type="date"
                  value={form.preferred_date}
                  onChange={(e) => onChange("preferred_date", e.target.value)}
                  data-testid="booking-date-input"
                />
              </div>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="notes">Additional Notes</Label>
                <Textarea
                  id="notes"
                  value={form.notes}
                  onChange={(e) => onChange("notes", e.target.value)}
                  placeholder="Share issue details or preferred time windows"
                  data-testid="booking-notes-input"
                />
              </div>
              <div className="rounded-2xl bg-stone-50 p-4 text-sm text-muted-foreground" data-testid="booking-review-box">
                <p data-testid="booking-review-name">Name: {form.full_name}</p>
                <p data-testid="booking-review-service">Service: {form.service_type}</p>
                <p data-testid="booking-review-date">Date: {form.preferred_date}</p>
              </div>
            </motion.div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <Button
              type="button"
              variant="outline"
              disabled={step === 1}
              onClick={() => setStep((prev) => prev - 1)}
              data-testid="booking-back-button"
            >
              Back
            </Button>

            {step < 3 ? (
              <Button type="button" disabled={!canGoNext} onClick={() => setStep((prev) => prev + 1)} data-testid="booking-next-button">
                Continue
              </Button>
            ) : (
              <Button type="button" disabled={loading || !canSubmit} onClick={submitBooking} data-testid="booking-submit-button">
                {loading ? "Submitting..." : "Confirm Booking"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {confirmationId && (
        <Card className="rounded-2xl border-accent/30 bg-accent/10">
          <CardContent className="py-5">
            <p className="text-sm text-accent" data-testid="booking-confirmation-message">
              Booking submitted successfully. Tracking ID:
            </p>
            <p className="font-mono text-base" data-testid="booking-confirmation-id">
              {confirmationId}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
