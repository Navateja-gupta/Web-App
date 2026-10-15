export interface TabItem<T extends string> {
  id: T;
  label: string;
}

export default function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: TabItem<T>[];
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div role="tablist" className="flex flex-wrap gap-1 border-b border-stone-200">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          type="button"
          aria-selected={tab.id === active}
          onClick={() => onChange(tab.id)}
          className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
            tab.id === active ? "border-maroon-700 text-maroon-800" : "border-transparent text-stone-600 hover:text-maroon-700"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
