import React from "react";
import "./StatusIndicator.css";

export type StatusColor = "green" | "amber" | "purple" | "red" | "gray";

export interface StatusIndicatorProps {
  color: StatusColor;
  text: string;
  tooltip?: string;
}

export function StatusIndicator({
  color,
  text,
  tooltip,
}: StatusIndicatorProps): React.ReactElement {
  return (
    <span className="status-indicator" title={tooltip}>
      <span className={`status-indicator__dot status-indicator__dot--${color}`} />
      <span className="status-indicator__text">{text}</span>
    </span>
  );
}
