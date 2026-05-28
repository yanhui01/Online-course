import { useState } from "react";
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Tabs,
  Tag,
  Space,
  App,
  Typography,
  Popconfirm,
} from "antd";
import { PlusOutlined, SearchOutlined, DeleteOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getQuestionsApi,
  getPendingQuestionsApi,
  addQuestionApi,
  deleteQuestionApi,
  searchQuestionApi,
  answerPendingApi,
  type Question,
  type PendingQuestion,
} from "../api/questions";

const { Title } = Typography;

const QUESTION_TYPE_LABELS: Record<string, string> = {
  single_choice: "单选题",
  multi_choice: "多选题",
  judge: "判断题",
  fill_blank: "填空题",
};

export default function QuestionBankPage() {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const [searchResult, setSearchResult] = useState<any>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const { data: questionsData, isLoading } = useQuery({
    queryKey: ["questions"],
    queryFn: () => getQuestionsApi(),
  });

  const { data: pendingData } = useQuery({
    queryKey: ["pendingQuestions"],
    queryFn: () => getPendingQuestionsApi(),
  });

  const addMutation = useMutation({
    mutationFn: addQuestionApi,
    onSuccess: () => {
      message.success("添加成功");
      setAddModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
    onError: (err: any) => message.error(err.response?.data?.detail || "添加失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteQuestionApi,
    onSuccess: () => {
      message.success("删除成功");
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });

  const answerPendingMutation = useMutation({
    mutationFn: ({ id, answer }: { id: string; answer: string }) =>
      answerPendingApi(id, answer),
    onSuccess: () => {
      message.success("已录入题库");
      queryClient.invalidateQueries({ queryKey: ["pendingQuestions"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });

  const handleSearch = async () => {
    if (!searchValue.trim()) return;
    try {
      const result = await searchQuestionApi(searchValue.trim());
      setSearchResult(result);
    } catch (err: any) {
      message.error(err.response?.data?.detail || "搜索失败");
    }
  };

  const questionColumns = [
    {
      title: "题目",
      dataIndex: "question_text",
      key: "text",
      width: 300,
      ellipsis: true,
    },
    {
      title: "类型",
      dataIndex: "question_type",
      key: "type",
      width: 80,
      render: (t: string) => QUESTION_TYPE_LABELS[t] || t,
    },
    {
      title: "平台",
      dataIndex: "platform",
      key: "platform",
      width: 80,
      render: (p: string | null) => p ? <Tag>{p}</Tag> : <Tag color="default">通用</Tag>,
    },
    {
      title: "答案",
      dataIndex: "correct_answer",
      key: "answer",
      width: 120,
      ellipsis: true,
    },
    {
      title: "命中",
      dataIndex: "hit_count",
      key: "hits",
      width: 60,
    },
    {
      title: "操作",
      key: "actions",
      width: 60,
      render: (_: any, record: Question) => (
        <Popconfirm title="确定删除？" onConfirm={() => deleteMutation.mutate(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const pendingColumns = [
    {
      title: "题目",
      dataIndex: "question_text",
      key: "text",
      ellipsis: true,
    },
    {
      title: "平台",
      dataIndex: "platform",
      key: "platform",
      width: 80,
      render: (p: string) => <Tag>{p}</Tag>,
    },
    {
      title: "操作",
      key: "actions",
      width: 200,
      render: (_: any, record: PendingQuestion) => {
        const [answer, setAnswer] = useState("");
        return (
          <Space>
            <Input
              size="small"
              placeholder="输入正确答案"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              style={{ width: 120 }}
            />
            <Button
              size="small"
              type="primary"
              disabled={!answer}
              onClick={() =>
                answerPendingMutation.mutate({ id: record.id, answer })
              }
            >
              录入
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>题库管理</Title>
        <Space>
          <Input.Search
            placeholder="搜索题目答案"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onSearch={handleSearch}
            enterButton={<SearchOutlined />}
            style={{ width: 300 }}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>
            添加题目
          </Button>
        </Space>
      </div>

      {searchResult && (
        <Card
          size="small"
          style={{ marginBottom: 16 }}
          title={`搜索结果: "${searchValue}"`}
          extra={<Button size="small" onClick={() => { setSearchResult(null); setSearchValue(""); }}>清除</Button>}
        >
          {searchResult.found ? (
            <div>
              <Tag color="success">已找到</Tag>
              答案: <strong>{searchResult.correct_answer}</strong>
              (置信度: {Math.round(searchResult.confidence * 100)}%)
            </div>
          ) : (
            <div>
              <Tag color="warning">未找到</Tag>
              {searchResult.similar_questions.length > 0 && (
                <span>找到 {searchResult.similar_questions.length} 个相似题目</span>
              )}
            </div>
          )}
        </Card>
      )}

      <Tabs
        items={[
          {
            key: "bank",
            label: `题库 (${questionsData?.total || 0})`,
            children: (
              <Table
                columns={questionColumns}
                dataSource={questionsData?.items || []}
                rowKey="id"
                loading={isLoading}
                pagination={{ pageSize: 20 }}
                size="small"
              />
            ),
          },
          {
            key: "pending",
            label: `待解答 (${pendingData?.total || 0})`,
            children: (
              <Table
                columns={pendingColumns}
                dataSource={pendingData?.items || []}
                rowKey="id"
                pagination={{ pageSize: 20 }}
                size="small"
                locale={{ emptyText: "暂无待答题" }}
              />
            ),
          },
        ]}
      />

      <Modal
        title="添加题目"
        open={addModalOpen}
        onOk={() => form.submit()}
        onCancel={() => setAddModalOpen(false)}
        confirmLoading={addMutation.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: 16 }}
          onFinish={(values) => addMutation.mutate(values)}
        >
          <Form.Item name="question_text" label="题目内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="question_type" label="题型" initialValue="single_choice">
            <Select
              options={Object.entries(QUESTION_TYPE_LABELS).map(([k, v]) => ({
                value: k,
                label: v,
              }))}
            />
          </Form.Item>
          <Form.Item name="correct_answer" label="正确答案" rules={[{ required: true }]}>
            <Input placeholder="例如: A / 对 / 具体答案内容" />
          </Form.Item>
          <Form.Item name="platform" label="平台（可选）">
            <Select
              allowClear
              placeholder="留空表示通用"
              options={[
                { value: "icve", label: "智慧职教" },
                { value: "zhihuishu", label: "知到" },
                { value: "xuetangx", label: "学堂在线" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
