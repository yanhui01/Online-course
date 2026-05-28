import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Form, Input, Button, App, Typography } from "antd";
import { UserOutlined, LockOutlined, PlayCircleOutlined } from "@ant-design/icons";
import { loginApi, getMeApi } from "../api/auth";
import { useAuthStore } from "../stores/authStore";

const { Title, Text } = Typography;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setUser } = useAuthStore();
  const { message } = App.useApp();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const tokens = await loginApi(values);
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);

      const user = await getMeApi();
      setUser(user);
      message.success("登录成功");
      navigate("/dashboard");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "登录失败";
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      {/* 左侧图片区域 */}
      <div className="auth-banner">
        <div className="auth-banner-content">
          <PlayCircleOutlined style={{ fontSize: 64, color: "#fff", marginBottom: 24 }} />
          <Title level={1} style={{ color: "#fff", marginBottom: 12, fontSize: 36 }}>
            OnlineCourse
          </Title>
          <Text style={{ color: "rgba(255,255,255,0.85)", fontSize: 18, lineHeight: 1.8 }}>
            多平台网课助手
          </Text>
          <div className="auth-banner-features">
            <div className="auth-feature-item">
              <span className="auth-feature-dot" />
              智慧职教 · 知到 · 学堂在线
            </div>
            <div className="auth-feature-item">
              <span className="auth-feature-dot" />
              一键自动刷课，智能答题
            </div>
            <div className="auth-feature-item">
              <span className="auth-feature-dot" />
              多账号统一管理，实时进度
            </div>
          </div>
        </div>
      </div>

      {/* 右侧登录表单 */}
      <div className="auth-form-section">
        <div className="auth-form-wrapper">
          <Title level={2} style={{ textAlign: "center", marginBottom: 4 }}>
            欢迎回来
          </Title>
          <p style={{ textAlign: "center", color: "#999", marginBottom: 40 }}>
            登录您的账号以继续
          </p>
          <Form name="login" onFinish={onFinish} size="large" style={{ width: 360 }}>
            <Form.Item name="username" rules={[{ required: true, message: "请输入用户名" }]}>
              <Input prefix={<UserOutlined />} placeholder="用户名" />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 16 }}>
              <Button type="primary" htmlType="submit" loading={loading} block size="large">
                登录
              </Button>
            </Form.Item>
            <div style={{ textAlign: "center" }}>
              还没有账号？<Link to="/register">立即注册</Link>
            </div>
          </Form>
        </div>
      </div>
    </div>
  );
}
