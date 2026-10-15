export type Role = "customer" | "vendor" | "admin";

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
