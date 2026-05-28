export interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginParams {
  username: string;
  password: string;
}

export interface RegisterParams {
  username: string;
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
