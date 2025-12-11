import {useState, useEffect, useRef} from 'react';
import {fetchWithAuth} from './utils/authErrors';

interface OrgUser {
  id: number;
  slack_user_id: string;
  email: string;
  is_org_admin: boolean;
  name?: string | null;
  avatar_url?: string | null;
}

interface OrgUsersData {
  users: OrgUser[];
}

type ConfirmAction = 'make_admin' | 'remove_admin';

interface ConfirmDialog {
  user: OrgUser;
  action: ConfirmAction;
}

export default function OrgUsersPage() {
  const [data, setData] = useState<OrgUsersData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openMenuUserId, setOpenMenuUserId] = useState<number | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialog | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchOrgUsers();
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenuUserId(null);
      }
    };

    if (openMenuUserId !== null) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [openMenuUserId]);

  const fetchOrgUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth('/api/org-users/list');
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmAction = async () => {
    if (!confirmDialog) {
      return;
    }

    const newAdminStatus = confirmDialog.action === 'make_admin';

    setIsUpdating(true);
    try {
      const response = await fetchWithAuth('/api/users/edit', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          slack_user_id: confirmDialog.user.slack_user_id,
          is_org_admin: newAdminStatus,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update user');
      }

      // Refresh the user list
      await fetchOrgUsers();
      setConfirmDialog(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update user');
    } finally {
      setIsUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg text-gray-600">Loading org users...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-800">Error: {error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg text-gray-600">No data available</div>
      </div>
    );
  }

  const users = data.users;

  const getConfirmDialogContent = () => {
    if (!confirmDialog) {
      return null;
    }

    const userName = confirmDialog.user.name || confirmDialog.user.email;

    if (confirmDialog.action === 'make_admin') {
      return {
        title: 'Make user an admin?',
        message: (
          <>
            Are you sure you want to make{' '}
            <span className="font-medium text-gray-900">{userName}</span> an organization admin?
          </>
        ),
        confirmButtonText: 'Make admin',
        confirmButtonClass: 'bg-blue-600 hover:bg-blue-700',
      };
    } else {
      return {
        title: 'Remove admin privileges?',
        message: (
          <>
            Are you sure you want to remove admin privileges from{' '}
            <span className="font-medium text-gray-900">{userName}</span>?
          </>
        ),
        confirmButtonText: 'Remove admin',
        confirmButtonClass: 'bg-red-600 hover:bg-red-700',
      };
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Organization Users</h1>
      </div>

      {users.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
          <p className="text-gray-500">No users found</p>
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
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((user) => {
                const handleCopyUserId = () => {
                  navigator.clipboard.writeText(user.slack_user_id);
                };

                return (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        {user.avatar_url ? (
                          <img
                            src={user.avatar_url}
                            alt={user.name || user.slack_user_id}
                            className="w-8 h-8 rounded-full cursor-pointer"
                            onDoubleClick={handleCopyUserId}
                          />
                        ) : (
                          <svg
                            className="w-8 h-8 text-gray-400 cursor-pointer"
                            fill="currentColor"
                            viewBox="0 0 20 20"
                            onDoubleClick={handleCopyUserId}
                          >
                            <path
                              fillRule="evenodd"
                              d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                              clipRule="evenodd"
                            />
                          </svg>
                        )}
                        <div className="flex flex-col">
                          <span className="text-sm font-medium text-gray-900">
                            {user.name || user.slack_user_id}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900">{user.email}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.is_org_admin ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-blue-100 text-blue-800">
                          Admin
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-gray-100 text-gray-700">
                          Member
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div
                        className="relative inline-block"
                        ref={openMenuUserId === user.id ? menuRef : null}
                      >
                        <button
                          onClick={() =>
                            setOpenMenuUserId(openMenuUserId === user.id ? null : user.id)
                          }
                          className="text-gray-400 hover:text-gray-600 transition-colors p-1"
                        >
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                          </svg>
                        </button>
                        {openMenuUserId === user.id && (
                          <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
                            {user.is_org_admin ? (
                              <button
                                onClick={() => {
                                  setConfirmDialog({user, action: 'remove_admin'});
                                  setOpenMenuUserId(null);
                                }}
                                className="w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-red-50 rounded-lg"
                              >
                                Remove admin
                              </button>
                            ) : (
                              <button
                                onClick={() => {
                                  setConfirmDialog({user, action: 'make_admin'});
                                  setOpenMenuUserId(null);
                                }}
                                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg"
                              >
                                Make admin
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {confirmDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              {getConfirmDialogContent()?.title}
            </h2>
            <p className="text-sm text-gray-600 mb-4">{getConfirmDialogContent()?.message}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  if (!isUpdating) {
                    setConfirmDialog(null);
                  }
                }}
                disabled={isUpdating}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                disabled={isUpdating}
                className={`px-4 py-2 text-white rounded-lg transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed ${getConfirmDialogContent()?.confirmButtonClass}`}
              >
                {isUpdating ? 'Updating...' : getConfirmDialogContent()?.confirmButtonText}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
