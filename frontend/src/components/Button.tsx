import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
  loading?: boolean;
}

const variants = {
  primary: "bg-maroon-700 text-white hover:bg-maroon-800",
  secondary: "border border-stone-300 bg-white text-stone-800 hover:bg-stone-50",
  danger: "border border-red-300 bg-white text-red-700 hover:bg-red-50",
};

export default function Button({ variant = "primary", loading, disabled, children, className = "", ...rest }: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${className}`}
      {...rest}
    >
      {loading ? "Please wait…" : children}
    </button>
  );
}
