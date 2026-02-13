import {useEffect, useState} from 'react';

import {ChatPanel} from './components/ChatPanel.js';
import {PlanDetail} from './components/PlanDetail.js';
import {PlanSidebar} from './components/PlanSidebar.js';
import {useChat} from './hooks/useChat.js';
import {usePlans} from './hooks/usePlans.js';
import type {PlanRow} from '../shared/types.js';
import './App.css';

export function App() {
  const chat = useChat();
  const {plans, loading, error} = usePlans();
  const [selectedPlan, setSelectedPlan] = useState<PlanRow | null>(null);

  // When the selected plan changes, resolve its worktree path and set chat context.
  // Clear messages and show loading immediately so the old session doesn't linger.
  useEffect(() => {
    if (!selectedPlan || !selectedPlan.exists_locally) {
      chat.setChatContext(null, null);
      return;
    }
    chat.setLoading(selectedPlan.worktree_branch);
    let cancelled = false;
    fetch(`/api/plans/${selectedPlan.issue_number}/worktree-path`)
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled && data.success) {
          chat.setChatContext(data.worktreePath, selectedPlan.worktree_branch);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [selectedPlan?.issue_number, selectedPlan?.exists_locally]);

  return (
    <div className="app">
      <PlanSidebar
        plans={plans}
        loading={loading}
        error={error}
        selectedPlan={selectedPlan}
        onSelect={setSelectedPlan}
      />
      <ChatPanel
        messages={chat.messages}
        streamingText={chat.streamingText}
        isStreaming={chat.isStreaming}
        sessionId={chat.sessionId}
        model={chat.model}
        chatBranch={chat.chatBranch}
        sessions={chat.sessions}
        selectedSessionId={chat.selectedSessionId}
        sessionsLoading={chat.sessionsLoading}
        permissionRequest={chat.permissionRequest}
        activity={chat.activity}
        commands={chat.commands}
        onSend={chat.sendMessage}
        onStop={chat.stopGeneration}
        onSelectSession={chat.selectSession}
        onPermissionRespond={chat.respondToPermission}
      />
      {selectedPlan && (
        <PlanDetail
          plan={selectedPlan}
          onClose={() => setSelectedPlan(null)}
          onSend={chat.sendMessage}
          isStreaming={chat.isStreaming}
        />
      )}
    </div>
  );
}
