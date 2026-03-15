import { useState } from "react";
import { Mail, PhoneCall } from "lucide-react";
import { toast } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { publicApi } from "@/services/api";

const initialContact = { name: "", email: "", phone: "", message: "" };

export default function ContactPage() {
  const [form, setForm] = useState(initialContact);
  const [loading, setLoading] = useState(false);

  const onChange = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const submitContact = async () => {
    setLoading(true);
    try {
      await publicApi.createContact(form);
      toast.success("Message sent. Our team will reach out soon.");
      setForm(initialContact);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Could not send message.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]" data-testid="contact-page">
      <Card className="rounded-3xl border-stone-200 bg-white/95">
        <CardContent className="space-y-5 p-6 md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">Support Team</p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-tight">Need help with a booking?</h1>
          <p className="text-sm md:text-lg text-muted-foreground" data-testid="contact-support-text">
            Tell us your concern and our team will get back quickly.
          </p>
          <div className="space-y-3 rounded-2xl bg-stone-50 p-4 text-sm">
            <p className="flex items-center gap-2" data-testid="contact-phone-info">
              <PhoneCall className="h-4 w-4 text-primary" /> +1 (000) 123-4567
            </p>
            <p className="flex items-center gap-2" data-testid="contact-email-info">
              <Mail className="h-4 w-4 text-primary" /> support@dialforhelp.com
            </p>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-3xl border-stone-200 bg-white/95">
        <CardContent className="grid gap-4 p-6 md:p-8">
          <div className="space-y-2">
            <Label htmlFor="contact_name">Name</Label>
            <Input id="contact_name" value={form.name} onChange={(e) => onChange("name", e.target.value)} data-testid="contact-name-input" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_email">Email</Label>
            <Input
              id="contact_email"
              type="email"
              value={form.email}
              onChange={(e) => onChange("email", e.target.value)}
              data-testid="contact-email-input"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_phone">Phone</Label>
            <Input id="contact_phone" value={form.phone} onChange={(e) => onChange("phone", e.target.value)} data-testid="contact-phone-input" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="contact_message">Message</Label>
            <Textarea
              id="contact_message"
              value={form.message}
              onChange={(e) => onChange("message", e.target.value)}
              data-testid="contact-message-input"
            />
          </div>
          <Button type="button" onClick={submitContact} disabled={loading} data-testid="contact-submit-button">
            {loading ? "Sending..." : "Send Message"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
