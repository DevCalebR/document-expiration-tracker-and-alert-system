import React, { useState } from 'react';
import { Brain, Loader2, AlertTriangle } from 'lucide-react';
import { api } from '../utils/api';

export const AIInsights = ({ results, showNotification }) => {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeWithAI = async () => {
    setLoading(true);
    try {
      const data = await api.analyzeWithAI(results);
      setInsights(data);
      showNotification('AI analysis complete', 'success');
    } catch (error) {
      showNotification('AI analysis unavailable. API key may not be configured.', 'warning');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-6 mb-6">
      <div className="flex items-center gap-3 mb-4">
        <Brain className="text-purple-600" size={28} />
        <h3 className="text-xl font-bold text-gray-800">AI Insights</h3>
      </div>

      {!insights ? (
        <button
          onClick={analyzeWithAI}
          disabled={loading}
          className="flex items-center gap-2 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:bg-gray-400"
        >
          {loading ? (
            <>
              <Loader2 className="animate-spin" size={20} />
              Analyzing...
            </>
          ) : (
            <>
              <Brain size={20} />
              Analyze with AI
            </>
          )}
        </button>
      ) : (
        <div className="space-y-4">
          {insights.anomalies && insights.anomalies.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="text-yellow-600" size={20} />
                <h4 className="font-semibold text-yellow-800">Unusual Dates Detected</h4>
              </div>
              <ul className="space-y-2">
                {insights.anomalies.map((anomaly, idx) => (
                  <li key={idx} className="text-sm text-yellow-800">
                    • {anomaly.message} - <span className="font-medium">{anomaly.date}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {insights.suggestions && insights.suggestions.length > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-semibold text-blue-800 mb-2">Recommendations</h4>
              <ul className="space-y-1">
                {insights.suggestions.map((suggestion, idx) => (
                  <li key={idx} className="text-sm text-blue-800">• {suggestion}</li>
                ))}
              </ul>
            </div>
          )}

          {insights.ai_insights && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <h4 className="font-semibold text-purple-800 mb-2">AI Analysis</h4>
              <p className="text-sm text-purple-800 whitespace-pre-wrap">{insights.ai_insights}</p>
            </div>
          )}

          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h4 className="font-semibold text-green-800 mb-2">Summary</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-green-700">Total dates analyzed:</p>
                <p className="text-2xl font-bold text-green-800">{insights.total_dates}</p>
              </div>
              <div>
                <p className="text-green-700">Expired:</p>
                <p className="text-2xl font-bold text-red-600">{insights.expired_count}</p>
              </div>
              <div>
                <p className="text-green-700">Expiring soon (&lt;30 days):</p>
                <p className="text-2xl font-bold text-orange-600">{insights.expiring_soon}</p>
              </div>
              <div>
                <p className="text-green-700">Valid:</p>
                <p className="text-2xl font-bold text-green-600">{insights.valid_count}</p>
              </div>
            </div>
          </div>

          <button
            onClick={() => setInsights(null)}
            className="text-purple-600 hover:text-purple-800 text-sm font-medium"
          >
            Run new analysis
          </button>
        </div>
      )}
    </div>
  );
};
