import "@testing-library/jest-dom";
import type { ErkdeskAPI } from "../types/erkdesk";

// jsdom does not implement scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// Provide a default mock of window.erkdesk so components can render
// without a real Electron preload script.
const mockErkdesk: ErkdeskAPI = {
  version: "test",
  updateWebViewBounds: vi.fn(),
  loadWebViewURL: vi.fn(),
  fetchPlans: vi.fn().mockResolvedValue({ success: true, plans: [], count: 0 }),
};

Object.defineProperty(window, "erkdesk", {
  value: mockErkdesk,
  writable: true,
});
