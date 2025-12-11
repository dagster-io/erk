import {useState, useEffect} from 'react';
import {useSearchParams, useNavigate} from 'react-router-dom';
import {fetchWithAuth, handleAuthError} from './utils/authErrors';
import {ErrorMessage} from './components/ErrorMessage';
import {TruncatedName} from './components/TruncatedName';
import {TableInputWithAutocomplete} from './components/TableInputWithAutocomplete';

interface Connection {
  connection_name: string;
  connection_type: string | null;
  bot_ids: string[];
  channel_names: string[];
  datasets: string[];
}

function TablePill({
  name,
  truncate = true,
  onClick,
}: {
  name: string;
  truncate?: boolean;
  onClick?: (name: string) => void;
}) {
  const handleClick = async () => {
    if (onClick) {
      onClick(name);
    } else {
      try {
        await navigator.clipboard.writeText(name);
      } catch (err) {
        console.error('Failed to copy to clipboard:', err);
      }
    }
  };

  const title = onClick ? `Click to add: ${name}` : `Click to copy: ${name}`;

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 cursor-pointer transition-colors"
      title={title}
    >
      <svg
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M10.6667 8V6.66667H1.33333V8H10.6667ZM10.6667 5.33333V4H1.33333V5.33333H10.6667ZM10.6667 2.66667V1.33333H1.33333V2.66667H10.6667ZM1.33333 12C0.966667 12 0.652778 11.8694 0.391667 11.6083C0.130556 11.3472 0 11.0333 0 10.6667V1.33333C0 0.966667 0.130556 0.652778 0.391667 0.391667C0.652778 0.130556 0.966667 0 1.33333 0H10.6667C11.0333 0 11.3472 0.130556 11.6083 0.391667C11.8694 0.652778 12 0.966667 12 1.33333V10.6667C12 11.0333 11.8694 11.3472 11.6083 11.6083C11.3472 11.8894 11.0333 12 10.6667 12H1.33333ZM10.6667 10.6667V9.33333H1.33333V10.6667H10.6667Z"
          fill="#67748A"
        />
      </svg>
      {truncate ? (
        <TruncatedName name={name} maxLength={60} mode="left" cursor="pointer" />
      ) : (
        <span>{name}</span>
      )}
    </button>
  );
}

const warehouseIcons: Record<string, string> = {
  snowflake: '/static/snowflake.svg',
  bigquery: '/static/bigquery.svg',
  athena: '/static/Athena.svg',
  redshift: '/static/redshift.svg',
  postgres: '/static/postgresql.svg',
  postgresql: '/static/postgresql.svg',
};

// Connection name for prospector (matches PROSPECTOR_CONNECTION_NAME in slackbot_core.py)
const PROSPECTOR_CONNECTION_NAME = 'bigquery_compass_prospector_us';

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [activeConnection, setActiveConnection] = useState<Connection | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isRemoveModalOpen, setIsRemoveModalOpen] = useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [isChannelsModalOpen, setIsChannelsModalOpen] = useState(false);
  const [selectedDatasets, setSelectedDatasets] = useState<string[]>([]);
  const [tablesToAdd, setTablesToAdd] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const intent = searchParams.get('intent');
  const [availableTables, setAvailableTables] = useState<string[]>([]);
  const [loadingTables, setLoadingTables] = useState(false);
  const [datasetsFetched, setDatasetsFetched] = useState(false);

  useEffect(() => {
    fetchConnections();
  }, []);

  const fetchConnections = async () => {
    setLoading(true);
    setError(null);
    try {
      // First fetch connections without datasets (fast)
      const response = await fetchWithAuth('/api/connections/list');
      const data = await response.json();
      const rawConnections = (data.connections || []) as Array<Connection & {datasets?: string[]}>;
      const normalizedConnections = rawConnections.map((connection) => ({
        ...connection,
        datasets: connection.datasets ?? [],
      }));
      setConnections(normalizedConnections);
      setLoading(false);

      // Then fetch datasets in the background, but only once to avoid repeated failures
      if (!datasetsFetched) {
        setDatasetsLoading(true);
        try {
          const datasetsResponse = await fetchWithAuth('/api/connections/list_datasets');
          const datasetsData = await datasetsResponse.json();
          const datasetMap = (datasetsData.dataset_map || {}) as Record<string, string[]>;

          // Merge datasets into connections
          const updatedConnections = normalizedConnections.map((connection) => ({
            ...connection,
            datasets: datasetMap[connection.connection_name] || [],
          }));
          setConnections(updatedConnections);
          setDatasetsFetched(true);
        } catch (datasetsErr) {
          // Silently fail - connections are already displayed
          // Mark as fetched to prevent retry loops
          console.error('Failed to load datasets:', datasetsErr);
          setDatasetsFetched(true);
        } finally {
          setDatasetsLoading(false);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setLoading(false);
    }
  };

  const fetchAvailableTables = async (connectionName: string) => {
    setLoadingTables(true);
    try {
      const url = `/api/connections/tables?connection_name=${encodeURIComponent(connectionName)}`;
      const response = await fetchWithAuth(url);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();

      if (data.success && data.tables) {
        const tableNames = data.tables.map((t: {name: string}) => t.name);
        setAvailableTables(tableNames);
      } else {
        setAvailableTables([]);
      }
    } catch (err) {
      console.error('Failed to fetch tables:', err);
      setAvailableTables([]);
    } finally {
      setLoadingTables(false);
    }
  };

  const resetModalState = () => {
    setActiveConnection(null);
    setSelectedDatasets([]);
    setTablesToAdd([]);
    setIsEditModalOpen(false);
    setIsRemoveModalOpen(false);
    setIsViewModalOpen(false);
    setIsChannelsModalOpen(false);
    setAvailableTables([]);
  };

  const openEditModal = (connection: Connection) => {
    setActiveConnection(connection);
    setSelectedDatasets([]);
    setTablesToAdd([]);
    setIsEditModalOpen(true);
    fetchAvailableTables(connection.connection_name);
  };

  const openRemoveModal = (connection: Connection) => {
    if (connection.datasets.length === 0) {
      return;
    }
    setActiveConnection(connection);
    setSelectedDatasets([]);
    setIsRemoveModalOpen(true);
  };

  const openViewModal = (connection: Connection) => {
    if (connection.datasets.length === 0) {
      return;
    }
    setActiveConnection(connection);
    setIsViewModalOpen(true);
  };

  const openChannelsModal = (connection: Connection) => {
    if (connection.channel_names.length === 0) {
      return;
    }
    setActiveConnection(connection);
    setIsChannelsModalOpen(true);
  };

  const toggleDatasetSelection = (datasetName: string) => {
    setSelectedDatasets((prev) =>
      prev.includes(datasetName)
        ? prev.filter((name) => name !== datasetName)
        : [...prev, datasetName],
    );
  };

  const addTableToList = (tableName: string) => {
    setTablesToAdd((prev) => [...prev, tableName]);
  };

  const removeTableFromList = (tableName: string) => {
    setTablesToAdd((prev) => prev.filter((t) => t !== tableName));
  };

  const handleDatasetSubmit = async () => {
    if (!activeConnection) {
      return;
    }

    if (tablesToAdd.length === 0) {
      alert('Add at least one dataset (fully qualified table name).');
      return;
    }

    setIsSubmitting(true);
    const connectionName = activeConnection.connection_name;

    try {
      const response = await fetch('/api/connections/datasets/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          connection_name: connectionName,
          datasets: tablesToAdd,
        }),
      });

      await handleAuthError(response);

      if (!response.ok) {
        let errorMessage = 'Failed to start dataset update';
        try {
          const errorData = await response.json();
          if (errorData.error) {
            errorMessage = errorData.error;
          }
        } catch {
          // Ignore parsing errors and use default message
        }
        throw new Error(errorMessage);
      }

      setFeedback(`Started dataset update for ${connectionName}. Redirecting to progress page...`);
      resetModalState();

      // Redirect to sync progress page after a short delay
      setTimeout(() => {
        navigate(`/dataset-sync?connection=${encodeURIComponent(connectionName)}`);
      }, 1500);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start dataset update');
      setIsSubmitting(false);
    }
  };

  const handleDatasetRemoval = async () => {
    if (!activeConnection) {
      return;
    }

    if (selectedDatasets.length === 0) {
      alert('Select at least one dataset to remove.');
      return;
    }

    setIsSubmitting(true);
    const connectionName = activeConnection.connection_name;

    try {
      const response = await fetch('/api/connections/datasets/remove', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          connection_name: connectionName,
          datasets: selectedDatasets,
        }),
      });

      await handleAuthError(response);

      if (!response.ok) {
        let errorMessage = 'Failed to start dataset removal';
        try {
          const errorData = await response.json();
          if (errorData.error) {
            errorMessage = errorData.error;
          }
        } catch {
          // Ignore parsing errors and use default message
        }
        throw new Error(errorMessage);
      }

      setFeedback(
        `Started dataset removal for ${connectionName}. Check Slack channel for progress updates.`,
      );
      resetModalState();
      await fetchConnections();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start dataset removal');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg text-gray-600">Loading connections...</div>
      </div>
    );
  }

  if (error) {
    return <ErrorMessage message={error} />;
  }

  return (
    <div className="max-w-full mx-auto px-8 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Connections</h1>
        <a
          href="/connections/add-connection"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
              clipRule="evenodd"
            />
          </svg>
          Add connection
        </a>
      </div>

      {intent === 'add-datasets' && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
          <p className="font-medium">Add or update datasets</p>
          <p className="mt-1">
            Select the connection you want to update from the list below, then launch the setup
            wizard to pick new datasets. You can restart the wizard anytime via the{' '}
            <a className="underline" href="/onboarding/connections">
              connection setup flow
            </a>
            .
          </p>
        </div>
      )}

      {intent === 'remove-datasets' && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-medium">Remove datasets</p>
          <p className="mt-1">
            Review the datasets linked to each connection below. To remove datasets, open the setup
            wizard from the{' '}
            <a className="underline" href="/onboarding/connections">
              connection flow
            </a>{' '}
            and uncheck the tables you no longer need.
          </p>
        </div>
      )}

      {feedback && (
        <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-900">
          <p>{feedback}</p>
        </div>
      )}

      {connections.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No connections found</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-2/5">
                  Tables
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Channels
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Control
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {connections.map((connection, index) => {
                const isProspector = connection.connection_name === PROSPECTOR_CONNECTION_NAME;
                const dialectType = connection.connection_type?.toLowerCase() || 'unknown';
                const iconSrc = isProspector
                  ? '/static/compass-logo-mark.svg'
                  : warehouseIcons[dialectType];
                const maxVisibleTables = 3;
                const visibleTables = connection.datasets.slice(0, maxVisibleTables);
                const remainingTablesCount = connection.datasets.length - maxVisibleTables;
                const maxVisibleChannels = 3;
                const visibleChannels = connection.channel_names.slice(0, maxVisibleChannels);
                const remainingChannelsCount = connection.channel_names.length - maxVisibleChannels;
                return (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {iconSrc ? (
                          <img src={iconSrc} alt={dialectType} className="w-6 h-6" />
                        ) : (
                          <div className="w-6 h-6 rounded bg-gray-200 flex items-center justify-center">
                            <svg
                              className="w-4 h-4 text-gray-500"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z" />
                              <path d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z" />
                              <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z" />
                            </svg>
                          </div>
                        )}
                        <div className="flex flex-col">
                          <span className="text-sm font-medium text-gray-900 capitalize">
                            {isProspector ? 'Prospecting Data by Compass' : dialectType}
                          </span>
                          {!isProspector && (
                            <span className="text-xs text-gray-500">
                              <TruncatedName name={connection.connection_name} maxLength={40} />
                            </span>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-2">
                        {datasetsLoading ? (
                          <span className="text-sm text-gray-500 italic">Loading tables...</span>
                        ) : connection.datasets.length > 0 ? (
                          <>
                            {visibleTables.map((dataset) => (
                              <TablePill key={dataset} name={dataset} />
                            ))}
                            {remainingTablesCount > 0 && (
                              <button
                                onClick={() => openViewModal(connection)}
                                className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100"
                              >
                                +{remainingTablesCount}
                              </button>
                            )}
                          </>
                        ) : (
                          <span className="text-sm text-gray-500">No tables yet</span>
                        )}
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-2">
                        {connection.channel_names.length > 0 ? (
                          <>
                            {visibleChannels.map((channel, channelIndex) => (
                              <span
                                key={channelIndex}
                                className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-blue-50 text-blue-700"
                              >
                                #{channel}
                              </span>
                            ))}
                            {remainingChannelsCount > 0 && (
                              <button
                                onClick={() => openChannelsModal(connection)}
                                className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100"
                              >
                                +{remainingChannelsCount}
                              </button>
                            )}
                          </>
                        ) : (
                          <span className="text-sm text-gray-500">No channels</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEditModal(connection)}
                          disabled={isSubmitting}
                          className="text-gray-400 hover:text-blue-600 transition-colors disabled:opacity-50"
                          title="Add or update datasets"
                        >
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => openRemoveModal(connection)}
                          disabled={isSubmitting || connection.datasets.length === 0}
                          className="text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                          title="Remove datasets"
                        >
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path
                              fillRule="evenodd"
                              d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                              clipRule="evenodd"
                            />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {isEditModalOpen && activeConnection && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={() => !isSubmitting && resetModalState()}
        >
          <div
            className="bg-white rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="overflow-y-auto flex-1 p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Add or update datasets</h2>
              <p className="text-sm text-gray-600 mb-4">
                Connection{' '}
                <span className="font-medium text-gray-900">
                  <TruncatedName name={activeConnection.connection_name} maxLength={40} />
                </span>{' '}
                powers{' '}
                {activeConnection.channel_names.length === 0 ? (
                  'no channels yet'
                ) : (
                  <>
                    {activeConnection.channel_names.map((channel, idx) => (
                      <span key={channel}>
                        {idx > 0 && ', '}
                        <span className="font-medium text-blue-600">#{channel}</span>
                      </span>
                    ))}
                  </>
                )}
                .
              </p>
              <div className="mb-4 rounded-lg border border-gray-200 p-4 text-sm text-gray-700">
                <p className="font-medium mb-1">Current datasets</p>
                <p className="text-xs text-gray-500 mb-2">Click to add to refresh list</p>
                {activeConnection.datasets.length > 0 ? (
                  <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
                    {activeConnection.datasets.map((dataset) => (
                      <TablePill
                        key={dataset}
                        name={dataset}
                        onClick={(name) => {
                          addTableToList(name);
                        }}
                      />
                    ))}
                  </div>
                ) : (
                  <p>No datasets have been added yet.</p>
                )}
              </div>

              <TableInputWithAutocomplete
                selectedTables={tablesToAdd}
                availableTables={availableTables}
                loadingTables={loadingTables}
                disabled={isSubmitting}
                onAddTable={addTableToList}
                onRemoveTable={removeTableFromList}
              />
            </div>
            <div className="border-t border-gray-200 p-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  if (!isSubmitting) {
                    resetModalState();
                  }
                }}
                disabled={isSubmitting}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDatasetSubmit}
                disabled={isSubmitting || tablesToAdd.length === 0}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Starting...' : 'Start dataset update'}
              </button>
            </div>
          </div>
        </div>
      )}

      {isRemoveModalOpen && activeConnection && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={() => !isSubmitting && resetModalState()}
        >
          <div
            className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Remove datasets</h2>
            <p className="text-sm text-gray-600 mb-4">
              Remove documentation and synced data for connection{' '}
              <span className="font-medium">
                <TruncatedName name={activeConnection.connection_name} maxLength={40} />
              </span>
              .
            </p>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {activeConnection.datasets.map((dataset) => (
                <label
                  key={dataset}
                  className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedDatasets.includes(dataset)}
                    onChange={() => toggleDatasetSelection(dataset)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    disabled={isSubmitting}
                  />
                  <span className="font-mono text-xs text-gray-700">{dataset}</span>
                </label>
              ))}
            </div>
            <p className="mt-3 text-xs text-gray-500">
              Selected datasets will be removed from documentation and no longer appear in Compass
              threads.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  if (!isSubmitting) {
                    resetModalState();
                  }
                }}
                disabled={isSubmitting}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDatasetRemoval}
                disabled={isSubmitting || selectedDatasets.length === 0}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Starting...' : 'Remove datasets'}
              </button>
            </div>
          </div>
        </div>
      )}

      {isViewModalOpen && activeConnection && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={resetModalState}
        >
          <div
            className="bg-white rounded-lg p-6 max-w-5xl w-auto mx-4 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Datasets</h2>
            <p className="text-sm text-gray-600 mb-4">
              Datasets for connection{' '}
              <span className="font-medium">{activeConnection.connection_name}</span>
            </p>
            <div className="flex flex-wrap gap-2 max-h-96 overflow-y-auto">
              {activeConnection.datasets.map((dataset) => (
                <TablePill key={dataset} name={dataset} truncate={false} />
              ))}
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={resetModalState}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {isChannelsModalOpen && activeConnection && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={resetModalState}
        >
          <div
            className="bg-white rounded-lg p-6 max-w-3xl w-auto mx-4 max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Channels</h2>
            <p className="text-sm text-gray-600 mb-4">
              Channels for connection{' '}
              <span className="font-medium">{activeConnection.connection_name}</span>
            </p>
            <div className="flex flex-wrap gap-2 max-h-96 overflow-y-auto">
              {activeConnection.channel_names.map((channel) => (
                <span
                  key={channel}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-blue-50 text-blue-700"
                >
                  #{channel}
                </span>
              ))}
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={resetModalState}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
