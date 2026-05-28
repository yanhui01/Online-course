import client from "./client";

export interface PlatformAccount {
  id: string;
  platform: string;
  login_type: string;
  account_name: string;
  is_valid: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateAccountParams {
  platform: string;
  login_type: string;
  account_name: string;
  password?: string | null;
}

export async function getAccountsApi(page = 1, pageSize = 20) {
  const res = await client.get("/accounts", { params: { page, page_size: pageSize } });
  return res.data;
}

export async function createAccountApi(params: CreateAccountParams) {
  const res = await client.post("/accounts", params);
  return res.data;
}

export async function updateAccountApi(id: string, params: Partial<CreateAccountParams & { is_valid: boolean }>) {
  const res = await client.put(`/accounts/${id}`, params);
  return res.data;
}

export async function deleteAccountApi(id: string) {
  const res = await client.delete(`/accounts/${id}`);
  return res.data;
}

export async function sendSmsApi(accountId: string) {
  const res = await client.post("/accounts/send-sms", { account_id: accountId });
  return res.data;
}

export async function verifySmsApi(accountId: string, smsCode: string) {
  const res = await client.post("/accounts/verify-sms", {
    account_id: accountId,
    sms_code: smsCode,
  });
  return res.data;
}
