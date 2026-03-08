import React from 'react';
import { AlertCircle, CheckCircle2, Clock3, Loader2, RefreshCw } from 'lucide-react';

const STATUS_COPY = {
  queueing: {
    title: 'Queueing documents',
    detail: 'Submitting documents for background OCR and date extraction.'
  },
  queued: {
    title: 'Job queued',
    detail: 'The processor has accepted the job and is waiting to start.'
  },
  started: {
    title: 'Processing in background',
    detail: 'OCR and date extraction are running now.'
  },
  finished: {
    title: 'Processing complete',
    detail: 'The latest document results are ready below.'
  },
  failed: {
    title: 'Processing failed',
    detail: 'The background job failed before results were returned.'
  },
  timeout: {
    title: 'Processing timed out',
    detail: 'The job did not finish in time. You can retry or fall back to a direct run.'
  },
  syncing: {
    title: 'Running sync fallback',
    detail: 'Using the direct processing endpoint as a recovery path.'
  }
};

const stateIcon = (status) => {
  if (status === 'finished') return <CheckCircle2 className="text-green-600" size={22} />;
  if (status === 'failed' || status === 'timeout') return <AlertCircle className="text-red-600" size={22} />;
  if (status === 'queueing' || status === 'syncing') return <RefreshCw className="animate-spin text-blue-600" size={22} />;
  if (status === 'queued' || status === 'started') return <Loader2 className="animate-spin text-blue-600" size={22} />;
  return <Clock3 className="text-gray-500" size={22} />;
};

export const ProcessingStatus = ({ state, onRetry, onFallback }) => {
  if (!state || state.status === 'idle') {
    return null;
  }

  const copy = STATUS_COPY[state.status] || STATUS_COPY.queued;
  const isError = state.status === 'failed' || state.status === 'timeout';

  return (
    <div className={`rounded-xl border p-5 mb-6 ${isError ? 'bg-red-50 border-red-200' : 'bg-blue-50 border-blue-200'}`}>
      <div className="flex items-start gap-3">
        {stateIcon(state.status)}
        <div className="flex-1">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <h3 className="text-lg font-semibold text-gray-800">{copy.title}</h3>
              <p className="text-sm text-gray-600 mt-1">{copy.detail}</p>
            </div>
            {state.jobId && (
              <span className="text-xs font-mono bg-white border px-2 py-1 rounded text-gray-600">
                {state.jobId}
              </span>
            )}
          </div>

          {state.error && (
            <p className="text-sm text-red-700 mt-3">{state.error}</p>
          )}

          {isError && (
            <div className="flex gap-3 mt-4 flex-wrap">
              <button
                onClick={onRetry}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Retry async
              </button>
              <button
                onClick={onFallback}
                className="px-4 py-2 bg-white text-gray-800 border rounded-lg hover:bg-gray-50"
              >
                Run sync fallback
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
