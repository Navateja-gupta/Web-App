import { useId, type TextareaHTMLAttributes } from "react";

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
  error?: string;
}

export default function TextArea({ label, hint, error, className = "", ...props }: TextAreaProps) {
  const id = useId();
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-stone-700">
        {label}
        {props.required && <span className="text-maroon-600"> *</span>}
      </label>
      <textarea
        id={id}
        rows={4}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? `${id}-help` : undefined}
        className={`mt-1 block w-full rounded-lg border px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-maroon-600 ${
          error ? "border-red-400" : "border-stone-300"
        }`}
        {...props}
      />
      {(error || hint) && (
        <p id={`${id}-help`} className={`mt-1 text-xs ${error ? "text-sm text-red-700" : "text-stone-500"}`}>
          {error ?? hint}
        </p>
      )}
    </div>
  );
}
