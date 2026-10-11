export interface User {
  id: string;
  email: string;
  display_name: string | null;
}

export interface Profile {
  id: string;
  name: string;
  relationship: string;
  preferred_name: string | null;
  created_at: string;
  updated_at: string;
}
