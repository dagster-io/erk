import { Menu, BrowserWindow, MenuItemConstructorOptions } from "electron";
import type { PlanRow } from "../types/erkdesk";

interface ActionDef {
  id: string;
  label: string;
  isAvailable: (plan: PlanRow) => boolean;
}

const ACTIONS: ActionDef[] = [
  {
    id: "submit_to_queue",
    label: "Submit",
    isAvailable: (plan) => plan.issue_url !== null,
  },
  {
    id: "land_pr",
    label: "Land",
    isAvailable: (plan) =>
      plan.pr_number !== null &&
      plan.pr_state === "OPEN" &&
      plan.run_url !== null,
  },
  {
    id: "address_remote",
    label: "Address",
    isAvailable: (plan) => plan.pr_number !== null,
  },
  {
    id: "fix_conflicts_remote",
    label: "Fix Conflicts",
    isAvailable: (plan) => plan.pr_number !== null,
  },
  {
    id: "close_plan",
    label: "Close",
    isAvailable: () => true,
  },
];

export function buildContextMenu(
  plan: PlanRow,
  window: BrowserWindow,
): Menu {
  const template: MenuItemConstructorOptions[] = [];

  // OPEN section
  template.push(
    {
      label: "Open Issue",
      enabled: plan.issue_url !== null,
      click: () => {
        if (plan.issue_url) {
          window.webContents.send("context-menu:action", {
            type: "open_url",
            payload: plan.issue_url,
          });
        }
      },
    },
    {
      label: "Open PR",
      enabled: plan.pr_url !== null,
      click: () => {
        if (plan.pr_url) {
          window.webContents.send("context-menu:action", {
            type: "open_url",
            payload: plan.pr_url,
          });
        }
      },
    },
    {
      label: "Open Run",
      enabled: plan.run_url !== null,
      click: () => {
        if (plan.run_url) {
          window.webContents.send("context-menu:action", {
            type: "open_url",
            payload: plan.run_url,
          });
        }
      },
    },
  );

  // Separator
  template.push({ type: "separator" });

  // COPY section
  template.push(
    {
      label: "Copy Checkout Command",
      enabled: plan.worktree_branch !== null,
      click: () => {
        if (plan.worktree_branch) {
          window.webContents.send("context-menu:action", {
            type: "copy",
            payload: `erk br co ${plan.worktree_branch}`,
          });
        }
      },
    },
    {
      label: "Copy PR Checkout Command",
      enabled: plan.pr_number !== null,
      click: () => {
        if (plan.pr_number !== null) {
          window.webContents.send("context-menu:action", {
            type: "copy",
            payload: `source "$(erk pr checkout ${plan.pr_number} --script)" && erk pr sync --dangerous`,
          });
        }
      },
    },
    {
      label: "Copy Prepare Command",
      enabled: true,
      click: () => {
        window.webContents.send("context-menu:action", {
          type: "copy",
          payload: `erk prepare ${plan.issue_number}`,
        });
      },
    },
    {
      label: "Copy Prepare & Implement",
      enabled: true,
      click: () => {
        window.webContents.send("context-menu:action", {
          type: "copy",
          payload: `source "$(erk prepare ${plan.issue_number} --script)" && erk implement --dangerous`,
        });
      },
    },
    {
      label: "Copy Submit Command",
      enabled: true,
      click: () => {
        window.webContents.send("context-menu:action", {
          type: "copy",
          payload: `erk plan submit ${plan.issue_number}`,
        });
      },
    },
    {
      label: "Copy Replan Command",
      enabled: plan.issue_url !== null,
      click: () => {
        window.webContents.send("context-menu:action", {
          type: "copy",
          payload: `erk plan replan ${plan.issue_number}`,
        });
      },
    },
  );

  // Separator
  template.push({ type: "separator" });

  // ACTION section
  ACTIONS.forEach((action) => {
    template.push({
      label: action.label,
      enabled: action.isAvailable(plan),
      click: () => {
        window.webContents.send("context-menu:action", {
          type: "execute",
          payload: action.id,
        });
      },
    });
  });

  return Menu.buildFromTemplate(template);
}
