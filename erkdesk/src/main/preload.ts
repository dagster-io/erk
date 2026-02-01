import { contextBridge, ipcRenderer } from "electron";
import type { WebViewBounds } from "../types/erkdesk";

contextBridge.exposeInMainWorld("erkdesk", {
  version: "0.1.0",
  updateWebViewBounds: (bounds: WebViewBounds) => {
    ipcRenderer.send("webview:update-bounds", bounds);
  },
  loadWebViewURL: (url: string) => {
    ipcRenderer.send("webview:load-url", url);
  },
  fetchPlans: () => ipcRenderer.invoke("plans:fetch"),
});
