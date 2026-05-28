import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { Layout as AntLayout, Menu, Button, Avatar, Dropdown, Typography } from "antd";
import {
  DashboardOutlined,
  UserOutlined,
  BookOutlined,
  ScheduleOutlined,
  QuestionCircleOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlayCircleOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../stores/authStore";

const { Header, Sider, Content } = AntLayout;

const menuItems = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "数据概览" },
  { key: "/accounts", icon: <UserOutlined />, label: "平台账号" },
  { key: "/courses", icon: <BookOutlined />, label: "课程管理" },
  { key: "/tasks", icon: <ScheduleOutlined />, label: "刷课任务" },
  { key: "/questions", icon: <QuestionCircleOutlined />, label: "题库管理" },
];

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const dropdownItems = {
    items: [
      { key: "logout", icon: <LogoutOutlined />, label: "退出登录", danger: true },
    ],
    onClick: ({ key }: { key: string }) => {
      if (key === "logout") handleLogout();
    },
  };

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="dark"
        breakpoint="lg"
        style={{ position: "fixed", left: 0, top: 0, bottom: 0, zIndex: 100 }}
      >
        <div
          style={{
            height: 48,
            margin: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <PlayCircleOutlined style={{ fontSize: collapsed ? 20 : 24, color: "#1677ff" }} />
          {!collapsed && (
            <Typography.Text strong style={{ color: "#fff", marginLeft: 8, fontSize: 16 }}>
              OnlineCourse
            </Typography.Text>
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname.split("/")[1] ? `/${location.pathname.split("/")[1]}` : "/dashboard"]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>

      <AntLayout style={{ marginLeft: collapsed ? 80 : 200, transition: "all 0.2s" }}>
        <Header
          style={{
            padding: "0 24px",
            background: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
            position: "sticky",
            top: 0,
            zIndex: 99,
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: 16 }}
          />
          <Dropdown menu={dropdownItems} placement="bottomRight">
            <div style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
              <Avatar icon={<UserOutlined />} />
              <span>{user?.username || "用户"}</span>
            </div>
          </Dropdown>
        </Header>

        <Content style={{ margin: 24, padding: 24, background: "#fff", borderRadius: 8, minHeight: 280 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
