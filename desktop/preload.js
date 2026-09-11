const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('alveonDesktop', {
    platform: process.platform,
    version: '5.1.0',
    isDesktop: true
});
