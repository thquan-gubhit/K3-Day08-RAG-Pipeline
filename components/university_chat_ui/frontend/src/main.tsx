import React from "react";
import ReactDOM from "react-dom/client";
import { withStreamlitConnection } from "streamlit-component-lib";

import App from "./App";
import "./index.css";

/**
 * `withStreamlitConnection` lo phần bắt tay với Streamlit: nhận `args` từ
 * Python và cung cấp `Streamlit.setComponentValue` để gửi sự kiện ngược lại.
 */
const ConnectedApp = withStreamlitConnection(App);

/** Chặn mọi lỗi render để iframe không bao giờ trắng — Streamlit vẫn chạy tiếp. */
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[university_chat_ui] lỗi render:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            padding: "16px",
            borderRadius: "14px",
            border: "1px solid rgba(251,113,133,.4)",
            background: "rgba(16,30,49,.78)",
            color: "#F8FAFC",
            fontFamily: "system-ui, sans-serif",
            fontSize: "13px",
          }}
          role="alert"
        >
          <strong>Giao diện nâng cao gặp lỗi hiển thị.</strong>
          <p style={{ color: "#94A3B8", marginTop: 6 }}>
            Hãy chuyển sang giao diện Streamlit native trong thanh bên (mục “Giao diện” → “native”),
            hoặc build lại frontend bằng <code>npm run build</code>. Chi tiết lỗi nằm trong console
            của trình duyệt.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ConnectedApp />
    </ErrorBoundary>
  </React.StrictMode>,
);
