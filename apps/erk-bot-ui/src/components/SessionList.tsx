import type { Session } from '../types';

interface SessionListProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
  onCreate: () => void;
}

export function SessionList({
  sessions,
  currentSessionId,
  onSelect,
  onDelete,
  onCreate,
}: SessionListProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return '#4caf50';
      case 'processing':
        return '#2196f3';
      case 'error':
        return '#f44336';
      default:
        return '#9e9e9e';
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Sessions</h2>
        <button onClick={onCreate} style={styles.createButton}>
          + New Session
        </button>
      </div>

      <div style={styles.list}>
        {sessions.length === 0 ? (
          <p style={styles.empty}>No sessions yet. Create one to get started!</p>
        ) : (
          sessions.map((session) => (
            <div
              key={session.session_id}
              style={{
                ...styles.item,
                ...(currentSessionId === session.session_id ? styles.itemSelected : {}),
              }}
              onClick={() => onSelect(session.session_id)}
            >
              <div style={styles.itemHeader}>
                <span
                  style={{
                    ...styles.status,
                    backgroundColor: getStatusColor(session.status),
                  }}
                />
                <span style={styles.directory}>
                  {session.working_directory.split('/').pop()}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(session.session_id);
                  }}
                  style={styles.deleteButton}
                >
                  x
                </button>
              </div>
              <div style={styles.itemMeta}>
                <span>{session.message_count} messages</span>
                <span>{formatDate(session.last_activity)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    width: '300px',
    borderRight: '1px solid #e0e0e0',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    padding: '16px',
    borderBottom: '1px solid #e0e0e0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    margin: 0,
    fontSize: '18px',
  },
  createButton: {
    padding: '8px 12px',
    backgroundColor: '#1976d2',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  list: {
    flex: 1,
    overflow: 'auto',
  },
  empty: {
    padding: '16px',
    color: '#666',
    textAlign: 'center',
  },
  item: {
    padding: '12px 16px',
    borderBottom: '1px solid #f0f0f0',
    cursor: 'pointer',
  },
  itemSelected: {
    backgroundColor: '#e3f2fd',
  },
  itemHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  status: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  directory: {
    fontWeight: 500,
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  deleteButton: {
    padding: '2px 6px',
    backgroundColor: 'transparent',
    border: '1px solid #ccc',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
  },
  itemMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
    color: '#666',
    marginTop: '4px',
  },
};
