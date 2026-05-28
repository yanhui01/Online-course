import { useState, useEffect, useRef } from "react";
import { Modal, Button, Spin, Result, App, Typography } from "antd";
import { ScanOutlined, LoadingOutlined } from "@ant-design/icons";
import client from "../api/client";

const { Text } = Typography;

interface Props {
  open: boolean;
  accountId: string;
  platform: string;
  accountName: string;
  onSuccess: () => void;
  onCancel: () => void;
}

export default function QrcodeLoginModal({
  open, accountId, platform, accountName, onSuccess, onCancel,
}: Props) {
  const [qrcode, setQrcode] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "scanning" | "success" | "error" | "timeout">("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const { message } = App.useApp();
  const pollingRef = useRef<boolean>(false);

  useEffect(() => {
    if (!open || !accountId) return;

    let cancelled = false;
    setStatus("loading");
    setQrcode(null);
    pollingRef.current = false;

    const startQrLogin = async () => {
      try {
        // 1. 获取二维码
        const qrRes = await client.post("/qrcode/get", { account_id: accountId });
        if (cancelled) return;

        const qrData = qrRes.data.qrcode;
        // 如果是 URL，直接用；如果是 base64，构建 data URI
        if (qrData.startsWith("http")) {
          setQrcode(qrData);
        } else {
          setQrcode(`data:image/png;base64,${qrData}`);
        }
        setStatus("scanning");
        pollingRef.current = true;

        // 2. 轮询等待扫码
        const waitRes = await client.post("/qrcode/wait", {
          account_id: accountId,
          timeout: 120,
        }, { timeout: 130000 });

        if (cancelled) return;

        if (waitRes.data?.message?.includes("成功")) {
          setStatus("success");
          message.success("扫码登录成功");
          setTimeout(() => onSuccess(), 1500);
        }
      } catch (err: any) {
        if (cancelled) return;
        const detail = err.response?.data?.detail || "";
        if (detail.includes("超时")) {
          setStatus("timeout");
          setErrorMsg("扫码超时，请重试");
        } else if (detail.includes("不支持")) {
          setStatus("error");
          setErrorMsg(detail);
        } else {
          setStatus("error");
          setErrorMsg(detail || "扫码失败");
        }
      }
    };

    startQrLogin();
    return () => { cancelled = true; };
  }, [open, accountId]);

  const handleRetry = () => {
    setStatus("loading");
    setQrcode(null);
    setErrorMsg("");
    // 重新触发 effect
    const event = new CustomEvent("retry-qrcode");
    window.dispatchEvent(event);
  };

  return (
    <Modal
      title={`${platform === "xuetangx" ? "学堂在线" : platform === "zhihuishu" ? "知到" : "智慧职教"} - 扫码登录`}
      open={open}
      onCancel={onCancel}
      footer={null}
      width={420}
      destroyOnClose
    >
      <div style={{ textAlign: "center", padding: "20px 0" }}>
        {status === "loading" && (
          <div>
            <Spin size="large" />
            <p style={{ marginTop: 16, color: "#999" }}>正在获取二维码...</p>
          </div>
        )}

        {status === "scanning" && qrcode && (
          <div>
            <img
              src={qrcode}
              alt="登录二维码"
              style={{ width: 240, height: 240, border: "1px solid #eee", borderRadius: 8 }}
            />
            <p style={{ marginTop: 16 }}>
              <ScanOutlined style={{ fontSize: 20, color: "#1677ff", marginRight: 8 }} />
              <Text strong>请使用对应平台 APP 扫描二维码</Text>
            </p>
            <p style={{ color: "#999", fontSize: 13 }}>
              账号: {accountName}
            </p>
            <div style={{ marginTop: 12 }}>
              <LoadingOutlined spin style={{ color: "#1677ff" }} />
              <span style={{ marginLeft: 8, color: "#999" }}>等待扫码中...</span>
            </div>
          </div>
        )}

        {status === "success" && (
          <Result status="success" title="登录成功" subTitle="即将同步课程..." />
        )}

        {(status === "error" || status === "timeout") && (
          <Result
            status={status === "timeout" ? "warning" : "error"}
            title={status === "timeout" ? "扫码超时" : "获取失败"}
            subTitle={errorMsg}
            extra={
              <Button type="primary" onClick={() => {
                setStatus("loading");
                setQrcode(null);
                setErrorMsg("");
                // 关闭再重新打开触发
                onCancel();
                setTimeout(() => {
                  const retryEvent = new Event("retry-qrcode");
                  window.dispatchEvent(retryEvent);
                }, 500);
              }}>
                重试
              </Button>
            }
          />
        )}
      </div>
    </Modal>
  );
}
