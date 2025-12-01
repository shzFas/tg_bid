export interface Request {
  id: number;
  phone: string;
  name: string;
  city: string;
  description: string;
  specialization: string;
  tg_chat_id: string;
  status: string;
  claimed_by_id?: number;
  claimed_by_username?: string;
  claimed_at?: string;
  created_at: string;
  tg_message_id?: string;
  cancel_note?: string;
}

export interface Specialist {
  id: number;
  tg_id: string;
  username: string | null;
  name: string;
  phone: string | null;
  is_approved: boolean;
  created_at: string;
  specializations: string[];
}

