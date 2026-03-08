import React, { useCallback, useEffect, useState } from 'react';
import { Activity, Loader2, RefreshCw } from 'lucide-react';
import { api } from '../utils/api';

export const AuditLog = ({ user, showNotification }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchLogs = useCallback(async () => {
    if (!user || user.role !== 'admin') {
      return;
    }

    setLoading(true);
    setError('');
    try {
      const data = await api.getAuditLogs();
      setLogs(data.logs || []);
    } catch (fetchError) {
      setError(fetchError.message);
      showNotification?.(fetchError.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [showNotification, user]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  if (!user || user.role !== 'admin') {
    return null;
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <Activity className="text-blue-600" size={24} />
          <h3 className="text-xl font-bold text-gray-800">Audit Log</h3>
        </div>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:bg-gray-300"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="animate-spin text-blue-500" size={32} />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      ) : logs.length === 0 ? (
        <p className="text-center text-gray-500 py-8">No audit logs available</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-3 font-semibold text-gray-700">Timestamp</th>
                <th className="text-left py-2 px-3 font-semibold text-gray-700">User</th>
                <th className="text-left py-2 px-3 font-semibold text-gray-700">Action</th>
                <th className="text-left py-2 px-3 font-semibold text-gray-700">Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.slice(0, 10).map((log, idx) => (
                <tr key={idx} className="border-b hover:bg-gray-50">
                  <td className="py-2 px-3">{new Date(log.timestamp).toLocaleString()}</td>
                  <td className="py-2 px-3">{log.username}</td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      log.action === 'upload' ? 'bg-blue-100 text-blue-800' :
                      log.action === 'process' ? 'bg-green-100 text-green-800' :
                      log.action === 'delete' ? 'bg-red-100 text-red-800' :
                      log.action === 'login' ? 'bg-purple-100 text-purple-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-gray-600">{log.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
