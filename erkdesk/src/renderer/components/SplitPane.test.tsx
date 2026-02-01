import { render, screen } from "@testing-library/react";
import SplitPane from "./SplitPane";

describe("SplitPane", () => {
  beforeEach(() => {
    vi.mocked(window.erkdesk.updateWebViewBounds).mockReset();
  });

  it("renders left pane content", () => {
    render(<SplitPane leftPane={<div>Left Content</div>} />);
    expect(screen.getByText("Left Content")).toBeInTheDocument();
  });

  it("renders divider element", () => {
    const { container } = render(<SplitPane leftPane={<div>Left</div>} />);
    // The divider has cursor: col-resize style
    const divider = container.querySelector('[style*="col-resize"]');
    expect(divider).toBeInTheDocument();
  });

  it("applies default left width", () => {
    const { container } = render(
      <SplitPane leftPane={<div>Left</div>} defaultLeftWidth={350} />,
    );
    // The left pane is the first child of the flex container
    const flexContainer = container.firstElementChild;
    const leftPane = flexContainer?.firstElementChild as HTMLElement;
    expect(leftPane.style.width).toBe("350px");
  });

  it("calls updateWebViewBounds on mount", () => {
    render(<SplitPane leftPane={<div>Left</div>} />);
    expect(window.erkdesk.updateWebViewBounds).toHaveBeenCalled();
  });
});
