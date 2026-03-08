import React, { useEffect, useState } from 'react';
import { CalendarClock, Loader2, RefreshCw } from 'lucide-react';
import { api } from '../utils/api';

export const ExpiringSoon = ({ showNotification }) => {
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);

  const fetchExpiring = async () => {
    setLoading(true);
    try {
      const data = await api.getExpiringSoon(days);
      setResults(data.results || []);
      if ((data.results || []).length === 0) {
        showNotification('No documents expiring soon', 'info');
      }
    } catch (error) {
      showNotification('Failed to load expiring documents', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExpiring();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <CalendarClock className="text-orange-600" size={24} />
          <h3 className="text-xl font-bold text-gray-800">Expiring Soon</h3>
        </div>
        <button
          onClick={fetchExpiring}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:bg-gray-300"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <label className="text-sm text-gray-600">Days ahead</label>
        <input
          type="number"
          min="1"
          max="365"
          value={days}
          onChange={(e) => setDays(Number(e.target.value || 1))}
          className="w-24 px-3 py-2 border rounded-lg text-sm"
        />
        <button
          onClick={fetchExpiring}
          disabled={loading}
          className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-400"
        >
          Apply
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="animate-spin text-orange-500" size={32} />
        </div>
      ) : results.length === 0 ? (
        <p className="text-center text-gray-500 py-6">No documents within {days} days</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-3 font-semibold text-gray-700">Document</th>
                <th className="text-left py-2 px-3 font-semibold text-gray-700">Date</th>
                <th className="text-left py-2 px-3 font-semibold text-gray-700">Days Left</th>
              </tr>
            </thead>
            <tbody>
              {results.map((row, idx) => (
                <tr key={idx} className="border-b last:border-b-0 hover:bg-gray-50">
                  <td className="py-2 px-3">{row.document?.original_filename || 'Unknown'}</td>
                  <td className="py-2 px-3">{row.date_raw || row.date_iso || 'N/A'}</td>
                  <td className="py-2 px-3 text-orange-700 font-medium">{row.days_until_expiration}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
