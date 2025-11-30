import type { StreamEvent } from '../types';

interface StreamingMessageProps {
  events: StreamEvent[];
  isStreaming: boolean;
}

export function StreamingMessage({ events, isStreaming }: StreamingMessageProps) {
  if (events.length === 0 && !isStreaming) {
    return null;
  }

  return (
    <div style={styles.container}>
      {events.map((event, index) => (
        <div key={index} style={getEventStyle(event.event_type)}>
          {renderEvent(event)}
        </div>
      ))}
      {isStreaming && (
        <div style={styles.streaming}>
          <span style={styles.dot}>.</span>
          <span style={styles.dot}>.</span>
          <span style={styles.dot}>.</span>
        </div>
      )}
    </div>
  );
}

function renderEvent(event: StreamEvent): React.ReactNode {
  switch (event.event_type) {
    case 'text':
      return (
        <div style={styles.text}>
          {String(event.data.content || '')}
        </div>
      );

    case 'tool':
      return (
        <div style={styles.tool}>
          <span style={styles.toolIcon}>{'>'}</span>
          <span style={styles.toolName}>{String(event.data.name || 'Tool')}</span>
          <span style={styles.toolSummary}>{String(event.data.summary || '')}</span>
        </div>
      );

    case 'done':
      const success = event.data.success;
      return (
        <div style={{ ...styles.done, color: success ? '#4caf50' : '#f44336' }}>
          {success ? 'Completed' : 'Failed'}
          {event.data.duration_seconds && (
            <span style={styles.duration}>
              ({Number(event.data.duration_seconds).toFixed(1)}s)
            </span>
          )}
        </div>
      );

    case 'error':
      return (
        <div style={styles.error}>
          Error: {String(event.data.message || 'Unknown error')}
        </div>
      );

    default:
      return null;
  }
}

function getEventStyle(eventType: string): React.CSSProperties {
  const base: React.CSSProperties = {
    padding: '8px 12px',
    borderRadius: '4px',
    marginBottom: '8px',
  };

  switch (eventType) {
    case 'text':
      return { ...base, backgroundColor: '#f5f5f5' };
    case 'tool':
      return { ...base, backgroundColor: '#e8f5e9', fontFamily: 'monospace', fontSize: '13px' };
    case 'done':
      return { ...base, backgroundColor: '#f5f5f5', fontWeight: 500 };
    case 'error':
      return { ...base, backgroundColor: '#ffebee', color: '#c62828' };
    default:
      return base;
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '16px',
  },
  text: {
    whiteSpace: 'pre-wrap',
    lineHeight: 1.5,
  },
  tool: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  toolIcon: {
    color: '#4caf50',
    fontWeight: 'bold',
  },
  toolName: {
    fontWeight: 500,
    color: '#2e7d32',
  },
  toolSummary: {
    color: '#666',
  },
  done: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  duration: {
    fontWeight: 'normal',
    color: '#666',
    fontSize: '13px',
  },
  error: {
    fontWeight: 500,
  },
  streaming: {
    display: 'flex',
    gap: '2px',
    padding: '8px 12px',
  },
  dot: {
    animation: 'blink 1.4s infinite both',
    fontSize: '20px',
    lineHeight: 1,
  },
};
