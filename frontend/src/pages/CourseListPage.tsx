import { useState } from "react";
import {
  Table,
  Button,
  Modal,
  Select,
  Progress,
  Tag,
  Space,
  App,
  Typography,
} from "antd";
import { SyncOutlined, EyeOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCoursesApi, syncCoursesApi, type Course } from "../api/courses";
import { getAccountsApi, type PlatformAccount } from "../api/accounts";

const { Title } = Typography;

const PLATFORM_LABELS: Record<string, string> = {
  icve: "智慧职教",
  zhihuishu: "知到",
  xuetangx: "学堂在线",
};

const STATUS_MAP: Record<string, { color: string; text: string }> = {
  not_started: { color: "default", text: "未开始" },
  in_progress: { color: "processing", text: "进行中" },
  completed: { color: "success", text: "已完成" },
};

export default function CourseListPage() {
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<string>("");
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const { data: coursesData, isLoading } = useQuery({
    queryKey: ["courses"],
    queryFn: () => getCoursesApi(),
  });

  const { data: accountsData } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => getAccountsApi(),
  });

  const syncMutation = useMutation({
    mutationFn: syncCoursesApi,
    onSuccess: (data) => {
      message.success(`同步完成，共获取 ${data.total} 门课程`);
      setSyncModalOpen(false);
      setSelectedAccount("");
      queryClient.invalidateQueries({ queryKey: ["courses"] });
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || "同步失败");
    },
  });

  const handleSync = () => {
    if (!selectedAccount) {
      message.warning("请选择平台账号");
      return;
    }
    syncMutation.mutate(selectedAccount);
  };

  const columns = [
    {
      title: "平台",
      dataIndex: "platform",
      key: "platform",
      width: 100,
      render: (platform: string) => (
        <Tag>{PLATFORM_LABELS[platform] || platform}</Tag>
      ),
    },
    {
      title: "课程名称",
      dataIndex: "name",
      key: "name",
      ellipsis: true,
    },
    {
      title: "授课教师",
      dataIndex: "teacher",
      key: "teacher",
      width: 120,
    },
    {
      title: "进度",
      key: "progress",
      width: 200,
      render: (_: any, record: Course) => (
        <Space direction="vertical" size={0} style={{ width: "100%" }}>
          <Progress percent={Math.round(record.progress)} size="small" />
          <span style={{ fontSize: 12, color: "#999" }}>
            {record.completed_sections}/{record.total_sections} 节
          </span>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 80,
      render: (status: string) => {
        const s = STATUS_MAP[status] || { color: "default", text: status };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      title: "操作",
      key: "actions",
      width: 80,
      render: () => (
        <Button type="link" icon={<EyeOutlined />}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          课程管理
        </Title>
        <Button
          type="primary"
          icon={<SyncOutlined />}
          onClick={() => setSyncModalOpen(true)}
        >
          同步课程
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={coursesData?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          total: coursesData?.total || 0,
          pageSize: 20,
          showTotal: (total) => `共 ${total} 门课程`,
        }}
        locale={{ emptyText: "暂无课程，请先同步" }}
      />

      <Modal
        title="同步课程"
        open={syncModalOpen}
        onOk={handleSync}
        onCancel={() => {
          setSyncModalOpen(false);
          setSelectedAccount("");
        }}
        confirmLoading={syncMutation.isPending}
      >
        <div style={{ marginTop: 16 }}>
          <p style={{ marginBottom: 12, color: "#666" }}>
            选择平台账号，系统将自动从对应平台拉取课程列表
          </p>
          <Select
            placeholder="选择平台账号"
            style={{ width: "100%" }}
            value={selectedAccount || undefined}
            onChange={setSelectedAccount}
            options={(accountsData?.items || []).map((a: PlatformAccount) => ({
              value: a.id,
              label: `[${PLATFORM_LABELS[a.platform] || a.platform}] ${a.account_name}`,
            }))}
            notFoundContent="暂无账号，请先在「平台账号」中添加"
          />
        </div>
      </Modal>
    </div>
  );
}
