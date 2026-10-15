import { useId, type SelectHTMLAttributes } from "react";

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  options: { value: string; label: string }[];
  placeholder?: string;
}

export default function SelectField({ label, error, options, placeholder, className = "", ...props }: SelectFieldProps) {
  const id = useId();
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-stone-700">
        {label}
        {props.required && <span className="text-maroon-600"> *</span>}
      </label>
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        className={`mt-1 block w-full rounded-lg border bg-white px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-maroon-600 ${
          error ? "border-red-400" : "border-stone-300"
        }`}
        {...props}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1 text-sm text-red-700">{error}</p>}
    </div>
  );
}
