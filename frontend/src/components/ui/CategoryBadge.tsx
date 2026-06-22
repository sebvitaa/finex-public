type CategoryBadgeProps = {
  name: string;
  color: string;
};

export function CategoryBadge({ name, color }: CategoryBadgeProps) {
  return (
    <span className="inline-flex max-w-full items-center gap-2 rounded-[8px] border border-border bg-surface2 px-2 py-1 text-xs text-text">
      <span aria-hidden="true" className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: color }} />
      <span className="truncate">{name}</span>
    </span>
  );
}
