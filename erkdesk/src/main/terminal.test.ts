import {
  toScreenCoordinates,
  buildPositionAppleScript,
  type ScreenBounds,
} from "./terminal";
import type { WebViewBounds } from "../types/erkdesk";

describe("toScreenCoordinates", () => {
  it("translates pane-relative bounds to screen coordinates", () => {
    const paneBounds: WebViewBounds = { x: 400, y: 0, width: 600, height: 800 };
    const windowBounds: ScreenBounds = {
      x: 100,
      y: 50,
      width: 1200,
      height: 850,
    };
    const contentBounds: ScreenBounds = {
      x: 100,
      y: 78,
      width: 1200,
      height: 822,
    };

    const result = toScreenCoordinates(paneBounds, windowBounds, contentBounds);

    expect(result).toEqual({
      x: 500, // 100 (window x) + 0 (frame offset) + 400 (pane x)
      y: 78, // 50 (window y) + 28 (title bar) + 0 (pane y)
      width: 600,
      height: 800,
    });
  });

  it("accounts for frame left offset", () => {
    const paneBounds: WebViewBounds = {
      x: 200,
      y: 10,
      width: 400,
      height: 300,
    };
    const windowBounds: ScreenBounds = {
      x: 50,
      y: 100,
      width: 800,
      height: 600,
    };
    // Content area offset by 2px on left (frame border)
    const contentBounds: ScreenBounds = {
      x: 52,
      y: 130,
      width: 796,
      height: 570,
    };

    const result = toScreenCoordinates(paneBounds, windowBounds, contentBounds);

    expect(result).toEqual({
      x: 252, // 50 + 2 + 200
      y: 140, // 100 + 30 + 10
      width: 400,
      height: 300,
    });
  });

  it("rounds fractional values", () => {
    const paneBounds: WebViewBounds = {
      x: 100.7,
      y: 0.3,
      width: 500.5,
      height: 400.9,
    };
    const windowBounds: ScreenBounds = { x: 0, y: 0, width: 1200, height: 800 };
    const contentBounds: ScreenBounds = {
      x: 0,
      y: 28,
      width: 1200,
      height: 772,
    };

    const result = toScreenCoordinates(paneBounds, windowBounds, contentBounds);

    expect(result.x).toBe(101);
    expect(result.y).toBe(28);
    expect(result.width).toBe(501);
    expect(result.height).toBe(401);
  });
});

describe("buildPositionAppleScript", () => {
  it("generates correct AppleScript for positioning", () => {
    const bounds: ScreenBounds = { x: 500, y: 78, width: 600, height: 800 };

    const script = buildPositionAppleScript(bounds);

    expect(script).toContain('tell application "System Events"');
    expect(script).toContain('tell process "Terminal"');
    expect(script).toContain("set position of front window to {500, 78}");
    expect(script).toContain("set size of front window to {600, 800}");
  });

  it("handles zero-origin bounds", () => {
    const bounds: ScreenBounds = { x: 0, y: 0, width: 1920, height: 1080 };

    const script = buildPositionAppleScript(bounds);

    expect(script).toContain("set position of front window to {0, 0}");
    expect(script).toContain("set size of front window to {1920, 1080}");
  });
});
