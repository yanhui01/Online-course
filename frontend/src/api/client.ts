import axios from "axios";
import { message } from "antd";

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// 请求拦截器：自动附加 access_token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：自动刷新 token 或跳转登录
let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem("refresh_token");

      if (!refreshToken) {
        localStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      if (!isRefreshing) {
        isRefreshing = true;
        originalRequest._retry = true;

        try {
          const res = await axios.post("/api/v1/auth/refresh", {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token } = res.data;

          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", refresh_token);

          isRefreshing = false;
          refreshQueue.forEach((cb) => cb(access_token));
          refreshQueue = [];

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return client(originalRequest);
        } catch {
          isRefreshing = false;
          refreshQueue = [];
          localStorage.clear();
          window.location.href = "/login";
          return Promise.reject(error);
        }
      } else {
        return new Promise((resolve) => {
          refreshQueue.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(client(originalRequest));
          });
        });
      }
    }

    return Promise.reject(error);
  }
);

export default client;
