import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Form, Input, Button, App, Typography } from "antd";
import { UserOutlined, LockOutlined, MailOutlined, PlayCircleOutlined } from "@ant-design/icons";
import { registerApi } from "../api/auth";

const { Title, Text } = Typography;

export default function RegisterPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { message } = App.useApp();

  const onFinish = async (values: { username: string; email: string; password: string }) => {
    setLoading(true);
    try {
      await registerApi(values);
      message.success("注册成功，请登录");
      navigate("/login");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "注册失败";
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

      {/* 右侧注册表单 */}
      <div className="auth-form-section">
        <div className="auth-form-wrapper">
          <Title level={2} style={{ textAlign: "center", marginBottom: 4 }}>
            创建账号
          </Title>
          <p style={{ textAlign: "center", color: "#999", marginBottom: 40 }}>
            注册以开始使用
          </p>
          <Form name="register" onFinish={onFinish} size="large" style={{ width: 360 }}>
            <Form.Item name="username" rules={[{ required: true, message: "请输入用户名" }]}>
              <Input prefix={<UserOutlined />} placeholder="用户名" />
            </Form.Item>
            <Form.Item
              name="email"
              rules={[
                { required: true, message: "请输入邮箱" },
                { type: "email", message: "邮箱格式不正确" },
              ]}
            >
              <Input prefix={<MailOutlined />} placeholder="邮箱" />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, min: 6, message: "密码至少6位" }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>
            <Form.Item
              name="confirm"
              dependencies={["password"]}
              rules={[
                { required: true, message: "请确认密码" },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue("password") === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error("两次输入的密码不一致"));
                  },
                }),
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="确认密码" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 16 }}>
              <Button type="primary" htmlType="submit" loading={loading} block size="large">
                注册
              </Button>
            </Form.Item>
            <div style={{ textAlign: "center" }}>
              已有账号？<Link to="/login">立即登录</Link>
            </div>
          </Form>
        </div>
      </div>
    </div>
  );
}
