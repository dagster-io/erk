import React, { useCallback, useEffect, useRef, useState } from "react";

interface SplitPaneProps {
  leftPane: React.ReactNode;
  minLeftWidth?: number;
  minRightWidth?: number;
  defaultLeftWidth?: number;
}

const DIVIDER_WIDTH = 4;

const SplitPane: React.FC<SplitPaneProps> = ({
  leftPane,
  minLeftWidth = 200,
  minRightWidth = 400,
  defaultLeftWidth = 300,
}) => {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const rightPaneRef = useRef<HTMLDivElement>(null);

  const reportBounds = useCallback(() => {
    const el = rightPaneRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    window.erkdesk.updateWebViewBounds({
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
    });
  }, []);

  // Report bounds on mount, leftWidth change, and window resize.
  useEffect(() => {
    reportBounds();
  }, [leftWidth, reportBounds]);

  useEffect(() => {
    window.addEventListener("resize", reportBounds);
    return () => window.removeEventListener("resize", reportBounds);
  }, [reportBounds]);

  // ResizeObserver to detect when right pane size changes (e.g., log panel appears).
  useEffect(() => {
    const el = rightPaneRef.current;
    if (!el) return;

    const observer = new ResizeObserver(() => {
      reportBounds();
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, [reportBounds]);

  // Divider drag handling.
  useEffect(() => {
    if (!isDragging) return;

    const onMouseMove = (e: MouseEvent) => {
      const container = containerRef.current;
      if (!container) return;
      const containerRect = container.getBoundingClientRect();
      const maxLeft = containerRect.width - DIVIDER_WIDTH - minRightWidth;
      const newLeft = e.clientX - containerRect.left;
      setLeftWidth(Math.max(minLeftWidth, Math.min(maxLeft, newLeft)));
    };

    const onMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, [isDragging, minLeftWidth, minRightWidth]);

  return (
    <div
      ref={containerRef}
      style={{
        display: "flex",
        width: "100%",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Left pane */}
      <div
        style={{
          width: leftWidth,
          minWidth: minLeftWidth,
          flexShrink: 0,
          overflow: "auto",
        }}
      >
        {leftPane}
      </div>

      {/* Divider */}
      <div
        onMouseDown={() => setIsDragging(true)}
        style={{
          width: DIVIDER_WIDTH,
          cursor: "col-resize",
          backgroundColor: isDragging ? "#999" : "#ccc",
          flexShrink: 0,
          userSelect: "none",
        }}
      />

      {/* Right pane placeholder — WebContentsView overlays this */}
      <div
        ref={rightPaneRef}
        style={{
          flex: 1,
          minWidth: minRightWidth,
        }}
      />
    </div>
  );
};

export default SplitPane;
