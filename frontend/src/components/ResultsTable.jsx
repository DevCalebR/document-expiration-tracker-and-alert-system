import React from 'react';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';

export const ResultsTable = ({ fileResults, expanded, onToggleExpand }) => {
  const results = fileResults.results || [];
  
  const getExpirationColor = (isExpired, days) => {
    if (isExpired) return 'text-red-600 font-semibold';
    if (days !== null && days < 30) return 'text-orange-600';
    return 'text-green-600';
  };

  return (
    <div className="border rounded-lg overflow-hidden mb-4">
      <div 
        className="bg-gray-100 p-4 flex items-center justify-between cursor-pointer hover:bg-gray-200 transition-colors"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-3">
          <FileText className="text-blue-600" size={24} />
          <div>
            <h3 className="font-semibold text-gray-800">{fileResults.filename}</h3>
            <p className="text-sm text-gray-600">
              {fileResults.error
                ? 'Processing failed for this document'
                : `${fileResults.pages_extracted ?? 0} pages • ${fileResults.dates_detected ?? 0} dates detected`}
            </p>
          </div>
        </div>
        {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
      </div>

      {expanded && (
        <div className="p-4">
          {fileResults.error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {fileResults.error}
            </div>
          ) : results.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No dates detected in this document</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3 font-semibold text-gray-700">Raw Date</th>
                    <th className="text-left py-2 px-3 font-semibold text-gray-700">ISO Date</th>
                    <th className="text-left py-2 px-3 font-semibold text-gray-700">Format</th>
                    <th className="text-left py-2 px-3 font-semibold text-gray-700">Status</th>
                    <th className="text-left py-2 px-3 font-semibold text-gray-700">Days Until Expiration</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result, idx) => (
                    <tr key={idx} className="border-b last:border-b-0 hover:bg-gray-50">
                      <td className="py-3 px-3">{result.date_raw}</td>
                      <td className="py-3 px-3">{result.date_iso || 'N/A'}</td>
                      <td className="py-3 px-3 text-sm text-gray-600">{result.detected_format || 'N/A'}</td>
                      <td className={`py-3 px-3 font-medium ${getExpirationColor(result.is_expired, result.days_until_expiration)}`}>
                        {result.is_expired === true ? 'Expired' : result.is_expired === false ? 'Valid' : 'Unknown'}
                      </td>
                      <td className={`py-3 px-3 ${getExpirationColor(result.is_expired, result.days_until_expiration)}`}>
                        {result.days_until_expiration !== null ? `${result.days_until_expiration} days` : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
