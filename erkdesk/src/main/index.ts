import { app, BrowserWindow, ipcMain, WebContentsView } from "electron";
import { execFile, spawn, ChildProcess } from "child_process";
import path from "path";
import type {
  WebViewBounds,
  FetchPlansResult,
  ActionResult,
  ActionOutputEvent,
  ActionCompletedEvent,
} from "../types/erkdesk";

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require("electron-squirrel-startup")) {
  app.quit();
}

let webView: WebContentsView | null = null;
let activeAction: ChildProcess | null = null;

const createWindow = (): void => {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Create WebContentsView for the right pane (embedded web content).
  webView = new WebContentsView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });
  mainWindow.contentView.addChildView(webView);

  // Start invisible until renderer reports bounds.
  webView.setBounds({ x: 0, y: 0, width: 0, height: 0 });
  webView.webContents.loadURL("about:blank");

  // IPC: Update the WebContentsView bounds from renderer measurements.
  ipcMain.on("webview:update-bounds", (_event, bounds: WebViewBounds) => {
    if (!webView) return;
    webView.setBounds({
      x: Math.max(0, Math.floor(bounds.x)),
      y: Math.max(0, Math.floor(bounds.y)),
      width: Math.max(0, Math.floor(bounds.width)),
      height: Math.max(0, Math.floor(bounds.height)),
    });
  });

  // IPC: Load a URL in the WebContentsView.
  ipcMain.on("webview:load-url", (_event, url: string) => {
    if (!webView) return;
    if (typeof url === "string" && url.length > 0) {
      webView.webContents.loadURL(url);
    }
  });

  // IPC: Fetch plan data from erk CLI.
  ipcMain.handle("plans:fetch", (): Promise<FetchPlansResult> => {
    return new Promise((resolve) => {
      execFile("erk", ["exec", "dash-data"], (error, stdout, stderr) => {
        if (error) {
          resolve({
            success: false,
            plans: [],
            count: 0,
            error: stderr || error.message,
          });
          return;
        }
        try {
          const data = JSON.parse(stdout);
          resolve({
            success: true,
            plans: data.plans ?? data,
            count: data.count ?? (data.plans ?? data).length,
          });
        } catch (parseError) {
          resolve({
            success: false,
            plans: [],
            count: 0,
            error: `Failed to parse erk output: ${parseError}`,
          });
        }
      });
    });
  });

  // IPC: Execute an erk CLI action.
  ipcMain.handle(
    "actions:execute",
    (_event, command: string, args: string[]): Promise<ActionResult> => {
      return new Promise((resolve) => {
        execFile(command, args, (error, stdout, stderr) => {
          if (error) {
            resolve({
              success: false,
              stdout: stdout ?? "",
              stderr: stderr ?? "",
              error: error.message,
            });
            return;
          }
          resolve({
            success: true,
            stdout: stdout ?? "",
            stderr: stderr ?? "",
          });
        });
      });
    },
  );

  // Load the app.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(
      path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`),
    );
  }

  // IPC: Start streaming action with spawn.
  ipcMain.on(
    "actions:start-streaming",
    (_event, command: string, args: string[]) => {
      if (activeAction) {
        activeAction.kill();
        activeAction = null;
      }

      const proc = spawn(command, args);
      activeAction = proc;

      const stripAnsi = (text: string): string =>
        text.replace(/\x1B\[[0-9;]*m/g, "");

      proc.stdout?.on("data", (chunk: Buffer) => {
        const event: ActionOutputEvent = {
          stream: "stdout",
          data: stripAnsi(chunk.toString()),
        };
        mainWindow.webContents.send("action:output", event);
      });

      proc.stderr?.on("data", (chunk: Buffer) => {
        const event: ActionOutputEvent = {
          stream: "stderr",
          data: stripAnsi(chunk.toString()),
        };
        mainWindow.webContents.send("action:output", event);
      });

      proc.on("close", (code: number | null) => {
        const event: ActionCompletedEvent = {
          success: code === 0,
          error: code !== 0 ? `Process exited with code ${code}` : undefined,
        };
        mainWindow.webContents.send("action:completed", event);
        if (activeAction === proc) {
          activeAction = null;
        }
      });

      proc.on("error", (error: Error) => {
        const event: ActionCompletedEvent = {
          success: false,
          error: error.message,
        };
        mainWindow.webContents.send("action:completed", event);
        if (activeAction === proc) {
          activeAction = null;
        }
      });
    },
  );

  // Open the DevTools in development mode.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.webContents.openDevTools();
  }

  // Clean up on window close.
  mainWindow.on("closed", () => {
    ipcMain.removeAllListeners("webview:update-bounds");
    ipcMain.removeAllListeners("webview:load-url");
    ipcMain.removeHandler("plans:fetch");
    ipcMain.removeHandler("actions:execute");
    ipcMain.removeAllListeners("actions:start-streaming");
    if (activeAction) {
      activeAction.kill();
      activeAction = null;
    }
    webView = null;
  });
};

app.on("ready", createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
