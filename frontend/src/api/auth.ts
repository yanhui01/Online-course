import client from "./client";
import type { LoginParams, RegisterParams, TokenResponse, User } from "../types/user";

export async function loginApi(params: LoginParams): Promise<TokenResponse> {
  const res = await client.post("/auth/login", params);
  return res.data;
}

export async function registerApi(params: RegisterParams): Promise<void> {
  await client.post("/auth/register", params);
}

export async function getMeApi(): Promise<User> {
  const res = await client.get("/users/me");
  return res.data;
}
