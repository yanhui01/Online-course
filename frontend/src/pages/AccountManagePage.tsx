import { useState } from "react";
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Popconfirm,
  App,
  Typography,
  Radio,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, PhoneOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getAccountsApi,
  createAccountApi,
  updateAccountApi,
  deleteAccountApi,
  sendSmsApi,
  verifySmsApi,
  type PlatformAccount,
  type CreateAccountParams,
} from "../api/accounts";

const { Title } = Typography;

const PLATFORM_OPTIONS = [
  { value: "icve", label: "智慧职教 (icve)" },
  { value: "zhihuishu", label: "知到/智慧树 (zhihuishu)" },
  { value: "xuetangx", label: "学堂在线 (xuetangx)" },
];

const PLATFORM_COLORS: Record<string, string> = {
  icve: "blue",
  zhihuishu: "green",
  xuetangx: "purple",
};

const LOGIN_TYPE_LABELS: Record<string, string> = {
  password: "密码登录",
  sms: "短信验证码",
};

export default function AccountManagePage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<PlatformAccount | null>(null);
  const [smsModalOpen, setSmsModalOpen] = useState(false);
  const [smsAccountId, setSmsAccountId] = useState<string>("");
  const [smsCode, setSmsCode] = useState("");
  const [smsSent, setSmsSent] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const { data, isLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => getAccountsApi(),
  });

  const createMutation = useMutation({
    mutationFn: createAccountApi,
    onSuccess: (data: PlatformAccount, variables: CreateAccountParams) => {
      setModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      // SMS 模式自动弹出验证码对话框
      if (variables.login_type === "sms") {
        message.info("账号已添加，请验证手机号");
        setSmsAccountId(data.id);
        setSmsCode("");
        setSmsSent(false);
        setSmsModalOpen(true);
      } else {
        message.success("添加成功");
      }
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || "添加失败");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...params }: { id: string } & Partial<CreateAccountParams>) =>
      updateAccountApi(id, params),
    onSuccess: () => {
      message.success("更新成功");
      setModalOpen(false);
      setEditingAccount(null);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || "更新失败");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAccountApi,
    onSuccess: () => {
      message.success("删除成功");
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || "删除失败");
    },
  });

  const sendSmsMutation = useMutation({
    mutationFn: sendSmsApi,
    onSuccess: () => {
      message.success("验证码已发送，请查收短信");
      setSmsSent(true);
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || "发送失败");
    },
  });

  const verifySmsMutation = useMutation({
    mutationFn: ({ id, code }: { id: string; code: string }) => verifySmsApi(id, code),
    onSuccess: () => {
      message.success("验证成功，账号已激活");
      setSmsModalOpen(false);
      setSmsCode("");
      setSmsSent(false);
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || "验证失败");
    },
  });

  const handleAdd = () => {
    setEditingAccount(null);
    form.resetFields();
    form.setFieldsValue({ login_type: "password" });
    setModalOpen(true);
  };

  const handleEdit = (record: PlatformAccount) => {
    setEditingAccount(record);
    form.setFieldsValue({
      platform: record.platform,
      login_type: record.login_type,
      account_name: record.account_name,
      password: "",
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    if (editingAccount) {
      updateMutation.mutate({
        id: editingAccount.id,
        ...values,
        password: values.password || undefined,
      });
    } else {
      createMutation.mutate(values);
    }
  };

  const handleOpenSms = (record: PlatformAccount) => {
    setSmsAccountId(record.id);
    setSmsCode("");
    setSmsSent(false);
    setSmsModalOpen(true);
    // 自动触发发送验证码
    sendSmsMutation.mutate(record.id);
  };

  const loginTypeValue = Form.useWatch("login_type", form);
  const platformValue = Form.useWatch("platform", form);
  const showSmsOption = platformValue === "xuetangx" || editingAccount?.platform === "xuetangx";

  const columns = [
    {
      title: "平台",
      dataIndex: "platform",
      key: "platform",
      render: (platform: string) => (
        <Tag color={PLATFORM_COLORS[platform]}>
          {PLATFORM_OPTIONS.find((p) => p.value === platform)?.label || platform}
        </Tag>
      ),
    },
    {
      title: "登录方式",
      dataIndex: "login_type",
      key: "login_type",
      width: 110,
      render: (t: string) => (
        <Tag color={t === "sms" ? "orange" : "blue"}>{LOGIN_TYPE_LABELS[t] || t}</Tag>
      ),
    },
    {
      title: "账号",
      dataIndex: "account_name",
      key: "account_name",
    },
    {
      title: "状态",
      dataIndex: "is_valid",
      key: "is_valid",
      render: (valid: boolean) =>
        valid ? <Tag color="success">有效</Tag> : <Tag color="error">待验证</Tag>,
    },
    {
      title: "最后登录",
      dataIndex: "last_login_at",
      key: "last_login_at",
      render: (v: string | null) => v || "-",
    },
    {
      title: "操作",
      key: "actions",
      render: (_: any, record: PlatformAccount) => (
        <Space>
          {record.platform === "xuetangx" && record.login_type === "sms" && (
            <Button
              type="link"
              icon={<PhoneOutlined />}
              onClick={() => handleOpenSms(record)}
            >
              验证
            </Button>
          )}
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定删除该账号？"
            onConfirm={() => deleteMutation.mutate(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          平台账号管理
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加账号
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          total: data?.total || 0,
          pageSize: 20,
          showTotal: (total) => `共 ${total} 个账号`,
        }}
      />

      {/* 添加/编辑账号弹窗 */}
      <Modal
        title={editingAccount ? "编辑账号" : "添加账号"}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => {
          setModalOpen(false);
          setEditingAccount(null);
        }}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="platform"
            label="平台"
            rules={[{ required: true, message: "请选择平台" }]}
          >
            <Select options={PLATFORM_OPTIONS} placeholder="选择平台" disabled={!!editingAccount} />
          </Form.Item>

          {showSmsOption && (
            <Form.Item name="login_type" label="登录方式">
              <Radio.Group disabled={!!editingAccount}>
                <Radio.Button value="password">密码登录</Radio.Button>
                <Radio.Button value="sms">短信验证码</Radio.Button>
              </Radio.Group>
            </Form.Item>
          )}

          <Form.Item
            name="account_name"
            label={loginTypeValue === "sms" ? "手机号" : "账号"}
            rules={[{ required: true, message: loginTypeValue === "sms" ? "请输入手机号" : "请输入账号" }]}
          >
            <Input placeholder={loginTypeValue === "sms" ? "输入接收验证码的手机号" : "手机号/学号/邮箱"} />
          </Form.Item>

          {(!showSmsOption || loginTypeValue === "password") && (
            <Form.Item
              name="password"
              label="密码"
              rules={[
                {
                  required: !editingAccount && loginTypeValue !== "sms",
                  message: "请输入密码",
                },
              ]}
            >
              <Input.Password placeholder={editingAccount ? "留空则不修改" : "平台登录密码"} />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* 短信验证弹窗 */}
      <Modal
        title="手机验证码登录"
        open={smsModalOpen}
        onOk={() => {
          if (!smsCode) {
            message.warning("请输入验证码");
            return;
          }
          verifySmsMutation.mutate({ id: smsAccountId, code: smsCode });
        }}
        onCancel={() => {
          setSmsModalOpen(false);
          setSmsCode("");
          setSmsSent(false);
        }}
        confirmLoading={verifySmsMutation.isPending}
        okText="验证登录"
      >
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 16 }}>
          <p style={{ color: "#666" }}>
            点击下方按钮，系统将通过学堂在线发送短信验证码到您绑定的手机号
          </p>
          <Button
            type="primary"
            ghost
            icon={<PhoneOutlined />}
            loading={sendSmsMutation.isPending}
            disabled={smsSent}
            onClick={() => sendSmsMutation.mutate(smsAccountId)}
            block
          >
            {smsSent ? "验证码已发送" : "发送验证码"}
          </Button>
          {smsSent && (
            <Input
              size="large"
              placeholder="输入短信验证码"
              value={smsCode}
              onChange={(e) => setSmsCode(e.target.value)}
              maxLength={6}
              style={{ textAlign: "center", letterSpacing: 4 }}
            />
          )}
        </div>
      </Modal>
    </div>
  );
}
