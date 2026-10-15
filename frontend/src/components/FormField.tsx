import { useId, type InputHTMLAttributes } from "react";

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  error?: string;
}

export default function FormField({ label, hint, error, className = "", ...inputProps }: FormFieldProps) {
  const id = useId();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-stone-700">
        {label}
        {inputProps.required && <span className="text-maroon-600"> *</span>}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={`mt-1 block w-full rounded-lg border px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-maroon-600 ${
          error ? "border-red-400" : "border-stone-300"
        }`}
        {...inputProps}
      />
      {error ? (
        <p id={`${id}-error`} className="mt-1 text-sm text-red-700">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="mt-1 text-xs text-stone-500">
            {hint}
          </p>
        )
      )}
    </div>
  );
}
