import { useMemo, useState } from "react";
import { ALL_SERVICES } from "@/constants/services";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const categories = ["All", ...new Set(ALL_SERVICES.map((item) => item.category))];

export default function AllServicesPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");

  const filtered = useMemo(() => {
    return ALL_SERVICES.filter((service) => {
      const queryMatch =
        service.name.toLowerCase().includes(query.toLowerCase()) ||
        service.description.toLowerCase().includes(query.toLowerCase());
      const categoryMatch = category === "All" || service.category === category;
      return queryMatch && categoryMatch;
    });
  }, [query, category]);

  return (
    <div className="space-y-8" data-testid="all-services-page">
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">All Services</p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl leading-tight">Browse and search every available service.</h1>
      </div>

      <div className="grid gap-3 md:grid-cols-[2fr_1fr]">
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search service name or need"
          data-testid="services-search-input"
        />
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger data-testid="services-category-filter">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            {categories.map((entry) => (
              <SelectItem key={entry} value={entry}>
                {entry}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((service) => (
          <Card key={service.name} className="rounded-2xl border-stone-200 bg-white" data-testid={`service-card-${service.name.toLowerCase().replace(/\s+/g, "-")}`}>
            <CardContent className="space-y-2 p-5">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground" data-testid={`service-category-${service.name.toLowerCase().replace(/\s+/g, "-")}`}>
                {service.category}
              </p>
              <h3 className="text-2xl" data-testid={`service-name-${service.name.toLowerCase().replace(/\s+/g, "-")}`}>
                {service.name}
              </h3>
              <p className="text-sm text-muted-foreground" data-testid={`service-description-${service.name.toLowerCase().replace(/\s+/g, "-")}`}>
                {service.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
