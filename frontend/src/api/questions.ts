import client from "./client";

export interface Question {
  id: string;
  platform: string | null;
  course_name: string | null;
  question_text: string;
  question_type: string;
  options: string[] | null;
  correct_answer: string;
  source: string;
  confidence: number;
  hit_count: number;
  created_at: string;
}

export interface QuestionSearchResult {
  found: boolean;
  question_id: string | null;
  correct_answer: string | null;
  confidence: number;
  similar_questions: Question[];
}

export interface PendingQuestion {
  id: string;
  task_id: string;
  platform: string;
  course_name: string | null;
  question_text: string;
  question_type: string | null;
  options: string[] | null;
  status: string;
  created_at: string;
}

export interface CreateQuestionParams {
  platform?: string;
  course_name?: string;
  question_text: string;
  question_type: string;
  options?: string[];
  correct_answer: string;
}

export async function searchQuestionApi(q: string) {
  const res = await client.get("/questions/search", { params: { q } });
  return res.data as QuestionSearchResult;
}

export async function getQuestionsApi(page = 1, pageSize = 20, platform?: string) {
  const res = await client.get("/questions", { params: { page, page_size: pageSize, platform } });
  return res.data;
}

export async function addQuestionApi(params: CreateQuestionParams) {
  const res = await client.post("/questions", params);
  return res.data;
}

export async function deleteQuestionApi(id: string) {
  const res = await client.delete(`/questions/${id}`);
  return res.data;
}

export async function getPendingQuestionsApi(page = 1, pageSize = 20) {
  const res = await client.get("/questions/pending", { params: { page, page_size: pageSize } });
  return res.data;
}

export async function answerPendingApi(pendingId: string, correctAnswer: string) {
  const res = await client.post(`/questions/pending/${pendingId}/answer`, null, {
    params: { correct_answer: correctAnswer },
  });
  return res.data;
}
