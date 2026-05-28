import client from "./client";

export interface Section {
  id: string;
  platform_section_id: string;
  name: string;
  section_type: string;
  duration_minutes: number;
  sort_order: number;
  is_completed: boolean;
  completed_at: string | null;
}

export interface Course {
  id: string;
  platform: string;
  platform_course_id: string;
  name: string;
  teacher: string;
  cover_url: string;
  total_sections: number;
  completed_sections: number;
  progress: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface CourseDetail extends Course {
  sections: Section[];
}

export async function getCoursesApi(page = 1, pageSize = 20) {
  const res = await client.get("/courses", { params: { page, page_size: pageSize } });
  return res.data;
}

export async function getCourseDetailApi(courseId: string) {
  const res = await client.get(`/courses/${courseId}`);
  return res.data as CourseDetail;
}

export async function syncCoursesApi(accountId: string) {
  const res = await client.post("/courses/sync", { account_id: accountId });
  return res.data;
}
