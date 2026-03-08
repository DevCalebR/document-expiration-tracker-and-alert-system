import React, { useEffect, useState } from 'react';
import { Cloud, ExternalLink, FileText, Link2Off, Loader2, RefreshCw, ShieldAlert } from 'lucide-react';
import { API_ORIGIN, api } from '../utils/api';

const PROVIDER_COLORS = {
  google_drive: 'bg-blue-500',
  dropbox: 'bg-sky-600',
  onedrive: 'bg-indigo-500'
};

export const CloudStorageConnector = ({ onImport, showNotification, disabled = false }) => {
  const [showModal, setShowModal] = useState(false);
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [files, setFiles] = useState([]);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [connectingProvider, setConnectingProvider] = useState(null);

  const loadProviders = async () => {
    setLoadingProviders(true);
    try {
      const data = await api.getCloudProviders();
      setProviders(data.providers || []);
    } catch (error) {
      showNotification(error.message, 'error');
    } finally {
      setLoadingProviders(false);
    }
  };

  useEffect(() => {
    if (showModal) {
      loadProviders();
    } else {
      setSelectedProvider(null);
      setFiles([]);
      setSelectedFiles(new Set());
      setConnectingProvider(null);
    }
  }, [showModal]);

  useEffect(() => {
    const handleMessage = async (event) => {
      if (event.origin !== API_ORIGIN) {
        return;
      }
      if (event.data?.type !== 'docexpire:cloud-oauth') {
        return;
      }

      setConnectingProvider(null);
      if (event.data.success) {
        showNotification(event.data.message, 'success');
        await loadProviders();
        setSelectedProvider(event.data.provider);
        await loadFiles(event.data.provider);
      } else {
        showNotification(event.data.message || 'Cloud authentication failed', 'error');
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const loadFiles = async (providerId) => {
    setLoadingFiles(true);
    setSelectedFiles(new Set());
    try {
      const data = await api.getCloudFiles(providerId);
      setFiles(data.files || []);
      setSelectedProvider(providerId);
      if ((data.files || []).length === 0) {
        showNotification('No compatible files found for this provider', 'info');
      }
    } catch (error) {
      showNotification(error.message, 'error');
    } finally {
      setLoadingFiles(false);
    }
  };

  const startOAuth = async (providerId) => {
    setConnectingProvider(providerId);
    try {
      const data = await api.getCloudAuthUrl(providerId);
      const popup = window.open(
        data.auth_url,
        `docexpire-${providerId}-oauth`,
        'width=640,height=760,menubar=no,toolbar=no,location=yes,status=no'
      );

      if (!popup) {
        setConnectingProvider(null);
        showNotification('Popup blocked. Allow popups to connect this provider.', 'error');
        return;
      }

      const closeWatcher = window.setInterval(() => {
        if (popup.closed) {
          window.clearInterval(closeWatcher);
          setConnectingProvider((current) => (current === providerId ? null : current));
        }
      }, 500);

      showNotification('Complete the cloud sign-in flow in the popup window.', 'info');
    } catch (error) {
      setConnectingProvider(null);
      showNotification(error.message, 'error');
    }
  };

  const openProvider = async (provider) => {
    if (!provider.configured) {
      showNotification(`${provider.name} is not configured on the backend`, 'warning');
      return;
    }
    if (!provider.connected) {
      await startOAuth(provider.id);
      return;
    }
    await loadFiles(provider.id);
  };

  const toggleFileSelection = (fileId) => {
    setSelectedFiles((previous) => {
      const next = new Set(previous);
      if (next.has(fileId)) {
        next.delete(fileId);
      } else {
        next.add(fileId);
      }
      return next;
    });
  };

  const importSelected = async () => {
    if (selectedFiles.size === 0) {
      showNotification('Select at least one file to import', 'warning');
      return;
    }

    setActionLoading(true);
    try {
      const selected = files.filter((file) => selectedFiles.has(file.id));
      const data = await api.importCloudFiles(selectedProvider, selected);
      onImport(data.imported_files || []);
      showNotification(`Imported ${data.imported_files.length} file(s)`, 'success');
      setShowModal(false);
    } catch (error) {
      showNotification(error.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const disconnect = async () => {
    setActionLoading(true);
    try {
      await api.disconnectCloudProvider(selectedProvider);
      showNotification('Cloud connection removed', 'success');
      await loadProviders();
      setFiles([]);
    } catch (error) {
      showNotification(error.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const activeProvider = providers.find((provider) => provider.id === selectedProvider) || null;

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        disabled={disabled}
        className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        <Cloud size={20} />
        Import from Cloud
      </button>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[85vh] flex flex-col">
            <div className="p-6 border-b flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-800">Cloud Storage</h2>
                <p className="text-sm text-gray-500 mt-1">Connect a provider, browse compatible files, and import them into DocExpire.</p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
                aria-label="Close cloud storage modal"
              >
                &times;
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              {!selectedProvider ? (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-700">Available providers</h3>
                    <button
                      onClick={loadProviders}
                      disabled={loadingProviders}
                      className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:bg-gray-300"
                    >
                      <RefreshCw size={16} className={loadingProviders ? 'animate-spin' : ''} />
                      Refresh
                    </button>
                  </div>

                  {loadingProviders ? (
                    <div className="flex items-center justify-center py-16">
                      <Loader2 className="animate-spin text-blue-500" size={48} />
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {providers.map((provider) => (
                        <button
                          key={provider.id}
                          onClick={() => openProvider(provider)}
                          disabled={actionLoading || connectingProvider === provider.id}
                          className={`${PROVIDER_COLORS[provider.id] || 'bg-gray-600'} text-white p-6 rounded-lg text-left hover:opacity-95 transition-opacity disabled:opacity-60`}
                        >
                          <Cloud size={42} className="mb-3" />
                          <p className="font-semibold text-lg">{provider.name}</p>
                          <p className="text-sm opacity-90 mt-1">
                            {!provider.configured
                              ? 'Backend credentials missing'
                              : provider.connected
                                ? 'Connected and ready to browse'
                                : 'Click to connect with OAuth'}
                          </p>
                          <div className="flex gap-2 mt-4 flex-wrap">
                            <span className={`text-xs px-2 py-1 rounded-full ${provider.configured ? 'bg-white/20' : 'bg-red-500/80'}`}>
                              {provider.configured ? 'Configured' : 'Disabled'}
                            </span>
                            <span className={`text-xs px-2 py-1 rounded-full ${provider.connected ? 'bg-green-500/80' : 'bg-white/20'}`}>
                              {provider.connected ? 'Connected' : 'Not connected'}
                            </span>
                          </div>
                          {connectingProvider === provider.id && (
                            <p className="text-xs mt-3 flex items-center gap-2">
                              <Loader2 className="animate-spin" size={14} />
                              Waiting for OAuth completion…
                            </p>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <div>
                  <div className="mb-4 flex items-center justify-between gap-4 flex-wrap">
                    <div>
                      <h3 className="font-semibold text-gray-800">{activeProvider?.name || selectedProvider}</h3>
                      <p className="text-sm text-gray-500">
                        {activeProvider?.connected ? 'Connected provider' : 'Provider is not connected'}
                      </p>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      <button
                        onClick={() => setSelectedProvider(null)}
                        className="px-3 py-2 text-blue-600 hover:text-blue-800 text-sm"
                      >
                        ← Back to providers
                      </button>
                      <button
                        onClick={() => loadFiles(selectedProvider)}
                        disabled={loadingFiles || actionLoading}
                        className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:bg-gray-300"
                      >
                        <RefreshCw size={16} className={loadingFiles ? 'animate-spin' : ''} />
                        Refresh files
                      </button>
                      {activeProvider?.connected && (
                        <button
                          onClick={disconnect}
                          disabled={actionLoading}
                          className="flex items-center gap-2 px-3 py-2 bg-white border text-red-700 rounded-lg hover:bg-red-50 disabled:bg-gray-100"
                        >
                          <Link2Off size={16} />
                          Disconnect
                        </button>
                      )}
                    </div>
                  </div>

                  {!activeProvider?.configured ? (
                    <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 flex gap-3">
                      <ShieldAlert className="text-yellow-700 shrink-0" size={20} />
                      <div>
                        <p className="font-medium text-yellow-900">Provider credentials are missing</p>
                        <p className="text-sm text-yellow-800 mt-1">
                          Configure this provider on the backend before attempting to connect from the UI.
                        </p>
                      </div>
                    </div>
                  ) : !activeProvider?.connected ? (
                    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                      <p className="text-sm text-blue-800 mb-3">
                        This provider is configured but not connected for your account yet.
                      </p>
                      <button
                        onClick={() => startOAuth(selectedProvider)}
                        disabled={connectingProvider === selectedProvider}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
                      >
                        <ExternalLink size={16} />
                        {connectingProvider === selectedProvider ? 'Waiting for OAuth…' : 'Connect provider'}
                      </button>
                    </div>
                  ) : loadingFiles ? (
                    <div className="flex items-center justify-center py-16">
                      <Loader2 className="animate-spin text-blue-500" size={48} />
                    </div>
                  ) : files.length === 0 ? (
                    <p className="text-center text-gray-500 py-12">No compatible files found for this provider.</p>
                  ) : (
                    <>
                      <div className="space-y-2 mb-4">
                        {files.map((file) => (
                          <div
                            key={file.id}
                            onClick={() => toggleFileSelection(file.id)}
                            className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                              selectedFiles.has(file.id) ? 'bg-blue-50 border-blue-500' : 'hover:bg-gray-50'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="checkbox"
                                checked={selectedFiles.has(file.id)}
                                onChange={() => {}}
                                className="w-4 h-4"
                              />
                              <FileText size={20} className="text-gray-600" />
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-gray-800 truncate">{file.name}</p>
                                <p className="text-xs text-gray-500">{file.size}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      <button
                        onClick={importSelected}
                        disabled={selectedFiles.size === 0 || actionLoading}
                        className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                      >
                        {actionLoading ? 'Importing…' : `Import ${selectedFiles.size} file(s)`}
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};
