import {useState, useEffect} from 'react';
import {fetchWithAuth} from './utils/authErrors';
import {ErrorMessage} from './components/ErrorMessage';
import {TruncatedName} from './components/TruncatedName';

interface Channel {
  bot_id: string;
  channel_name: string;
  connection_names: string[];
}

interface PlanLimits {
  num_channels: number;
  allow_additional_channels: boolean;
}

interface ChannelsData {
  channels: Channel[];
  plan_limits: PlanLimits | null;
  available_connections: string[];
}

export default function ChannelsPage() {
  const [data, setData] = useState<ChannelsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [newChannelName, setNewChannelName] = useState('');
  const [selectedConnectionNames, setSelectedConnectionNames] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchChannels();
  }, []);

  const fetchChannels = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth('/api/channels/list');
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const canCreateChannel = (): boolean => {
    if (!data || !data.plan_limits) {
      return false;
    }
    const currentCount = data.channels.length;
    return (
      currentCount < data.plan_limits.num_channels || data.plan_limits.allow_additional_channels
    );
  };

  const getChannelUsageText = (): string => {
    if (!data || !data.plan_limits) {
      return '';
    }
    const currentCount = data.channels.length;
    const allowed = data.plan_limits.num_channels;
    if (data.plan_limits.allow_additional_channels) {
      return `Using ${currentCount} of ${allowed} plan base channels`;
    }
    return `Using ${currentCount} of ${allowed} channels`;
  };

  const handleAddChannel = async () => {
    if (!newChannelName.trim()) {
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch('/api/channels/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          channel_name: newChannelName.trim(),
          connection_names: selectedConnectionNames,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create channel');
      }

      setIsAddModalOpen(false);
      setNewChannelName('');
      setSelectedConnectionNames([]);
      await fetchChannels();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create channel');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditChannel = (channel: Channel) => {
    setEditingChannel(channel);
    setSelectedConnectionNames(channel.connection_names);
    setIsEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editingChannel) {
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch('/api/channels/update', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          bot_id: editingChannel.bot_id,
          connection_names: selectedConnectionNames,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update channel');
      }

      setIsEditModalOpen(false);
      setEditingChannel(null);
      setSelectedConnectionNames([]);
      await fetchChannels();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update channel');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteChannel = async (channel: Channel) => {
    if (!confirm(`Are you sure you want to delete channel #${channel.channel_name}?`)) {
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch('/api/channels/delete', {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          bot_id: channel.bot_id,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete channel');
      }

      await fetchChannels();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete channel');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleConnectionSelection = (connectionName: string) => {
    setSelectedConnectionNames((prev) =>
      prev.includes(connectionName)
        ? prev.filter((name) => name !== connectionName)
        : [...prev, connectionName],
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg text-gray-600">Loading channels...</div>
      </div>
    );
  }

  if (error) {
    return <ErrorMessage message={error} />;
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg text-gray-600">No data available</div>
      </div>
    );
  }

  const channels = data.channels;
  const availableConnections = data.available_connections;
  const canCreate = canCreateChannel();
  const usageText = getChannelUsageText();

  return (
    <>
      <div className="max-w-7xl mx-auto px-8 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Channels</h1>
          <button
            onClick={() => setIsAddModalOpen(true)}
            disabled={!canCreate || submitting}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clipRule="evenodd"
              />
            </svg>
            Add channel
          </button>
        </div>

        {usageText && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">{usageText}</p>
          </div>
        )}

        {/* Plan limit message */}
        {!canCreate && data.plan_limits && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              📊 You've reached your plan limit of {data.plan_limits.num_channels} channels.{' '}
              <a href="/billing" className="underline font-medium hover:text-yellow-900">
                Upgrade your plan
              </a>{' '}
              to add more channels.
            </p>
          </div>
        )}

        {channels.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <p className="text-gray-500">No channels found</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Connections
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Controls
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {channels.map((channel) => (
                  <tr key={channel.bot_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <svg
                          className="w-5 h-5 text-gray-400"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                        <span className="text-sm font-medium text-gray-900">
                          #{channel.channel_name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-2">
                        {channel.connection_names.length > 0 ? (
                          channel.connection_names.map((connectionName, idx) => (
                            <span
                              key={idx}
                              className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-gray-100 text-gray-700"
                            >
                              <TruncatedName name={connectionName} maxLength={40} />
                            </span>
                          ))
                        ) : (
                          <span className="text-sm text-gray-500">No connections</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleEditChannel(channel)}
                          disabled={submitting}
                          className="text-gray-400 hover:text-blue-600 transition-colors disabled:opacity-50"
                          title="Edit channel"
                        >
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDeleteChannel(channel)}
                          disabled={submitting}
                          className="text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                          title="Delete channel"
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Channel Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Add Channel</h2>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Channel Name</label>
              <div className="flex items-center">
                <span className="text-gray-500 mr-1">#</span>
                <input
                  type="text"
                  value={newChannelName}
                  onChange={(e) => setNewChannelName(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="channel-name"
                  autoFocus
                  disabled={submitting}
                />
              </div>
            </div>

            {availableConnections.length > 0 && (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Connections (Optional)
                </label>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {availableConnections.map((connectionName) => (
                    <label
                      key={connectionName}
                      className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedConnectionNames.includes(connectionName)}
                        onChange={() => toggleConnectionSelection(connectionName)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                        disabled={submitting}
                      />
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">
                          <TruncatedName name={connectionName} maxLength={50} />
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setIsAddModalOpen(false);
                  setNewChannelName('');
                  setSelectedConnectionNames([]);
                }}
                disabled={submitting}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAddChannel}
                disabled={!newChannelName.trim() || submitting}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {submitting ? 'Creating...' : 'Add Channel'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Channel Modal */}
      {isEditModalOpen && editingChannel && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Edit Channel: #{editingChannel.channel_name}
            </h2>

            {availableConnections.length > 0 ? (
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Connections
                </label>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {availableConnections.map((connectionName) => (
                    <label
                      key={connectionName}
                      className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedConnectionNames.includes(connectionName)}
                        onChange={() => toggleConnectionSelection(connectionName)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                        disabled={submitting}
                      />
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">
                          <TruncatedName name={connectionName} maxLength={50} />
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">
                  No connections available. Add a connection first using the Connections page.
                </p>
              </div>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingChannel(null);
                  setSelectedConnectionNames([]);
                }}
                disabled={submitting}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={submitting}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {submitting ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
