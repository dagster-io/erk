import { contextBridge } from 'electron';

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('erkdesk', {
  version: '0.1.0',
  // Future IPC methods will go here:
  // - fetchDashData()
  // - executeCommand()
});
