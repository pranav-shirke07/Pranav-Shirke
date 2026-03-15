import { useState } from "react";
import { toast } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { publicApi } from "@/services/api";

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

  const onChange = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const submitWorker = async () => {
    setLoading(true);
    try {
      await publicApi.createWorkerSignup({ ...form, years_experience: Number(form.years_experience) });
      toast.success("Worker profile submitted");
      setForm(initialWorker);
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Signup failed. Please retry.");
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
                  {["Plumbing", "Electrical", "Cleaning", "General Handyman"].map((skill) => (
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
