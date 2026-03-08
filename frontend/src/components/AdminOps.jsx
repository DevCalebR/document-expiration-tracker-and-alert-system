import React, { useEffect, useState } from 'react';
import { Mail, RefreshCw, Server, ShieldCheck, Zap } from 'lucide-react';
import { api } from '../utils/api';

const DependencyPill = ({ label, status, detail }) => (
  <div className="rounded-lg border bg-gray-50 px-3 py-2">
    <div className="flex items-center justify-between gap-3">
      <span className="text-sm font-medium text-gray-800">{label}</span>
      <span className={`text-xs px-2 py-1 rounded-full ${status === 'ok' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
        {status}
      </span>
    </div>
    {detail && <p className="text-xs text-gray-500 mt-1 break-all">{detail}</p>}
  </div>
);

export const AdminOps = ({ user, showNotification }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await api.getAdminStatus();
      setStatus(data);
    } catch (error) {
      showNotification(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchStatus();
    }
  }, [user]);

  if (!user || user.role !== 'admin') {
    return null;
  }

  const runAction = async (name, fn, successMessage) => {
    setAction(name);
    try {
      const data = await fn();
      showNotification(data.message || successMessage, 'success');
      await fetchStatus();
    } catch (error) {
      showNotification(error.message, 'error');
    } finally {
      setAction(null);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
      <div className="flex items-center justify-between gap-4 flex-wrap mb-5">
        <div className="flex items-center gap-3">
          <Server className="text-blue-600" size={24} />
          <div>
            <h3 className="text-xl font-bold text-gray-800">System Operations</h3>
            <p className="text-sm text-gray-600">Admin-only health, queue, email, and cloud configuration status.</p>
          </div>
        </div>
        <button
          onClick={fetchStatus}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:bg-gray-300"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="text-sm text-gray-500">Loading system status…</div>
      ) : status ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            <div className="rounded-xl bg-blue-50 border border-blue-200 p-4">
              <p className="text-sm text-blue-700">Environment</p>
              <p className="text-2xl font-bold text-blue-900">{status.environment}</p>
              <p className="text-xs text-blue-700 mt-1">{status.service} v{status.version}</p>
            </div>
            <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
              <p className="text-sm text-gray-600">Queue mode</p>
              <p className="text-2xl font-bold text-gray-900">{status.queue?.mode || 'unknown'}</p>
              <p className="text-xs text-gray-500 mt-1">Queued: {status.queue?.queued ?? 'n/a'}</p>
            </div>
            <div className="rounded-xl bg-green-50 border border-green-200 p-4">
              <p className="text-sm text-green-700">Email</p>
              <p className="text-2xl font-bold text-green-900">
                {status.email?.configured ? 'Configured' : 'Disabled'}
              </p>
              <p className="text-xs text-green-700 mt-1">SMTP-backed admin alerts and verification</p>
            </div>
            <div className="rounded-xl bg-purple-50 border border-purple-200 p-4">
              <p className="text-sm text-purple-700">Cloud providers</p>
              <p className="text-2xl font-bold text-purple-900">
                {Object.values(status.cloud || {}).filter((provider) => provider.configured).length}
              </p>
              <p className="text-xs text-purple-700 mt-1">OAuth providers configured on the backend</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {Object.entries(status.dependencies || {}).map(([name, dependency]) => (
              <DependencyPill
                key={name}
                label={name}
                status={dependency.status}
                detail={dependency.detail}
              />
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button
              onClick={() => runAction('alerts', api.runAlerts, 'Alert run enqueued')}
              disabled={action !== null}
              className="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
            >
              <Zap size={18} />
              {action === 'alerts' ? 'Queueing alerts…' : 'Trigger alerts run'}
            </button>
            <button
              onClick={() => runAction('email', api.sendTestEmail, 'Test email sent')}
              disabled={action !== null || !status.email?.configured}
              className="flex items-center justify-center gap-2 px-4 py-3 bg-white border text-gray-900 rounded-lg hover:bg-gray-50 disabled:bg-gray-100"
            >
              <Mail size={18} />
              {action === 'email' ? 'Sending test email…' : status.email?.configured ? 'Send test email' : 'SMTP not configured'}
            </button>
            <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 border rounded-lg">
              <ShieldCheck className="text-green-600" size={18} />
              <div>
                <p className="text-sm font-medium text-gray-800">Queue counters</p>
                <p className="text-xs text-gray-500">
                  Started {status.queue?.started ?? 'n/a'} • Failed {status.queue?.failed ?? 'n/a'} • Finished {status.queue?.finished ?? 'n/a'}
                </p>
              </div>
            </div>
          </div>

          {!status.email?.configured && (
            <p className="text-sm text-amber-700 mt-4">
              SMTP is disabled. Registration falls back to manual verification links only in development and test environments.
            </p>
          )}
        </>
      ) : (
        <div className="text-sm text-red-600">System status is unavailable.</div>
      )}
    </div>
  );
};
