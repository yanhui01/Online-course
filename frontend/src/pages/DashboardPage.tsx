import { Card, Row, Col, Statistic, Typography } from "antd";
import {
  BookOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
} from "@ant-design/icons";

const { Title } = Typography;

export default function DashboardPage() {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        数据概览
      </Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平台账号"
              value={0}
              prefix={<BookOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="课程总数"
              value={0}
              prefix={<PlayCircleOutlined />}
              suffix="门"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="进行中任务"
              value={0}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: "#faad14" }}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="已完成任务"
              value={0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: "#52c41a" }}
              suffix="个"
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 24 }}>
        <Title level={4}>欢迎使用 OnlineCourse</Title>
        <p style={{ color: "#666", lineHeight: 2 }}>
          OnlineCourse 是一个多平台网课助手，支持以下平台：
        </p>
        <ul style={{ color: "#666", lineHeight: 2, paddingLeft: 20 }}>
          <li><strong>智慧职教</strong> (icve.com.cn) — 职业教育教学资源平台</li>
          <li><strong>知到 / 智慧树</strong> (zhihuishu.com) — 全球最大的学分课程服务平台</li>
          <li><strong>学堂在线</strong> (xuetangx.com) — 清华大学发起的精品中文慕课平台</li>
        </ul>
        <p style={{ color: "#999", marginTop: 16 }}>
          请先在「平台账号」中添加账号，然后在「课程管理」中同步课程，最后在「刷课任务」中创建自动任务。
        </p>
      </Card>
    </div>
  );
}
