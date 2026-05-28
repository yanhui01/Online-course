import { useState } from "react";
import {
  Table,
  Button,
  Modal,
  Select,
  InputNumber,
  Progress,
  Tag,
  Space,
  App,
  Typography,
  Popconfirm,
} from "antd";
import {
  PlusOutlined,
  PauseCircleOutlined,
  CaretRightOutlined,
  StopOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getTasksApi,
  createTaskApi,
  pauseTaskApi,
  resumeTaskApi,
  cancelTaskApi,
  type Task,
} from "../api/tasks";
import { getCoursesApi, type Course } from "../api/courses";
import { getAccountsApi, type PlatformAccount } from "../api/accounts";

const { Title } = Typography;

const STATUS_MAP: Record<string, { color: string; text: string }> = {
  pending: { color: "processing", text: "等待中" },
  running: { color: "processing", text: "运行中" },
  paused: { color: "warning", text: "已暂停" },
  completed: { color: "success", text: "已完成" },
  failed: { color: "error", text: "失败" },
  cancelled: { color: "default", text: "已取消" },
  needs_manual: { color: "warning", text: "需手动" },
};

export default function TaskListPage() {
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState<string>("");
  const [selectedAccount, setSelectedAccount] = useState<string>("");
  const [maxRetries, setMaxRetries] = useState(3);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const { data: tasksData, isLoading } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => getTasksApi(),
    refetchInterval: 5000,  // 每5秒刷新
  });

  const { data: coursesData } = useQuery({
    queryKey: ["courses"],
    queryFn: () => getCoursesApi(),
  });

  const { data: accountsData } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => getAccountsApi(),
  });

  const createMutation = useMutation({
    mutationFn: createTaskApi,
    onSuccess: () => {
      message.success("任务创建成功");
      setCreateModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (err: any) => message.error(err.response?.data?.detail || "创建失败"),
  });

  const pauseMutation = useMutation({
    mutationFn: pauseTaskApi,
    onSuccess: () => {
      message.success("任务已暂停");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: resumeTaskApi,
    onSuccess: () => {
      message.success("任务已恢复");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: cancelTaskApi,
    onSuccess: () => {
      message.success("任务已取消");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const columns = [
    {
      title: "平台",
      dataIndex: "platform",
      key: "platform",
      width: 80,
      render: (p: string) => <Tag>{p}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 80,
      render: (s: string) => {
        const st = STATUS_MAP[s] || { color: "default", text: s };
        return <Tag color={st.color}>{st.text}</Tag>;
      },
    },
    {
      title: "进度",
      key: "progress",
      width: 200,
      render: (_: any, record: Task) => (
        <Progress
          percent={Math.round(record.progress)}
          size="small"
          status={record.status === "failed" ? "exception" : undefined}
        />
      ),
    },
    {
      title: "章节",
      key: "sections",
      width: 100,
      render: (_: any, record: Task) =>
        `${record.completed_sections}/${record.total_sections}`,
    },
    {
      title: "重试",
      dataIndex: "retry_count",
      key: "retry",
      width: 60,
      render: (c: number, r: Task) => `${c}/${r.max_retries}`,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
    },
    {
      title: "操作",
      key: "actions",
      width: 200,
      render: (_: any, record: Task) => (
        <Space size={0}>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/tasks/${record.id}`)}
          >
            详情
          </Button>
          {record.status === "running" && (
            <Popconfirm title="暂停任务？" onConfirm={() => pauseMutation.mutate(record.id)}>
              <Button type="link" size="small" icon={<PauseCircleOutlined />}>
                暂停
              </Button>
            </Popconfirm>
          )}
          {record.status === "paused" && (
            <Popconfirm title="恢复任务？" onConfirm={() => resumeMutation.mutate(record.id)}>
              <Button type="link" size="small" icon={<CaretRightOutlined />}>
                恢复
              </Button>
            </Popconfirm>
          )}
          {["pending", "running", "paused", "failed"].includes(record.status) && (
            <Popconfirm title="取消任务？" onConfirm={() => cancelMutation.mutate(record.id)}>
              <Button type="link" size="small" danger icon={<StopOutlined />}>
                取消
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          刷课任务
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalOpen(true)}
        >
          创建任务
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={tasksData?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          total: tasksData?.total || 0,
          pageSize: 20,
          showTotal: (total) => `共 ${total} 个任务`,
        }}
        locale={{ emptyText: "暂无任务" }}
      />

      <Modal
        title="创建刷课任务"
        open={createModalOpen}
        onOk={() => {
          if (!selectedCourse || !selectedAccount) {
            message.warning("请选择课程和账号");
            return;
          }
          createMutation.mutate({
            course_id: selectedCourse,
            account_id: selectedAccount,
            max_retries: maxRetries,
          });
        }}
        onCancel={() => setCreateModalOpen(false)}
        confirmLoading={createMutation.isPending}
      >
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", marginBottom: 4 }}>选择课程</label>
            <Select
              placeholder="选择要刷的课程"
              style={{ width: "100%" }}
              value={selectedCourse || undefined}
              onChange={setSelectedCourse}
              options={(coursesData?.items || []).map((c: Course) => ({
                value: c.id,
                label: c.name,
              }))}
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4 }}>选择平台账号</label>
            <Select
              placeholder="选择用于登录的账号"
              style={{ width: "100%" }}
              value={selectedAccount || undefined}
              onChange={setSelectedAccount}
              options={(accountsData?.items || []).map((a: PlatformAccount) => ({
                value: a.id,
                label: `[${a.platform}] ${a.account_name}`,
              }))}
            />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4 }}>最大重试次数</label>
            <InputNumber
              min={1}
              max={10}
              value={maxRetries}
              onChange={(v) => setMaxRetries(v || 3)}
              style={{ width: "100%" }}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
