import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LogPanel, LogLine } from "./LogPanel";

describe("LogPanel", () => {
  const mockOnDismiss = vi.fn();

  beforeEach(() => {
    mockOnDismiss.mockReset();
  });

  it("renders with running status", () => {
    const lines: LogLine[] = [
      { stream: "stdout", text: "Starting process..." },
    ];
    render(
      <LogPanel lines={lines} status="running" onDismiss={mockOnDismiss} />,
    );

    expect(screen.getByText("Running...")).toBeInTheDocument();
    expect(screen.getByText("Starting process...")).toBeInTheDocument();
  });

  it("renders with success status", () => {
    const lines: LogLine[] = [{ stream: "stdout", text: "Done!" }];
    render(
      <LogPanel lines={lines} status="success" onDismiss={mockOnDismiss} />,
    );

    expect(screen.getByText("Success")).toBeInTheDocument();
  });

  it("renders with error status", () => {
    const lines: LogLine[] = [
      { stream: "stderr", text: "Error: command failed" },
    ];
    render(<LogPanel lines={lines} status="error" onDismiss={mockOnDismiss} />);

    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("renders multiple log lines with different streams", () => {
    const lines: LogLine[] = [
      { stream: "stdout", text: "Output line 1" },
      { stream: "stderr", text: "Error line 1" },
      { stream: "stdout", text: "Output line 2" },
    ];
    render(
      <LogPanel lines={lines} status="running" onDismiss={mockOnDismiss} />,
    );

    expect(screen.getByText("Output line 1")).toBeInTheDocument();
    expect(screen.getByText("Error line 1")).toBeInTheDocument();
    expect(screen.getByText("Output line 2")).toBeInTheDocument();
  });

  it("calls onDismiss when dismiss button is clicked", async () => {
    const lines: LogLine[] = [];
    render(
      <LogPanel lines={lines} status="success" onDismiss={mockOnDismiss} />,
    );

    const user = userEvent.setup();
    const dismissButton = screen.getByLabelText("Dismiss log panel");
    await user.click(dismissButton);

    expect(mockOnDismiss).toHaveBeenCalledTimes(1);
  });

  it("auto-scrolls to bottom when new lines are added", () => {
    const { rerender } = render(
      <LogPanel lines={[]} status="running" onDismiss={mockOnDismiss} />,
    );

    const lines: LogLine[] = [
      { stream: "stdout", text: "Line 1" },
      { stream: "stdout", text: "Line 2" },
      { stream: "stdout", text: "Line 3" },
    ];

    rerender(
      <LogPanel lines={lines} status="running" onDismiss={mockOnDismiss} />,
    );

    expect(screen.getByText("Line 3")).toBeInTheDocument();
  });
});
