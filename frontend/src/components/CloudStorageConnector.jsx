import React, { useState } from 'react';
import { Cloud, FileText, Loader2 } from 'lucide-react';
import { api } from '../utils/api';

export const CloudStorageConnector = ({ onImport, showNotification }) => {
  const [showModal, setShowModal] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState(new Set());

  const providers = [
    { id: 'google_drive', name: 'Google Drive', icon: Cloud, color: 'bg-blue-500' },
    { id: 'dropbox', name: 'Dropbox', icon: Cloud, color: 'bg-blue-600' },
    { id: 'onedrive', name: 'OneDrive', icon: Cloud, color: 'bg-blue-400' }
  ];

  const connectToProvider = async (providerId) => {
    setLoading(true);
    setSelectedProvider(providerId);
    
    try {
      const data = await api.getCloudFiles(providerId);
      setFiles(data.files || []);
      
      if (data.files && data.files.length > 0) {
        showNotification(`Connected to ${providers.find(p => p.id === providerId).name}`, 'success');
      } else {
        showNotification(`No files found or not connected to ${providers.find(p => p.id === providerId).name}`, 'warning');
      }
    } catch (error) {
      showNotification(`Failed to connect. API credentials may not be configured.`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const toggleFileSelection = (fileId) => {
    setSelectedFiles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fileId)) {
        newSet.delete(fileId);
      } else {
        newSet.add(fileId);
      }
      return newSet;
    });
  };

  const importSelected = async () => {
    if (selectedFiles.size === 0) {
      showNotification('Please select files to import', 'warning');
      return;
    }

    setLoading(true);
    try {
      const data = await api.importCloudFiles(selectedProvider, Array.from(selectedFiles));
      onImport(data.imported_files);
      showNotification(`Imported ${data.imported_files.length} files`, 'success');
      setShowModal(false);
      setSelectedFiles(new Set());
      setSelectedProvider(null);
    } catch (error) {
      showNotification('Failed to import files', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
      >
        <Cloud size={20} />
        Import from Cloud
      </button>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-800">Cloud Storage</h2>
              <button onClick={() => { setShowModal(false); setSelectedProvider(null); }} className="text-gray-500 hover:text-gray-700">
                <span className="text-2xl">&times;</span>
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              {!selectedProvider ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {providers.map(provider => {
                    const Icon = provider.icon;
                    return (
                      <button
                        key={provider.id}
                        onClick={() => connectToProvider(provider.id)}
                        className={`${provider.color} text-white p-6 rounded-lg hover:opacity-90 transition-opacity`}
                      >
                        <Icon size={48} className="mx-auto mb-3" />
                        <p className="font-semibold">{provider.name}</p>
                      </button>
                    );
                  })}
                </div>
              ) : loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="animate-spin text-blue-500" size={48} />
                </div>
              ) : (
                <div>
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="font-semibold text-gray-700">Select files to import</h3>
                    <button
                      onClick={() => { setSelectedProvider(null); setFiles([]); }}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      ← Change provider
                    </button>
                  </div>
                  
                  {files.length === 0 ? (
                    <p className="text-center text-gray-500 py-8">No compatible files found or not connected</p>
                  ) : (
                    <>
                      <div className="space-y-2 mb-4">
                        {files.map(file => (
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
                              <div className="flex-1">
                                <p className="font-medium text-gray-800">{file.name}</p>
                                <p className="text-xs text-gray-500">{file.size}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      <button
                        onClick={importSelected}
                        disabled={selectedFiles.size === 0 || loading}
                        className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                      >
                        {loading ? 'Importing...' : `Import ${selectedFiles.size} file(s)`}
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
