import { contextBridge, ipcRenderer } from "electron";
import type {
  WebViewBounds,
  ActionOutputEvent,
  ActionCompletedEvent,
} from "../types/erkdesk";

contextBridge.exposeInMainWorld("erkdesk", {
  version: "0.1.0",
  updateWebViewBounds: (bounds: WebViewBounds) => {
    ipcRenderer.send("webview:update-bounds", bounds);
  },
  loadWebViewURL: (url: string) => {
    ipcRenderer.send("webview:load-url", url);
  },
  fetchPlans: () => ipcRenderer.invoke("plans:fetch"),
  executeAction: (command: string, args: string[]) =>
    ipcRenderer.invoke("actions:execute", command, args),
  startStreamingAction: (command: string, args: string[]) => {
    ipcRenderer.send("actions:start-streaming", command, args);
  },
  onActionOutput: (callback: (event: ActionOutputEvent) => void) => {
    ipcRenderer.on("action:output", (_ipcEvent, event: ActionOutputEvent) => {
      callback(event);
    });
  },
  onActionCompleted: (callback: (event: ActionCompletedEvent) => void) => {
    ipcRenderer.on(
      "action:completed",
      (_ipcEvent, event: ActionCompletedEvent) => {
        callback(event);
      },
    );
  },
  summonTerminal: (planId: number) =>
    ipcRenderer.invoke("terminal:summon", planId),
  removeActionListeners: () => {
    ipcRenderer.removeAllListeners("action:output");
    ipcRenderer.removeAllListeners("action:completed");
  },
});
