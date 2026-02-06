import { execFile } from "child_process";
import type { WebViewBounds, TerminalSummonResult } from "../types/erkdesk";

export interface ScreenBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Translate renderer-relative bounds to absolute screen coordinates.
 *
 * The right pane bounds from the renderer are relative to the BrowserWindow
 * content area. To get screen coordinates we add the window position and
 * the content area offset (title bar height, etc.).
 */
export function toScreenCoordinates(
  paneBounds: WebViewBounds,
  windowBounds: ScreenBounds,
  contentBounds: ScreenBounds,
): ScreenBounds {
  const titleBarHeight = contentBounds.y - windowBounds.y;
  const frameLeftOffset = contentBounds.x - windowBounds.x;

  return {
    x: Math.round(windowBounds.x + frameLeftOffset + paneBounds.x),
    y: Math.round(windowBounds.y + titleBarHeight + paneBounds.y),
    width: Math.round(paneBounds.width),
    height: Math.round(paneBounds.height),
  };
}

/**
 * Build the osascript command arguments to position Terminal.app's front window.
 */
export function buildPositionAppleScript(bounds: ScreenBounds): string {
  return [
    'tell application "System Events"',
    '  tell process "Terminal"',
    `    set position of front window to {${bounds.x}, ${bounds.y}}`,
    `    set size of front window to {${bounds.width}, ${bounds.height}}`,
    "  end tell",
    "end tell",
  ].join("\n");
}

/**
 * Spawn Terminal.app via `open -a Terminal`.
 */
function spawnTerminal(): Promise<void> {
  return new Promise((resolve, reject) => {
    execFile("open", ["-a", "Terminal"], (error) => {
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    });
  });
}

/**
 * Run an AppleScript string via osascript.
 */
function runAppleScript(script: string): Promise<void> {
  return new Promise((resolve, reject) => {
    execFile("osascript", ["-e", script], (error) => {
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    });
  });
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Summon a terminal window positioned over the given screen bounds.
 *
 * 1. Spawns Terminal.app via `open -a`
 * 2. Waits briefly for the window to appear
 * 3. Positions it via osascript System Events
 */
export async function summonTerminal(
  screenBounds: ScreenBounds | null,
): Promise<TerminalSummonResult> {
  if (screenBounds === null) {
    return { success: false, pid: null, error: "No pane bounds available" };
  }

  try {
    await spawnTerminal();
    await delay(500);
    const script = buildPositionAppleScript(screenBounds);
    await runAppleScript(script);
    return { success: true, pid: null };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { success: false, pid: null, error: message };
  }
}
