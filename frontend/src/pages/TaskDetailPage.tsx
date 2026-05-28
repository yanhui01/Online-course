import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Progress,
  Tag,
  Descriptions,
  Timeline,
  Button,
  Space,
  App,
  Typography,
  Spin,
} from "antd";
import {
  ArrowLeftOutlined,
  PauseCircleOutlined,
  CaretRightOutlined,
  StopOutlined,
} from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getTaskDetailApi,
  pauseTaskApi,
  resumeTaskApi,
  cancelTaskApi,
  type TaskDetail,
  type TaskLog,
} from "../api/tasks";

const { Title } = Typography;

const LEVEL_COLORS: Record<string, string> = {
  INFO: "blue",
  WARNING: "orange",
  ERROR: "red",
  DEBUG: "default",
};

const STATUS_MAP: Record<string, { color: string; text: string }> = {
  pending: { color: "processing", text: "等待中" },
  running: { color: "processing", text: "运行中" },
  paused: { color: "warning", text: "已暂停" },
  completed: { color: "success", text: "已完成" },
  failed: { color: "error", text: "失败" },
  cancelled: { color: "default", text: "已取消" },
};

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const logEndRef = useRef<HTMLDivElement>(null);

  const { data: task, isLoading } = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => getTaskDetailApi(taskId!),
    enabled: !!taskId,
    refetchInterval: 3000,
  });

  const pauseMutation = useMutation({
    mutationFn: () => pauseTaskApi(taskId!),
    onSuccess: () => {
      message.success("已暂停");
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => resumeTaskApi(taskId!),
    onSuccess: () => {
      message.success("已恢复");
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelTaskApi(taskId!),
    onSuccess: () => {
      message.success("已取消");
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    },
  });

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [task?.logs]);

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!task) return <div>任务不存在</div>;

  const statusInfo = STATUS_MAP[task.status] || { color: "default", text: task.status };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/tasks")}>
          返回
        </Button>
        <Title level={3} style={{ margin: 0 }}>
          任务详情
        </Title>
        <Tag color={statusInfo.color}>{statusInfo.text}</Tag>
      </div>

      <Space style={{ marginBottom: 16 }}>
        {task.status === "running" && (
          <Button icon={<PauseCircleOutlined />} onClick={() => pauseMutation.mutate()}>
            暂停
          </Button>
        )}
        {task.status === "paused" && (
          <Button icon={<CaretRightOutlined />} onClick={() => resumeMutation.mutate()}>
            恢复
          </Button>
        )}
        {["pending", "running", "paused", "failed"].includes(task.status) && (
          <Button danger icon={<StopOutlined />} onClick={() => cancelMutation.mutate()}>
            取消
          </Button>
        )}
      </Space>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small">
          <Descriptions.Item label="任务 ID">{task.id}</Descriptions.Item>
          <Descriptions.Item label="平台">{task.platform}</Descriptions.Item>
          <Descriptions.Item label="进度">
            <Progress percent={Math.round(task.progress)} size="small" style={{ width: 200 }} />
          </Descriptions.Item>
          <Descriptions.Item label="章节">
            {task.completed_sections} / {task.total_sections}
          </Descriptions.Item>
          <Descriptions.Item label="重试">
            {task.retry_count} / {task.max_retries}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{task.created_at}</Descriptions.Item>
          {task.error_message && (
            <Descriptions.Item label="错误信息" span={3}>
              <Tag color="red">{task.error_message}</Tag>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title="执行日志" style={{ maxHeight: 500, overflow: "auto" }}>
        {task.logs.length === 0 ? (
          <div style={{ textAlign: "center", color: "#999", padding: 20 }}>暂无日志</div>
        ) : (
          <Timeline
            items={(task.logs as TaskLog[]).map((log) => ({
              color: LEVEL_COLORS[log.level] || "gray",
              children: (
                <div>
                  <Tag>{log.level}</Tag>
                  <span style={{ color: "#666", fontSize: 12 }}>
                    {new Date(log.created_at).toLocaleTimeString()}
                  </span>
                  <div>{log.message}</div>
                </div>
              ),
            }))}
          />
        )}
        <div ref={logEndRef} />
      </Card>
    </div>
  );
}
