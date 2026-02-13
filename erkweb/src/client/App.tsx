import {useState} from 'react';

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
        permissionRequest={chat.permissionRequest}
        activity={chat.activity}
        commands={chat.commands}
        onSend={chat.sendMessage}
        onStop={chat.stopGeneration}
        onPermissionRespond={chat.respondToPermission}
      />
      {selectedPlan && <PlanDetail plan={selectedPlan} onClose={() => setSelectedPlan(null)} />}
    </div>
  );
}
