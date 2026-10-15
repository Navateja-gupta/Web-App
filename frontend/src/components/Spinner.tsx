export default function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-stone-600" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-maroon-600 border-t-transparent" />
      <span>{label}</span>
    </div>
  );
}
