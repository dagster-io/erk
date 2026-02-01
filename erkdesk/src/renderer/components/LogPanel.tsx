import React, { useEffect, useRef } from "react";
import "./LogPanel.css";

export interface LogLine {
  stream: "stdout" | "stderr";
  text: string;
}

export interface LogPanelProps {
  lines: LogLine[];
  status: "running" | "success" | "error";
  onDismiss: () => void;
}

export const LogPanel: React.FC<LogPanelProps> = ({
  lines,
  status,
  onDismiss,
}) => {
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [lines]);

  const statusLabel =
    status === "running"
      ? "Running..."
      : status === "success"
        ? "Success"
        : "Error";

  return (
    <div className="log-panel">
      <div className="log-panel__header">
        <span className={`log-panel__status log-panel__status--${status}`}>
          {statusLabel}
        </span>
        <button
          className="log-panel__dismiss"
          onClick={onDismiss}
          aria-label="Dismiss log panel"
        >
          ×
        </button>
      </div>
      <div className="log-panel__content" ref={contentRef}>
        {lines.map((line, index) => (
          <div
            key={index}
            className={`log-panel__line log-panel__line--${line.stream}`}
          >
            {line.text}
          </div>
        ))}
      </div>
    </div>
  );
};
