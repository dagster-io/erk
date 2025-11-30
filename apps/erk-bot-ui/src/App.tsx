import { useState, useCallback } from 'react';
import { useSession } from './hooks/useSession';
import { SessionList } from './components/SessionList';
import { SessionView } from './components/SessionView';

function App() {
  const {
    sessions,
    currentSession,
    isLoading,
    error,
    selectSession,
    createNewSession,
    removeSession,
  } = useSession();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkingDir, setNewWorkingDir] = useState('');

  const handleCreate = useCallback(async () => {
    if (newWorkingDir.trim()) {
      await createNewSession(newWorkingDir.trim());
      setNewWorkingDir('');
      setShowCreateModal(false);
    }
  }, [createNewSession, newWorkingDir]);

  return (
    <div style={styles.app}>
      <SessionList
        sessions={sessions}
        currentSessionId={currentSession?.session_id || null}
        onSelect={selectSession}
        onDelete={removeSession}
        onCreate={() => setShowCreateModal(true)}
      />

      <div style={styles.main}>
        {error && (
          <div style={styles.error}>
            {error}
          </div>
        )}

        {isLoading && (
          <div style={styles.loading}>Loading...</div>
        )}

        {!currentSession && !isLoading && (
          <div style={styles.empty}>
            <h2>Welcome to Erk Bot</h2>
            <p>Select a session from the list or create a new one to get started.</p>
          </div>
        )}

        {currentSession && (
          <SessionView session={currentSession} />
        )}
      </div>

      {showCreateModal && (
        <div style={styles.modalOverlay} onClick={() => setShowCreateModal(false)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3 style={styles.modalTitle}>Create New Session</h3>
            <input
              type="text"
              value={newWorkingDir}
              onChange={(e) => setNewWorkingDir(e.target.value)}
              placeholder="Working directory (e.g., /path/to/repo)"
              style={styles.input}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleCreate();
                }
              }}
            />
            <div style={styles.modalButtons}>
              <button
                onClick={() => setShowCreateModal(false)}
                style={styles.cancelButton}
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                style={styles.createButton}
                disabled={!newWorkingDir.trim()}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    display: 'flex',
    height: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
  },
  error: {
    padding: '12px 16px',
    backgroundColor: '#ffebee',
    color: '#c62828',
    borderBottom: '1px solid #ffcdd2',
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#666',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#666',
    textAlign: 'center',
    padding: '32px',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modal: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '24px',
    width: '400px',
    maxWidth: '90%',
  },
  modalTitle: {
    margin: '0 0 16px 0',
    fontSize: '18px',
  },
  input: {
    width: '100%',
    padding: '12px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '14px',
    marginBottom: '16px',
    boxSizing: 'border-box',
  },
  modalButtons: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '8px',
  },
  cancelButton: {
    padding: '8px 16px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    backgroundColor: 'white',
    cursor: 'pointer',
  },
  createButton: {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: '#1976d2',
    color: 'white',
    cursor: 'pointer',
  },
};

export default App;
