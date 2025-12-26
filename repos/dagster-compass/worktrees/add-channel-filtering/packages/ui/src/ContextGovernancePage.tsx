import {useState, useEffect, useRef, type ReactNode, useCallback} from 'react';
import {fetchWithAuth} from './utils/authErrors';
import {useGovernanceCount} from './contexts/GovernanceCountContext';
import {ErrorMessage} from './components/ErrorMessage';

type ContextUpdateType = 'SCHEDULED_ANALYSIS' | 'CONTEXT_UPDATE' | 'DATA_REQUEST';
type ContextStatusType = 'OPEN' | 'MERGED' | 'CLOSED';

interface PrInfo {
  type: 'context_update_created' | 'scheduled_analysis_created';
  bot_id: string;
}

interface ChannelReviewOptions {
  available: boolean;
  channel_label: string | null;
  channel_name: string | null;
}

interface ContextStatusEntry {
  id: number;
  organization_id: number;
  repo_name: string;
  update_type: ContextUpdateType;
  github_url: string;
  github_auth_url: string;
  title: string;
  description: string;
  status: ContextStatusType;
  created_at: number;
  updated_at: number;
  github_updated_at: number;
  acted_by_user_id: string | null;
  acted_at: number | null;
  pr_info: PrInfo | null;
  channel_review_options?: ChannelReviewOptions | null;
}

interface ContextStatusData {
  entries: ContextStatusEntry[];
}

type ModalType = 'approve' | 'reject';

interface ModalState {
  type: ModalType;
  entry: ContextStatusEntry;
}

const extractRequestNumber = (entry: ContextStatusEntry): string | null => {
  const pullMatch = entry.github_url.match(/\/pull\/(\d+)/);
  const pullNumber = pullMatch?.[1];
  if (pullNumber) {
    return pullNumber;
  }
  const issueNumber = entry.github_url.match(/\/issues\/(\d+)/)?.[1];
  return issueNumber ?? null;
};

export default function ContextGovernancePage() {
  const [data, setData] = useState<ContextStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGithubAuthorized, setIsGithubAuthorized] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<number | null>(null);
  const {refresh: refreshGovernanceCount} = useGovernanceCount();

  // Initialize filters from URL query params
  const searchParams = new URLSearchParams(window.location.search);
  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get('status') || 'OPEN');
  const [updateTypeFilter, setUpdateTypeFilter] = useState<string>(
    searchParams.get('update_type') || 'all',
  );
  const [highlightRequest] = useState<string | null>(() => searchParams.get('request'));
  const hasScrolledToHighlight = useRef(false);
  const [modalState, setModalState] = useState<ModalState | null>(null);
  const [pendingApproveScope, setPendingApproveScope] = useState<'all' | 'channel' | null>(null);

  useEffect(() => {
    // Check for GitHub authorization cookie
    const githubCookie = document.cookie
      .split('; ')
      .find((row) => row.startsWith('github_authorized='));

    setIsGithubAuthorized(!!githubCookie);
  }, []);

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (statusFilter !== 'all') {
      params.set('status', statusFilter);
    }
    if (updateTypeFilter !== 'all') {
      params.set('update_type', updateTypeFilter);
    }
    if (highlightRequest) {
      params.set('request', highlightRequest);
    }
    const searchString = params.toString();
    const basePath = window.location.pathname;
    const newUrl = searchString ? `${basePath}?${searchString}` : basePath;
    const currentUrl = `${basePath}${window.location.search}`;
    if (newUrl !== currentUrl) {
      window.history.replaceState({}, '', newUrl);
    }
  }, [statusFilter, updateTypeFilter, highlightRequest]);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      if (updateTypeFilter !== 'all') {
        params.append('update_type', updateTypeFilter);
      }

      const response = await fetchWithAuth(`/api/context-governance/list?${params}`);
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, updateTypeFilter]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  useEffect(() => {
    if (!highlightRequest || !data || hasScrolledToHighlight.current) {
      return;
    }

    const requestExists = data.entries.some(
      (entry) => extractRequestNumber(entry) === highlightRequest,
    );
    if (!requestExists) {
      return;
    }

    const targetRow = document.getElementById(`governance-request-${highlightRequest}`);
    if (targetRow) {
      targetRow.scrollIntoView({behavior: 'smooth', block: 'center'});
      hasScrolledToHighlight.current = true;
    }
  }, [data, highlightRequest]);

  const handleApprove = async (entry: ContextStatusEntry, scope: 'all' | 'channel') => {
    setPendingApproveScope(scope);
    setActionInProgress(entry.id);
    setError(null);
    try {
      const response = await fetchWithAuth('/api/context-governance/approve', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({github_url: entry.github_url, scope}),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to approve');
      }

      // Refresh the list after approval
      setModalState(null);
      setPendingApproveScope(null);
      await fetchEvents();
      // Refresh the badge count
      await refreshGovernanceCount();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setActionInProgress(null);
      setPendingApproveScope(null);
    }
  };

  const handleReject = async (entry: ContextStatusEntry) => {
    setActionInProgress(entry.id);
    setError(null);
    try {
      const response = await fetchWithAuth('/api/context-governance/reject', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({github_url: entry.github_url}),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to reject');
      }

      // Refresh the list after rejection
      setModalState(null);
      setPendingApproveScope(null);
      await fetchEvents();
      // Refresh the badge count
      await refreshGovernanceCount();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setActionInProgress(null);
    }
  };

  const openApproveModal = (entry: ContextStatusEntry) => {
    setPendingApproveScope(null);
    setModalState({type: 'approve', entry});
  };

  const openRejectModal = (entry: ContextStatusEntry) => {
    setPendingApproveScope(null);
    setModalState({type: 'reject', entry});
  };

  const closeModal = () => {
    if (modalState && actionInProgress === modalState.entry.id) {
      return;
    }
    setModalState(null);
    setPendingApproveScope(null);
  };

  const confirmReject = async () => {
    if (!modalState) {
      return;
    }
    await handleReject(modalState.entry);
  };

  const isSubmitting = modalState ? actionInProgress === modalState.entry.id : false;
  const submittingScope = isSubmitting ? pendingApproveScope : null;

  const getStatusBadge = (status: ContextStatusType) => {
    switch (status) {
      case 'OPEN':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
              <circle cx="6" cy="6" r="3" />
            </svg>
            Open
          </span>
        );
      case 'MERGED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor">
              <path d="M2 6l3 3 5-6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Approved
          </span>
        );
      case 'CLOSED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor">
              <path d="M3 3l6 6M9 3l-6 6" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Closed
          </span>
        );
    }
  };

  const getRequestTypeLabel = (updateType: ContextUpdateType) => {
    switch (updateType) {
      case 'CONTEXT_UPDATE':
        return 'Context update';
      case 'DATA_REQUEST':
        return 'Data request';
      case 'SCHEDULED_ANALYSIS':
        return 'Recurring analysis';
      default:
        return updateType;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-sm text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error && !data) {
    return <ErrorMessage message={error} />;
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-sm text-gray-500">No data available</div>
      </div>
    );
  }

  const entries = data.entries;

  // Extract repo URL from first entry
  const repoUrl = entries[0]?.github_url?.split('/pull/')[0]?.split('/issues/')[0] || '#';
  // For auth flow, use the first entry's auth URL which will redirect back to governance after auth
  const repoAuthUrl = entries[0]?.github_auth_url || '#';

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start">
              <svg
                className="w-5 h-5 text-red-600 mt-0.5 mr-3"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              <div className="flex-1">
                <p className="text-sm text-red-800">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="text-red-600 hover:text-red-800">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
        )}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">Governance</h1>
          <a
            href={isGithubAuthorized ? repoUrl : repoAuthUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:text-gray-900 hover:bg-white border border-gray-300 rounded-lg transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
            Github Context Repo
          </a>
        </div>

        {/* Filters */}
        <div className="mb-6 flex gap-3">
          <div>
            <label
              htmlFor="status-filter"
              className="block text-xs font-medium text-gray-700 mb-1.5"
            >
              Status
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
            >
              <option value="all">All</option>
              <option value="OPEN">Open</option>
              <option value="MERGED">Approved</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="update-type-filter"
              className="block text-xs font-medium text-gray-700 mb-1.5"
            >
              Request type
            </label>
            <select
              id="update-type-filter"
              value={updateTypeFilter}
              onChange={(e) => setUpdateTypeFilter(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
            >
              <option value="all">All</option>
              <option value="CONTEXT_UPDATE">Context update</option>
              <option value="DATA_REQUEST">Data request</option>
              <option value="SCHEDULED_ANALYSIS">Recurring analysis</option>
            </select>
          </div>
        </div>

        {entries.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <p className="text-sm text-gray-500">No entries found</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Request type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Updated
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Context
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Controls
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {entries.map((entry) => {
                  const requestNumber = extractRequestNumber(entry);
                  const isHighlighted =
                    highlightRequest !== null && requestNumber === highlightRequest;
                  const rowClasses = [
                    'transition-colors',
                    isHighlighted
                      ? 'bg-amber-50 hover:bg-amber-100 ring-1 ring-amber-200'
                      : 'hover:bg-gray-50',
                  ].join(' ');

                  return (
                    <tr
                      key={entry.id}
                      id={
                        isHighlighted && requestNumber
                          ? `governance-request-${requestNumber}`
                          : undefined
                      }
                      className={rowClasses}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(entry.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-gray-900">
                          {getRequestTypeLabel(entry.update_type)}
                        </span>
                      </td>
                      <td className="px-6 py-4 max-w-md">
                        <div className="text-sm text-gray-900 truncate">{entry.title}</div>
                        {requestNumber ? (
                          <div className="text-xs text-gray-500 mt-1">Request #{requestNumber}</div>
                        ) : null}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-gray-500">
                          {new Date(entry.updated_at * 1000).toLocaleDateString()}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <a
                          href={isGithubAuthorized ? entry.github_url : entry.github_auth_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center text-gray-700 hover:text-gray-900"
                        >
                          <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
                          </svg>
                        </a>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {entry.status === 'OPEN' && entry.update_type !== 'DATA_REQUEST' ? (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => openApproveModal(entry)}
                              disabled={actionInProgress === entry.id}
                              className="inline-flex items-center justify-center w-8 h-8 rounded border border-gray-300 hover:bg-green-50 text-green-600 hover:border-green-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Approve request"
                            >
                              {actionInProgress === entry.id ? (
                                <svg
                                  className="animate-spin"
                                  width="16"
                                  height="16"
                                  viewBox="0 0 24 24"
                                  fill="none"
                                >
                                  <circle
                                    className="opacity-25"
                                    cx="12"
                                    cy="12"
                                    r="10"
                                    stroke="currentColor"
                                    strokeWidth="4"
                                  />
                                  <path
                                    className="opacity-75"
                                    fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                  />
                                </svg>
                              ) : (
                                <svg
                                  width="16"
                                  height="16"
                                  viewBox="0 0 16 16"
                                  fill="none"
                                  stroke="currentColor"
                                >
                                  <path
                                    d="M3 8l3 3 7-7"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  />
                                </svg>
                              )}
                            </button>
                            <button
                              onClick={() => openRejectModal(entry)}
                              disabled={actionInProgress === entry.id}
                              className="inline-flex items-center justify-center w-8 h-8 rounded border border-gray-300 hover:bg-red-50 text-red-600 hover:border-red-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Reject request"
                            >
                              {actionInProgress === entry.id ? (
                                <svg
                                  className="animate-spin"
                                  width="16"
                                  height="16"
                                  viewBox="0 0 24 24"
                                  fill="none"
                                >
                                  <circle
                                    className="opacity-25"
                                    cx="12"
                                    cy="12"
                                    r="10"
                                    stroke="currentColor"
                                    strokeWidth="4"
                                  />
                                  <path
                                    className="opacity-75"
                                    fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                  />
                                </svg>
                              ) : (
                                <svg
                                  width="16"
                                  height="16"
                                  viewBox="0 0 16 16"
                                  fill="none"
                                  stroke="currentColor"
                                >
                                  <path
                                    d="M4 4l8 8M12 4l-8 8"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                  />
                                </svg>
                              )}
                            </button>
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {modalState && (
        <ModalBackdrop onDismiss={closeModal} isDismissDisabled={isSubmitting}>
          {modalState.type === 'approve' ? (
            <ApprovalModal
              entry={modalState.entry}
              onApproveAll={() => handleApprove(modalState.entry, 'all')}
              onApproveChannel={() => handleApprove(modalState.entry, 'channel')}
              onClose={closeModal}
              isSubmitting={isSubmitting}
              submittingScope={submittingScope}
            />
          ) : (
            <RejectModal
              entry={modalState.entry}
              onClose={closeModal}
              onReject={confirmReject}
              isSubmitting={isSubmitting}
            />
          )}
        </ModalBackdrop>
      )}
    </div>
  );
}

function formatChannelLabel(
  channelOptions: ChannelReviewOptions | null | undefined,
  prInfo: PrInfo | null,
): string {
  if (channelOptions?.channel_label && channelOptions.channel_label.length > 0) {
    return channelOptions.channel_label;
  }
  const rawName = channelOptions?.channel_name ?? prInfo?.bot_id?.split('-').slice(1).join('-');
  if (!rawName || rawName.length === 0) {
    return 'original channel';
  }
  return rawName.startsWith('#') ? rawName : `#${rawName}`;
}

interface ModalBackdropProps {
  children: ReactNode;
  onDismiss: () => void;
  isDismissDisabled: boolean;
}

function ModalBackdrop({children, onDismiss, isDismissDisabled}: ModalBackdropProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      role="presentation"
      onClick={() => {
        if (!isDismissDisabled) {
          onDismiss();
        }
      }}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl ring-1 ring-black/5"
        role="dialog"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

interface ModalShellProps {
  title: string;
  subtitle: string;
  onClose: () => void;
  isCloseDisabled: boolean;
  children: ReactNode;
}

function ModalShell({title, subtitle, onClose, isCloseDisabled, children}: ModalShellProps) {
  return (
    <>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <p className="mt-1 text-sm text-gray-600 break-words">{subtitle}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          disabled={isCloseDisabled}
          className="rounded-full p-1 text-gray-400 transition hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Close modal"
        >
          <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor">
            <path d="M5 5l10 10M15 5l-10 10" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
      </div>
      {children}
    </>
  );
}

interface ApprovalModalProps {
  entry: ContextStatusEntry;
  onApproveAll: () => void;
  onApproveChannel: () => void;
  onClose: () => void;
  isSubmitting: boolean;
  submittingScope: 'all' | 'channel' | null;
}

function ApprovalModal({
  entry,
  onApproveAll,
  onApproveChannel,
  onClose,
  isSubmitting,
  submittingScope,
}: ApprovalModalProps) {
  const [resolvedPrInfo, setResolvedPrInfo] = useState<PrInfo | null>(entry.pr_info);
  const [resolvedChannelOptions, setResolvedChannelOptions] = useState<
    ChannelReviewOptions | null | undefined
  >(entry.channel_review_options);
  const [isLoadingPrInfo, setIsLoadingPrInfo] = useState(false);

  useEffect(() => {
    let isMounted = true;
    setResolvedPrInfo(entry.pr_info);
    setResolvedChannelOptions(entry.channel_review_options);

    const isChannelEligible =
      entry.update_type === 'CONTEXT_UPDATE' || entry.update_type === 'SCHEDULED_ANALYSIS';
    const hasChannelOptions = Boolean(entry.channel_review_options?.available);
    const hasPrInfo = entry.pr_info !== null && entry.pr_info !== undefined;

    if (!isChannelEligible || (hasChannelOptions && hasPrInfo)) {
      setIsLoadingPrInfo(false);
      return () => {
        isMounted = false;
      };
    }

    setIsLoadingPrInfo(true);
    const params = new URLSearchParams();
    params.set('status', entry.status);
    params.set('update_type', entry.update_type);
    params.set('limit', '100');
    (async () => {
      try {
        const response = await fetchWithAuth(`/api/context-governance/list?${params}`);
        const result: ContextStatusData = await response.json();
        const matchedEntry = result.entries.find(
          (candidate) => candidate.github_url === entry.github_url,
        );
        if (!matchedEntry || !isMounted) {
          return;
        }
        setResolvedPrInfo(matchedEntry.pr_info);
        setResolvedChannelOptions(matchedEntry.channel_review_options);
      } catch (fetchError) {
        console.error('Failed to fetch PR info for approval modal', fetchError);
      } finally {
        if (isMounted) {
          setIsLoadingPrInfo(false);
        }
      }
    })();

    return () => {
      isMounted = false;
    };
  }, [entry]);

  const channelOptions = resolvedChannelOptions;
  const channelLabel = formatChannelLabel(channelOptions, resolvedPrInfo);
  const isChannelEligibleUpdate =
    entry.update_type === 'CONTEXT_UPDATE' || entry.update_type === 'SCHEDULED_ANALYSIS';
  const showChannelButtons = Boolean(channelOptions?.available && isChannelEligibleUpdate);
  const isSubmittingAll = isSubmitting && submittingScope === 'all';
  const isSubmittingChannel = isSubmitting && submittingScope === 'channel';

  return (
    <ModalShell
      title="Approve request"
      subtitle={entry.title}
      onClose={onClose}
      isCloseDisabled={isSubmitting}
    >
      <div className="mt-5 space-y-4">
        <p className="text-sm text-gray-600">
          Approving will merge this change so the team can rely on it for future analyses.
        </p>
        {showChannelButtons ? (
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Choose where to merge this update
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={onApproveAll}
                disabled={isSubmitting}
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmittingAll ? (
                  <svg className="h-4 w-4 animate-spin text-white" viewBox="0 0 24 24" fill="none">
                    <circle
                      className="opacity-30"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-80"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                ) : (
                  'Merge to all channels'
                )}
              </button>
              <button
                type="button"
                onClick={onApproveChannel}
                disabled={isSubmitting}
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md border border-emerald-200 px-3 py-2 text-sm font-semibold text-emerald-700 transition hover:border-emerald-300 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmittingChannel ? (
                  <svg
                    className="h-4 w-4 animate-spin text-emerald-600"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-30"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-80"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                ) : (
                  `Merge to ${channelLabel}`
                )}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Merge this update
            </p>
            {isChannelEligibleUpdate && isLoadingPrInfo ? (
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle
                    className="opacity-30"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-80"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span>Loading channel-specific options...</span>
              </div>
            ) : null}
            <button
              type="button"
              onClick={onApproveAll}
              disabled={isSubmitting}
              className="inline-flex items-center justify-center whitespace-nowrap rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? (
                <svg className="h-4 w-4 animate-spin text-white" viewBox="0 0 24 24" fill="none">
                  <circle
                    className="opacity-30"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-80"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              ) : (
                'Merge to all channels'
              )}
            </button>
          </div>
        )}
      </div>
      <div className="mt-6 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          disabled={isSubmitting}
          className="inline-flex items-center justify-center whitespace-nowrap rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </ModalShell>
  );
}

interface RejectModalProps {
  entry: ContextStatusEntry;
  onReject: () => void;
  onClose: () => void;
  isSubmitting: boolean;
}

function RejectModal({entry, onReject, onClose, isSubmitting}: RejectModalProps) {
  return (
    <ModalShell
      title="Reject request"
      subtitle={entry.title}
      onClose={onClose}
      isCloseDisabled={isSubmitting}
    >
      <div className="mt-5 space-y-4">
        <p className="text-sm text-gray-600">
          Rejecting will close this review request in GitHub. You can re-open or create a new one
          later if needed.
        </p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onReject}
            disabled={isSubmitting}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? (
              <svg className="h-4 w-4 animate-spin text-white" viewBox="0 0 24 24" fill="none">
                <circle
                  className="opacity-30"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-80"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              'Reject'
            )}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </ModalShell>
  );
}
