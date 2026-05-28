import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import AccountManagePage from "./pages/AccountManagePage";
import CourseListPage from "./pages/CourseListPage";
import TaskListPage from "./pages/TaskListPage";
import TaskDetailPage from "./pages/TaskDetailPage";
import QuestionBankPage from "./pages/QuestionBankPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="accounts" element={<AccountManagePage />} />
        <Route path="courses" element={<CourseListPage />} />
        <Route path="tasks" element={<TaskListPage />} />
        <Route path="tasks/:taskId" element={<TaskDetailPage />} />
        <Route path="questions" element={<QuestionBankPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
