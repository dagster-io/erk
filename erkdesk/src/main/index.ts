import { app, BrowserWindow, ipcMain, WebContentsView } from "electron";
import path from "path";
import type { WebViewBounds } from "../types/erkdesk";

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (require("electron-squirrel-startup")) {
  app.quit();
}

let webView: WebContentsView | null = null;

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

  // Load the app.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(
      path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`),
    );
  }

  // Open the DevTools in development mode.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.webContents.openDevTools();
  }

  // Clean up on window close.
  mainWindow.on("closed", () => {
    ipcMain.removeAllListeners("webview:update-bounds");
    ipcMain.removeAllListeners("webview:load-url");
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
