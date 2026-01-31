import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Calendar, Download, FileText, Loader2, LogOut, Upload } from 'lucide-react';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { Notification } from './components/Notification';
import { FileUploader } from './components/FileUploader';
import { CloudStorageConnector } from './components/CloudStorageConnector';
import { AIInsights } from './components/AIInsights';
import { AuditLog } from './components/AuditLog';
import { ResultsTable } from './components/ResultsTable';
import { TextPreview } from './components/TextPreview';
import { VerifyEmail } from './components/VerifyEmail';
import { api, getAuthToken } from './utils/api';

function AppContent() {
  const [user, setUser] = useState(null);
  const [mode, setMode] = useState('login'); // login | register
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [processedResults, setProcessedResults] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [notification, setNotification] = useState(null);
  const [expandedFiles, setExpandedFiles] = useState(new Set());
  const [previewFile, setPreviewFile] = useState(null);

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      // optional future enhancement: fetch user profile
    }
  }, []);

  const showNotification = (message, type = 'info') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const handleLogin = (userData) => {
    setUser(userData);
    showNotification(`Welcome, ${userData.full_name}!`, 'success');
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    setUploadedFiles([]);
    setProcessedResults([]);
    showNotification('Logged out successfully', 'success');
  };

  if (!user) {
    return mode === 'login' ? (
      <Login onLogin={handleLogin} onRegister={() => setMode('register')} />
    ) : (
      <Register onBackToLogin={() => setMode('login')} />
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {notification && (
        <Notification
          message={notification.message}
          type={notification.type}
          onClose={() => setNotification(null)}
        />
      )}

      {previewFile && (
        <TextPreview
          filename={previewFile}
          onClose={() => setPreviewFile(null)}
        />
      )}

      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Calendar className="text-blue-600" size={48} />
              <div>
                <h1 className="text-4xl font-bold text-gray-800">DocExpire</h1>
                <p className="text-gray-600">Enterprise Document Management</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="font-medium text-gray-800">{user.full_name}</p>
                <p className="text-sm text-gray-600">
                  <span className={`px-2 py-1 rounded text-xs ${
                    user.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
                  }`}>
                    {user.role}
                  </span>
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors"
              >
                <LogOut size={20} />
                Logout
              </button>
            </div>
          </div>
        </header>

        {user.role === 'admin' && <AuditLog user={user} />}

        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6 flex items-center gap-2">
            <Upload size={24} />
            Upload Documents
          </h2>
          
          <FileUploader
            onFilesUploaded={(s, f) => {
              setUploadedFiles(prev => [...prev, ...s]);
              if (s.length) showNotification(`${s.length} file(s) uploaded`, 'success');
              if (f.length) showNotification(`${f.length} failed`, 'error');
            }}
            isUploading={isUploading}
            setIsUploading={setIsUploading}
            user={user}
            showNotification={showNotification}
          />

          {uploadedFiles.length > 0 && (
            <div className="mt-6 flex gap-4 flex-wrap">
              <button
                onClick={async () => {
                  if (!uploadedFiles.length) return;
                  setIsProcessing(true);
                  try {
                    const filenames = uploadedFiles.map(f => f.saved_filename);
                    const data = await api.processFiles(filenames);
                    setProcessedResults(data.summary);
                    setExpandedFiles(new Set(data.summary.map((_, idx) => idx)));
                    showNotification(`Processed ${data.files_processed} file(s)`, 'success');
                  } catch (e) {
                    showNotification(e.message, 'error');
                  } finally {
                    setIsProcessing(false);
                  }
                }}
                disabled={isProcessing}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
              >
                {isProcessing ? <Loader2 className="animate-spin" size={20} /> : <Calendar size={20} />}
                {isProcessing ? 'Processing...' : 'Process Files'}
              </button>

              <CloudStorageConnector 
                onImport={(files) => setUploadedFiles(prev => [...prev, ...files])}
                showNotification={showNotification}
              />

              {processedResults.length > 0 && (
                <button
                  onClick={() => {
                    const headers = ['Filename','Raw Date','ISO Date','Format','Expired','Days Until Expiration'];
                    const rows = processedResults.flatMap(file =>
                      file.results?.map(r => [
                        file.filename,
                        r.date_raw,
                        r.date_iso || '',
                        r.detected_format || '',
                        r.is_expired ? 'Yes' : 'No',
                        r.days_until_expiration ?? ''
                      ]) || []
                    );
                    const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n');
                    const blob = new Blob([csv], { type: 'text/csv' });
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `docexpire-${Date.now()}.csv`;
                    link.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  <Download size={20} />
                  Export to CSV
                </button>
              )}
            </div>
          )}
        </div>

        {processedResults.length > 0 && (
          <>
            <AIInsights results={processedResults} showNotification={showNotification} />
            <div className="bg-white rounded-xl shadow-lg p-8">
              {processedResults.map((result, idx) => (
                <div key={idx} className="mb-4">
                  <ResultsTable
                    fileResults={result}
                    expanded={expandedFiles.has(idx)}
                    onToggleExpand={() => {
                      const s = new Set(expandedFiles);
                      s.has(idx) ? s.delete(idx) : s.add(idx);
                      setExpandedFiles(s);
                    }}
                  />
                  <button
                    onClick={() => setPreviewFile(result.filename)}
                    className="ml-4 mt-2 text-blue-600 text-sm"
                  >
                    View extracted text
                  </button>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/" element={<AppContent />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
