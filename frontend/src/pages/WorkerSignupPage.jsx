import { useState } from "react";
import { toast } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ALL_SERVICES } from "@/constants/services";
import { paymentsApi, publicApi } from "@/services/api";
import { loadRazorpayScript, openRazorpayCheckout } from "@/services/razorpay";

const workerSkills = ALL_SERVICES.map((item) => item.name).filter((item) => item !== "Other");

const initialWorker = {
  full_name: "",
  phone: "",
  email: "",
  skill: "",
  city: "",
  years_experience: 0,
  availability: "",
  about: "",
};

export default function WorkerSignupPage() {
  const [form, setForm] = useState(initialWorker);
  const [loading, setLoading] = useState(false);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [workerSubscription, setWorkerSubscription] = useState({
    hasActive: false,
    expiresAt: null,
  });

  const onChange = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const checkWorkerSubscription = async () => {
    if (!form.phone || !form.email) {
      toast.error("Enter phone and email to check subscription status.");
      return false;
    }

    try {
      const status = await paymentsApi.getWorkerSubscriptionStatus({
        phone: form.phone,
        email: form.email,
      });
      setWorkerSubscription({
        hasActive: status.has_active_subscription,
        expiresAt: status.subscription_expires_at,
      });
      return status.has_active_subscription;
    } catch {
      toast.error("Could not verify worker subscription status.");
      return false;
    }
  };

  const startWorkerSubscriptionPayment = async () => {
    if (!form.full_name || !form.phone || !form.email) {
      toast.error("Fill name, phone and email before payment.");
      return;
    }

    setPaymentLoading(true);
    try {
      const sdkLoaded = await loadRazorpayScript();
      if (!sdkLoaded) {
        toast.error("Could not load Razorpay checkout.");
        return;
      }

      const order = await paymentsApi.createOrder({
        plan_type: "worker",
        name: form.full_name,
        email: form.email,
        phone: form.phone,
      });

      const paymentResult = await openRazorpayCheckout({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "Dial For Help",
        description: `Worker Annual Plan ₹${order.amount_inr}`,
        order_id: order.order_id,
        prefill: {
          name: form.full_name,
          email: form.email,
          contact: form.phone,
        },
        notes: {
          plan_type: "worker",
        },
        theme: {
          color: "#ea580c",
        },
      });

      const verifyResponse = await paymentsApi.verifyOrder({
        plan_type: "worker",
        razorpay_order_id: paymentResult.razorpay_order_id,
        razorpay_payment_id: paymentResult.razorpay_payment_id,
        razorpay_signature: paymentResult.razorpay_signature,
        subscriber_name: form.full_name,
        email: form.email,
        phone: form.phone,
      });

      setWorkerSubscription({ hasActive: true, expiresAt: verifyResponse.active_until });
      toast.success("Worker subscription activated for 1 year.");
    } catch (error) {
      toast.error(error?.message || error?.response?.data?.detail || "Worker payment failed.");
    } finally {
      setPaymentLoading(false);
    }
  };

  const submitWorker = async () => {
    if (!workerSubscription.hasActive) {
      const active = await checkWorkerSubscription();
      if (!active) {
        toast.error("Worker annual subscription (₹199/year) is mandatory before signup.");
        return;
      }
    }

    setLoading(true);
    try {
      await publicApi.createWorkerSignup({ ...form, years_experience: Number(form.years_experience) });
      toast.success("Worker profile submitted");
      setForm(initialWorker);
      setWorkerSubscription({ hasActive: false, expiresAt: null });
    } catch (error) {
      const detail = error?.response?.data?.detail;
      if (error?.response?.status === 402) {
        toast.error(detail?.message || "Subscription required before signup.");
        setWorkerSubscription({ hasActive: false, expiresAt: null });
      } else {
        toast.error(detail || "Signup failed. Please retry.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8" data-testid="worker-signup-page">
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Worker Application</p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-tight">Join Dial For Help as a trusted local professional.</h1>
      </div>

      <Card className="rounded-3xl border-stone-200 bg-white/95">
        <CardHeader>
          <CardTitle data-testid="worker-signup-form-title">Worker Signup Form</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <Card className="rounded-2xl border-primary/30 bg-primary/10" data-testid="worker-subscription-card">
            <CardContent className="space-y-3 p-4 text-sm">
              <p data-testid="worker-subscription-pricing-text">Mandatory plan: ₹199/year before signup submission.</p>
              <p data-testid="worker-subscription-status-text">
                Subscription active: {workerSubscription.hasActive ? "Yes" : "No"}
              </p>
              {workerSubscription.expiresAt && (
                <p data-testid="worker-subscription-expiry-text">Valid till: {new Date(workerSubscription.expiresAt).toLocaleDateString()}</p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  onClick={startWorkerSubscriptionPayment}
                  disabled={paymentLoading}
                  data-testid="worker-subscription-pay-button"
                >
                  {paymentLoading ? "Opening Razorpay..." : "Pay ₹199/year"}
                </Button>
                <Button type="button" variant="outline" onClick={checkWorkerSubscription} data-testid="worker-subscription-check-button">
                  Check Active Plan
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="worker_name">Full Name</Label>
              <Input id="worker_name" value={form.full_name} onChange={(e) => onChange("full_name", e.target.value)} data-testid="worker-name-input" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="worker_phone">Phone</Label>
              <Input id="worker_phone" value={form.phone} onChange={(e) => onChange("phone", e.target.value)} data-testid="worker-phone-input" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="worker_email">Email</Label>
              <Input
                id="worker_email"
                type="email"
                value={form.email}
                onChange={(e) => onChange("email", e.target.value)}
                data-testid="worker-email-input"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="worker_city">City</Label>
              <Input id="worker_city" value={form.city} onChange={(e) => onChange("city", e.target.value)} data-testid="worker-city-input" />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Primary Skill</Label>
              <Select value={form.skill} onValueChange={(value) => onChange("skill", value)}>
                <SelectTrigger className="h-12 rounded-xl bg-stone-50" data-testid="worker-skill-select-trigger">
                  <SelectValue placeholder="Choose skill" />
                </SelectTrigger>
                <SelectContent>
                  {workerSkills.map((skill) => (
                    <SelectItem key={skill} value={skill} data-testid={`worker-skill-option-${skill.toLowerCase().replace(/\s+/g, "-")}`}>
                      {skill}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Availability</Label>
              <Select value={form.availability} onValueChange={(value) => onChange("availability", value)}>
                <SelectTrigger className="h-12 rounded-xl bg-stone-50" data-testid="worker-availability-select-trigger">
                  <SelectValue placeholder="Choose availability" />
                </SelectTrigger>
                <SelectContent>
                  {["Full-time", "Part-time", "Weekends"].map((availability) => (
                    <SelectItem key={availability} value={availability} data-testid={`worker-availability-option-${availability.toLowerCase().replace(/\s+/g, "-")}`}>
                      {availability}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="worker_exp">Years of Experience</Label>
            <Input
              id="worker_exp"
              type="number"
              min={0}
              value={form.years_experience}
              onChange={(e) => onChange("years_experience", e.target.value)}
              data-testid="worker-experience-input"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="worker_about">About Your Work</Label>
            <Textarea
              id="worker_about"
              value={form.about}
              onChange={(e) => onChange("about", e.target.value)}
              placeholder="Tell us what makes your service reliable"
              data-testid="worker-about-input"
            />
          </div>

          <Button type="button" onClick={submitWorker} disabled={loading} data-testid="worker-submit-button">
            {loading ? "Submitting..." : "Submit Application"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
