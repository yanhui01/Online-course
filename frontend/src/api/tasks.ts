import client from "./client";

export interface TaskLog {
  id: string;
  level: string;
  section_id: string | null;
  message: string;
  screenshot_path: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  course_id: string;
  account_id: string;
  platform: string;
  status: string;
  total_sections: number;
  completed_sections: number;
  progress: number;
  current_section_id: string | null;
  error_message: string | null;
  retry_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskDetail extends Task {
  logs: TaskLog[];
}

export interface CreateTaskParams {
  course_id: string;
  account_id: string;
  max_retries?: number;
}

export async function getTasksApi(page = 1, pageSize = 20) {
  const res = await client.get("/tasks", { params: { page, page_size: pageSize } });
  return res.data;
}

export async function getTaskDetailApi(taskId: string) {
  const res = await client.get(`/tasks/${taskId}`);
  return res.data as TaskDetail;
}

export async function createTaskApi(params: CreateTaskParams) {
  const res = await client.post("/tasks", params);
  return res.data;
}

export async function pauseTaskApi(taskId: string) {
  const res = await client.post(`/tasks/${taskId}/pause`);
  return res.data;
}

export async function resumeTaskApi(taskId: string) {
  const res = await client.post(`/tasks/${taskId}/resume`);
  return res.data;
}

export async function cancelTaskApi(taskId: string) {
  const res = await client.post(`/tasks/${taskId}/cancel`);
  return res.data;
}
