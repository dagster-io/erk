export interface WebViewBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ErkdeskAPI {
  version: string;
  updateWebViewBounds: (bounds: WebViewBounds) => void;
  loadWebViewURL: (url: string) => void;
}

declare global {
  interface Window {
    erkdesk: ErkdeskAPI;
  }
}
