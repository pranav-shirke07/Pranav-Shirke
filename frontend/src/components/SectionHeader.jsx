export const SectionHeader = ({ eyebrow, title, description, testId }) => {
  return (
    <div className="max-w-3xl space-y-4" data-testid={testId}>
      <p className="text-xs font-semibold uppercase tracking-[0.3em] text-primary">{eyebrow}</p>
      <h2 className="text-4xl sm:text-5xl lg:text-6xl leading-tight text-balance">{title}</h2>
      <p className="text-sm md:text-base text-muted-foreground md:text-lg">{description}</p>
    </div>
  );
};
