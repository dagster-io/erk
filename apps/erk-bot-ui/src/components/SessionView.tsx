import type { Session } from '../types';
import { useSSE } from '../hooks/useSSE';
import { MessageInput } from './MessageInput';
import { StreamingMessage } from './StreamingMessage';

interface SessionViewProps {
  session: Session;
}

export function SessionView({ session }: SessionViewProps) {
  const { events, isStreaming, send } = useSSE(session.session_id);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>{session.working_directory}</h2>
        <div style={styles.meta}>
          <span style={styles.status(session.status)}>{session.status}</span>
          <span>{session.message_count} messages</span>
        </div>
      </div>

      <div style={styles.content}>
        <StreamingMessage events={events} isStreaming={isStreaming} />
      </div>

      <MessageInput onSend={send} disabled={isStreaming} />
    </div>
  );
}

const styles = {
  container: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
  },
  header: {
    padding: '16px',
    borderBottom: '1px solid #e0e0e0',
    backgroundColor: '#fafafa',
  },
  title: {
    margin: 0,
    fontSize: '16px',
    fontWeight: 500,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  meta: {
    display: 'flex',
    gap: '16px',
    marginTop: '8px',
    fontSize: '13px',
    color: '#666',
  },
  status: (status: string): React.CSSProperties => ({
    textTransform: 'capitalize',
    fontWeight: 500,
    color:
      status === 'active'
        ? '#4caf50'
        : status === 'processing'
        ? '#2196f3'
        : status === 'error'
        ? '#f44336'
        : '#9e9e9e',
  }),
  content: {
    flex: 1,
    overflow: 'auto',
  },
};
