import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Bolt, Brush, Clock3, ShieldCheck, Wrench } from "lucide-react";
import { Link } from "react-router-dom";
import { APP_IMAGES } from "@/constants/images";
import { ALL_SERVICES } from "@/constants/services";
import { SectionHeader } from "@/components/SectionHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const serviceCards = [
  { title: "Plumbing", icon: Wrench, image: APP_IMAGES.plumber },
  { title: "Electrical", icon: Bolt, image: APP_IMAGES.electrician },
  { title: "Cleaning", icon: Brush, image: APP_IMAGES.cleaner },
];

const reasonCards = [
  { title: "Rapid Response", desc: "Book help in under 2 minutes.", icon: Clock3 },
  { title: "Verified Workers", desc: "Screened professionals for home safety.", icon: ShieldCheck },
  { title: "Simple Tracking", desc: "See status from pending to completed.", icon: Wrench },
];

export default function HomePage() {
  const [query, setQuery] = useState("");

  const quickResults = useMemo(() => {
    return ALL_SERVICES.filter((item) => item.name.toLowerCase().includes(query.toLowerCase())).slice(0, 6);
  }, [query]);

  return (
    <div className="space-y-24 md:space-y-32" data-testid="home-page">
      <section className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
          <SectionHeader
            eyebrow="Emergency Home Support"
            title="A trusted worker at your door when life gets messy."
            description="Dial For Help connects families with reliable electricians, plumbers, and cleaners with one smooth booking flow."
            testId="hero-section-header"
          />
          <div className="flex flex-wrap gap-3">
            <Link to="/book" data-testid="hero-book-now-link">
              <Button className="rounded-full px-8 py-6 text-base font-semibold">Book Help Now</Button>
            </Link>
            <Link to="/services" data-testid="hero-view-services-link">
              <Button variant="outline" className="rounded-full px-8 py-6 text-base font-semibold">
                View All Services
              </Button>
            </Link>
            <Link to="/worker-signup" data-testid="hero-join-workers-link">
              <Button variant="outline" className="rounded-full px-8 py-6 text-base font-semibold">
                Join as Worker
              </Button>
            </Link>
          </div>
          <p className="text-sm text-muted-foreground" data-testid="hero-trust-text">
            Status updates + notification-ready flow for customer and admin.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="overflow-hidden rounded-3xl border border-stone-200 bg-white p-3 shadow-xl"
          data-testid="hero-image-card"
        >
          <div className="aspect-[4/3] overflow-hidden rounded-2xl">
            <img
              src={APP_IMAGES.hero}
              alt="Family receiving support from home service professional"
              className="h-full w-full object-cover object-center"
              data-testid="hero-image"
            />
          </div>
        </motion.div>
      </section>

      <section className="space-y-8" data-testid="services-section">
        <SectionHeader
          eyebrow="Services"
          title="Professional help across your everyday home needs"
          description="Choose your service type, share details, and our team handles the rest."
          testId="services-section-header"
        />
        <div className="grid gap-6 md:grid-cols-3">
          {serviceCards.map((service, index) => {
            const Icon = service.icon;
            return (
              <motion.div
                key={service.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.08 }}
              >
                <Card className="overflow-hidden rounded-3xl border-stone-200 bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-md">
                  <CardContent className="space-y-4 p-5">
                    <div className="aspect-square overflow-hidden rounded-2xl" data-testid={`service-image-wrapper-${service.title.toLowerCase()}`}>
                      <img
                        src={service.image}
                        alt={service.title}
                        className="h-full w-full object-cover object-center"
                        data-testid={`service-image-${service.title.toLowerCase()}`}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <h3 className="text-xl" data-testid={`service-title-${service.title.toLowerCase()}`}>
                        {service.title}
                      </h3>
                      <Icon className="h-5 w-5 text-primary" />
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>

        <Card className="rounded-3xl border-stone-200 bg-white">
          <CardContent className="space-y-4 p-6">
            <p className="text-sm font-medium" data-testid="home-service-search-label">Quick service search</p>
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search services like AC Repair, Pest Control..."
              data-testid="home-service-search-input"
            />
            <div className="flex flex-wrap gap-2" data-testid="home-service-search-results">
              {(query ? quickResults : ALL_SERVICES.slice(0, 6)).map((service) => (
                <span
                  key={service.name}
                  className="rounded-full bg-stone-100 px-3 py-1 text-sm"
                  data-testid={`home-service-tag-${service.name.toLowerCase().replace(/\s+/g, "-")}`}
                >
                  {service.name}
                </span>
              ))}
              {query && quickResults.length === 0 && (
                <span className="text-sm text-muted-foreground" data-testid="home-service-search-empty">
                  No matching service found.
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-3" data-testid="why-choose-us-section">
        {reasonCards.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.title} className="rounded-3xl border-stone-200 bg-white/90 shadow-sm">
              <CardContent className="space-y-4 p-6">
                <Icon className="h-6 w-6 text-primary" />
                <h3 className="text-2xl" data-testid={`reason-title-${item.title.toLowerCase().replace(/\s+/g, "-")}`}>
                  {item.title}
                </h3>
                <p className="text-sm text-muted-foreground" data-testid={`reason-desc-${item.title.toLowerCase().replace(/\s+/g, "-")}`}>
                  {item.desc}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </section>
    </div>
  );
}
