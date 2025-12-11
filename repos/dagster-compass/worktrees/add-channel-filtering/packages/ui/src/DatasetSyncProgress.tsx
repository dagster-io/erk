import {useState, useEffect} from 'react';
import {useSearchParams} from 'react-router-dom';
import {useDocumentTitle} from './hooks/useDocumentTitle';
import {HelpFooter} from './components/HelpFooter';

type DatasetStatus = 'not_started' | 'processing' | 'completed' | 'failed';
type WorkflowStatus = 'in_progress' | 'completed' | 'failed' | 'not_found' | 'unknown';

interface DatasetProgress {
  table_name: string;
  status: DatasetStatus;
  message: string;
}

interface SyncDetailsResponse {
  workflow_id: string;
  connection_name: string;
  status: WorkflowStatus;
  datasets: DatasetProgress[];
  pr_url?: string;
  error?: string;
}

const POLL_INTERVAL = 5000; // Poll every 5 seconds

export default function DatasetSyncProgress() {
  const [searchParams] = useSearchParams();
  const connectionName = searchParams.get('connection') || '';

  useDocumentTitle(`Syncing ${connectionName}`);

  const [syncDetails, setSyncDetails] = useState<SyncDetailsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!connectionName) {
      setError('Missing connection name parameter');
      setLoading(false);
      return;
    }

    let pollInterval: ReturnType<typeof setInterval> | null = null;

    const fetchSyncDetails = async () => {
      try {
        const response = await fetch(
          `/api/dataset-sync/details?connection_name=${encodeURIComponent(connectionName)}`,
        );

        if (!response.ok) {
          if (response.status === 404) {
            setError('No sync workflow found for this connection');
            setLoading(false);
            return;
          }
          if (response.status === 401) {
            setError('Authentication required. Please log in to view sync progress.');
            setLoading(false);
            return;
          }
          throw new Error(`Failed to fetch sync details: ${response.statusText}`);
        }

        const data: SyncDetailsResponse = await response.json();
        setSyncDetails(data);
        setLoading(false);

        // Stop polling if workflow is completed or failed
        if (data.status === 'completed' || data.status === 'failed') {
          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
          }
        }
      } catch (err) {
        console.error('Error fetching sync details:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch sync details');
        setLoading(false);
      }
    };

    // Initial fetch
    fetchSyncDetails();

    // Set up polling for in-progress workflows
    pollInterval = setInterval(fetchSyncDetails, POLL_INTERVAL);

    // Cleanup
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [connectionName]);

  const getStatusIcon = (status: DatasetStatus) => {
    switch (status) {
      case 'completed':
        return <i className="ph-fill ph-check-circle text-green-600 text-xl"></i>;
      case 'failed':
        return <i className="ph-fill ph-x-circle text-red-600 text-xl"></i>;
      case 'processing':
        return (
          <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
        );
      case 'not_started':
        return <i className="ph ph-circle text-gray-400 text-xl"></i>;
      default:
        return <i className="ph ph-circle text-gray-400 text-xl"></i>;
    }
  };

  const getStatusColor = (status: DatasetStatus) => {
    switch (status) {
      case 'completed':
        return 'text-green-700';
      case 'failed':
        return 'text-red-700';
      case 'processing':
        return 'text-blue-700';
      case 'not_started':
        return 'text-gray-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusLabel = (status: DatasetStatus) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'processing':
        return 'Processing';
      case 'not_started':
        return 'Pending';
      default:
        return 'Unknown';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-lg text-gray-700">Loading sync progress...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-8 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <div className="flex items-start gap-3">
              <i className="ph-fill ph-warning-circle text-red-600 text-2xl flex-shrink-0"></i>
              <div>
                <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Progress</h3>
                <p className="text-red-800">{error}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!syncDetails) {
    return (
      <div className="flex items-center justify-center py-32">
        <p className="text-lg text-gray-700">No sync details available</p>
      </div>
    );
  }

  const completedCount = syncDetails.datasets.filter((d) => d.status === 'completed').length;
  const failedCount = syncDetails.datasets.filter((d) => d.status === 'failed').length;
  const totalCount = syncDetails.datasets.length;
  const isComplete = syncDetails.status === 'completed';
  const isFailed = syncDetails.status === 'failed';

  return (
    <div className="py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">Dataset Sync Progress</h1>
          <p className="text-lg text-gray-600">
            Connection: <span className="font-medium">{syncDetails.connection_name}</span>
          </p>
        </div>

        {/* Overall Status Card */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Overall Status</h2>
            {isComplete && (
              <span className="flex items-center gap-2 text-green-700 font-medium">
                <i className="ph-fill ph-check-circle text-xl"></i>
                Complete
              </span>
            )}
            {isFailed && (
              <span className="flex items-center gap-2 text-red-700 font-medium">
                <i className="ph-fill ph-x-circle text-xl"></i>
                Failed
              </span>
            )}
            {syncDetails.status === 'in_progress' && (
              <span className="flex items-center gap-2 text-blue-700 font-medium">
                <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                In Progress
              </span>
            )}
          </div>

          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>
                {completedCount} of {totalCount} datasets processed
              </span>
              <span>{Math.round((completedCount / totalCount) * 100)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{width: `${(completedCount / totalCount) * 100}%`}}
              ></div>
            </div>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-green-600">{completedCount}</div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-600">
                {totalCount - completedCount - failedCount}
              </div>
              <div className="text-sm text-gray-600">Remaining</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">{failedCount}</div>
              <div className="text-sm text-gray-600">Failed</div>
            </div>
          </div>

          {/* Context Update Link */}
          {syncDetails.pr_url && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <a
                href={syncDetails.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-brand hover:text-blue-brand-dark font-medium"
              >
                <i className="ph-bold ph-file-text text-xl"></i>
                View Context Update
                <i className="ph-bold ph-arrow-square-out text-sm"></i>
              </a>
            </div>
          )}
        </div>

        {/* Dataset List */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Dataset Details</h2>

          <div className="space-y-3">
            {syncDetails.datasets.map((dataset, index) => (
              <div
                key={index}
                className="flex items-start gap-4 p-4 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
              >
                <div className="flex-shrink-0 mt-0.5">{getStatusIcon(dataset.status)}</div>
                <div className="flex-grow min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-base font-medium text-gray-900 truncate">
                      {dataset.table_name}
                    </h3>
                    <span
                      className={`text-sm font-medium ${getStatusColor(dataset.status)} shrink-0`}
                    >
                      {getStatusLabel(dataset.status)}
                    </span>
                  </div>
                  {dataset.message && (
                    <p className="text-sm text-gray-600 break-words">{dataset.message}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Error Details */}
        {syncDetails.error && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-red-900 mb-2">Error Details</h3>
            <p className="text-red-800">{syncDetails.error}</p>
          </div>
        )}

        {/* Footer */}
        <HelpFooter />
      </div>
    </div>
  );
}
