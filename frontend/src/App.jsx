import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Calendar, Download, Loader2, LogOut, Upload } from 'lucide-react';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { Notification } from './components/Notification';
import { FileUploader } from './components/FileUploader';
import { CloudStorageConnector } from './components/CloudStorageConnector';
import { AIInsights } from './components/AIInsights';
import { AuditLog } from './components/AuditLog';
import { ExpiringSoon } from './components/ExpiringSoon';
import { ResultsTable } from './components/ResultsTable';
import { TextPreview } from './components/TextPreview';
import { VerifyEmail } from './components/VerifyEmail';
import { ProcessingStatus } from './components/ProcessingStatus';
import { AdminOps } from './components/AdminOps';
import { api, getAuthToken } from './utils/api';

const PROCESSING_TIMEOUT_MS = 120000;
const ACTIVE_PROCESSING_STATUSES = new Set(['queueing', 'queued', 'started', 'syncing']);

const mergeFiles = (currentFiles, incomingFiles) => {
  const merged = new Map();

  [...incomingFiles, ...currentFiles].forEach((file) => {
    if (file?.saved_filename && !merged.has(file.saved_filename)) {
      merged.set(file.saved_filename, file);
    }
  });

  return Array.from(merged.values());
};

const buildExpandedFiles = (results) => new Set(results.map((_, index) => index));

function AppContent() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [mode, setMode] = useState('login');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [processedResults, setProcessedResults] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [processingState, setProcessingState] = useState({ status: 'idle' });
  const [notification, setNotification] = useState(null);
  const [expandedFiles, setExpandedFiles] = useState(new Set());
  const [previewFile, setPreviewFile] = useState(null);
  const notificationTimerRef = useRef(null);

  const showNotification = useCallback((message, type = 'info') => {
    if (notificationTimerRef.current) {
      window.clearTimeout(notificationTimerRef.current);
    }

    setNotification({ message, type });
    notificationTimerRef.current = window.setTimeout(() => {
      setNotification(null);
      notificationTimerRef.current = null;
    }, 4000);
  }, []);

  useEffect(() => {
    return () => {
      if (notificationTimerRef.current) {
        window.clearTimeout(notificationTimerRef.current);
      }
    };
  }, []);

  const loadDocuments = useCallback(async ({ silent = false } = {}) => {
    try {
      const data = await api.getFiles();
      setUploadedFiles(data.files || []);
      return data.files || [];
    } catch (error) {
      if (!silent) {
        showNotification(error.message, 'error');
      }
      throw error;
    }
  }, [showNotification]);

  const applyProcessingResult = useCallback(async (payload, source = 'background') => {
    const summary = payload.summary || [];
    setProcessedResults(summary);
    setExpandedFiles(buildExpandedFiles(summary));
    setProcessingState((previous) => ({
      ...previous,
      status: 'finished',
      error: null,
      source,
      completedAt: Date.now()
    }));

    try {
      await loadDocuments({ silent: true });
    } catch (_error) {
      // The processing result is still valid even if the file list refresh fails.
    }

    showNotification(`Processed ${payload.files_processed ?? summary.length} file(s)`, 'success');
  }, [loadDocuments, showNotification]);

  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      const token = getAuthToken();
      if (!token) {
        setAuthLoading(false);
        return;
      }

      try {
        const data = await api.getCurrentUser();
        if (cancelled) {
          return;
        }
        setUser(data.user);
        await loadDocuments({ silent: true });
      } catch (_error) {
        if (!cancelled) {
          await api.logout();
          setUser(null);
          showNotification('Session expired. Sign in again to continue.', 'warning');
        }
      } finally {
        if (!cancelled) {
          setAuthLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, [loadDocuments, showNotification]);

  useEffect(() => {
    if (!processingState.jobId || !ACTIVE_PROCESSING_STATUSES.has(processingState.status) || processingState.status === 'syncing') {
      return undefined;
    }

    let cancelled = false;
    const { jobId } = processingState;
    const startedAt = processingState.startedAt || Date.now();

    const pollJob = async () => {
      if (Date.now() - startedAt > PROCESSING_TIMEOUT_MS) {
        if (!cancelled) {
          setProcessingState((previous) => {
            if (previous.jobId !== jobId) {
              return previous;
            }
            return {
              ...previous,
              status: 'timeout',
              error: 'The background job did not finish within 2 minutes.'
            };
          });
          showNotification('Processing timed out. Retry or use the sync fallback.', 'warning');
        }
        return;
      }

      try {
        const data = await api.getJobStatus(jobId);
        if (cancelled) {
          return;
        }

        if (data.status === 'finished') {
          if (data.result) {
            await applyProcessingResult(data.result, 'background');
            return;
          }

          setProcessingState((previous) => {
            if (previous.jobId !== jobId) {
              return previous;
            }
            return {
              ...previous,
              status: 'failed',
              error: 'The background job completed without returning results.'
            };
          });
          showNotification('Background processing completed without results. Use the sync fallback.', 'warning');
          return;
        }

        if (data.status === 'failed') {
          setProcessingState((previous) => {
            if (previous.jobId !== jobId) {
              return previous;
            }
            return {
              ...previous,
              status: 'failed',
              error: data.error || 'The background processor reported a failure.'
            };
          });
          showNotification('Background processing failed. Review the error and retry.', 'error');
          return;
        }

        setProcessingState((previous) => {
          if (previous.jobId !== jobId) {
            return previous;
          }
          return {
            ...previous,
            status: data.status || previous.status,
            error: null
          };
        });
      } catch (error) {
        if (!cancelled) {
          setProcessingState((previous) => {
            if (previous.jobId !== jobId) {
              return previous;
            }
            return {
              ...previous,
              status: 'failed',
              error: error.message
            };
          });
          showNotification(error.message, 'error');
        }
      }
    };

    pollJob();
    const intervalId = window.setInterval(pollJob, 1500);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [applyProcessingResult, processingState.jobId, processingState.startedAt, processingState.status, showNotification]);

  const handleLogin = async (userData) => {
    setUser(userData);
    setMode('login');

    try {
      await loadDocuments({ silent: true });
      showNotification(`Welcome, ${userData.full_name}!`, 'success');
    } catch (_error) {
      showNotification(`Welcome, ${userData.full_name}. Your files could not be loaded yet.`, 'warning');
    }
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    setUploadedFiles([]);
    setProcessedResults([]);
    setProcessingState({ status: 'idle' });
    setExpandedFiles(new Set());
    setPreviewFile(null);
    showNotification('Logged out successfully', 'success');
  };

  const startAsyncProcessing = useCallback(async (filenamesOverride) => {
    const filenames = filenamesOverride?.length
      ? filenamesOverride
      : uploadedFiles.map((file) => file.saved_filename);

    if (filenames.length === 0) {
      showNotification('Upload or import at least one file before processing.', 'warning');
      return;
    }

    setProcessingState({
      status: 'queueing',
      jobId: null,
      filenames,
      error: null,
      startedAt: Date.now()
    });

    try {
      const data = await api.processFilesAsync(filenames);
      if (data.status === 'finished' && data.job_id) {
        const jobData = await api.getJobStatus(data.job_id);
        if (jobData.result) {
          await applyProcessingResult(jobData.result, 'background');
          return;
        }

        setProcessingState({
          status: 'failed',
          jobId: data.job_id,
          filenames,
          error: 'The background job completed without returning results.',
          startedAt: Date.now()
        });
        showNotification('Background processing completed without results. Use the sync fallback.', 'warning');
        return;
      }

      setProcessingState({
        status: data.status || 'queued',
        jobId: data.job_id,
        filenames,
        error: null,
        startedAt: Date.now()
      });
    } catch (error) {
      setProcessingState({
        status: 'failed',
        jobId: null,
        filenames,
        error: error.message,
        startedAt: Date.now()
      });
      showNotification(error.message, 'error');
    }
  }, [showNotification, uploadedFiles]);

  const runSyncFallback = useCallback(async (filenamesOverride) => {
    const filenames = filenamesOverride?.length
      ? filenamesOverride
      : processingState.filenames?.length
        ? processingState.filenames
        : uploadedFiles.map((file) => file.saved_filename);

    if (filenames.length === 0) {
      showNotification('Upload or import at least one file before processing.', 'warning');
      return;
    }

    setProcessingState((previous) => ({
      ...previous,
      status: 'syncing',
      filenames,
      error: null,
      startedAt: Date.now()
    }));

    try {
      const data = await api.processFiles(filenames);
      await applyProcessingResult(data, 'sync');
    } catch (error) {
      setProcessingState((previous) => ({
        ...previous,
        status: 'failed',
        filenames,
        error: error.message
      }));
      showNotification(error.message, 'error');
    }
  }, [applyProcessingResult, processingState.filenames, showNotification, uploadedFiles]);

  const handleFilesUploaded = (successfulUploads, failedUploads) => {
    if (successfulUploads.length > 0) {
      setUploadedFiles((previous) => mergeFiles(previous, successfulUploads));
      showNotification(`${successfulUploads.length} file(s) uploaded`, 'success');
    }

    if (failedUploads.length > 0) {
      const firstFailure = failedUploads[0];
      const detail = firstFailure?.error ? `: ${firstFailure.error}` : '';
      showNotification(`${failedUploads.length} upload(s) failed${detail}`, 'error');
    }
  };

  const handleImportedFiles = (files) => {
    if (files.length > 0) {
      setUploadedFiles((previous) => mergeFiles(previous, files));
    }
  };

  const handleFileDeleted = (savedFilename) => {
    setUploadedFiles((previous) => previous.filter((file) => file.saved_filename !== savedFilename));
    setProcessedResults((previous) => {
      const remainingResults = previous.filter((result) => result.stored_filename !== savedFilename);
      setExpandedFiles(buildExpandedFiles(remainingResults));
      return remainingResults;
    });

    if (previewFile?.storedFilename === savedFilename) {
      setPreviewFile(null);
    }
  };

  const exportResults = () => {
    const headers = ['Filename', 'Stored Filename', 'Raw Date', 'ISO Date', 'Format', 'Expired', 'Days Until Expiration'];
    const rows = processedResults.flatMap((file) => (
      file.results?.map((result) => [
        file.filename,
        file.stored_filename || '',
        result.date_raw,
        result.date_iso || '',
        result.detected_format || '',
        result.is_expired ? 'Yes' : 'No',
        result.days_until_expiration ?? ''
      ]) || []
    ));

    if (rows.length === 0) {
      showNotification('There are no processed rows to export yet.', 'warning');
      return;
    }

    const csv = [headers.join(','), ...rows.map((row) => row.map((cell) => `"${cell}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `docexpire-${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const isProcessing = ACTIVE_PROCESSING_STATUSES.has(processingState.status);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-xl px-8 py-6 flex items-center gap-3 text-gray-700">
          <Loader2 className="animate-spin text-blue-600" size={24} />
          Restoring your session…
        </div>
      </div>
    );
  }

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
          onClose={() => {
            if (notificationTimerRef.current) {
              window.clearTimeout(notificationTimerRef.current);
              notificationTimerRef.current = null;
            }
            setNotification(null);
          }}
        />
      )}

      {previewFile && (
        <TextPreview
          filename={previewFile.storedFilename}
          title={previewFile.title}
          onClose={() => setPreviewFile(null)}
        />
      )}

      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <header className="mb-8">
          <div className="flex items-center justify-between gap-6 flex-wrap">
            <div className="flex items-center gap-3">
              <Calendar className="text-blue-600" size={48} />
              <div>
                <h1 className="text-4xl font-bold text-gray-800">DocExpire</h1>
                <p className="text-gray-600">Enterprise document expiration tracking with OCR, alerts, and cloud import.</p>
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

        <AdminOps user={user} showNotification={showNotification} />
        {user.role === 'admin' && <AuditLog user={user} showNotification={showNotification} />}
        <ExpiringSoon showNotification={showNotification} />

        <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6 flex items-center gap-2">
            <Upload size={24} />
            Documents
          </h2>

          <ProcessingStatus
            state={processingState}
            onRetry={() => startAsyncProcessing(processingState.filenames)}
            onFallback={() => runSyncFallback(processingState.filenames)}
          />

          <FileUploader
            uploadedFiles={uploadedFiles}
            onFilesUploaded={handleFilesUploaded}
            onFileDeleted={handleFileDeleted}
            isUploading={isUploading}
            setIsUploading={setIsUploading}
            showNotification={showNotification}
            disabled={isProcessing}
          />

          <div className="mt-6 flex gap-4 flex-wrap">
            <button
              onClick={() => startAsyncProcessing()}
              disabled={isProcessing || uploadedFiles.length === 0}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
            >
              {isProcessing ? <Loader2 className="animate-spin" size={20} /> : <Calendar size={20} />}
              {isProcessing ? 'Processing…' : 'Process Files'}
            </button>

            <CloudStorageConnector
              onImport={handleImportedFiles}
              showNotification={showNotification}
              disabled={isProcessing}
            />

            {processedResults.length > 0 && (
              <button
                onClick={exportResults}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                <Download size={20} />
                Export to CSV
              </button>
            )}
          </div>

          {uploadedFiles.length > 0 && (
            <p className="text-sm text-gray-500 mt-4">
              Background processing uses the queue first and automatically falls back to the sync endpoint only when needed.
            </p>
          )}
        </div>

        {processedResults.length > 0 && (
          <>
            <AIInsights results={processedResults} showNotification={showNotification} />
            <div className="bg-white rounded-xl shadow-lg p-8">
              {processedResults.map((result, index) => (
                <div key={`${result.stored_filename || result.filename}-${index}`} className="mb-4">
                  <ResultsTable
                    fileResults={result}
                    expanded={expandedFiles.has(index)}
                    onToggleExpand={() => {
                      setExpandedFiles((previous) => {
                        const next = new Set(previous);
                        if (next.has(index)) {
                          next.delete(index);
                        } else {
                          next.add(index);
                        }
                        return next;
                      });
                    }}
                  />
                  {result.stored_filename && !result.error && (
                    <button
                      onClick={() => setPreviewFile({ storedFilename: result.stored_filename, title: result.filename })}
                      className="ml-4 mt-2 text-blue-600 text-sm hover:text-blue-800"
                    >
                      View extracted text
                    </button>
                  )}
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
