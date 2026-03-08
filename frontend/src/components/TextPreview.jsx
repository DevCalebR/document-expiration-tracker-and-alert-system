import React, { useState, useEffect } from 'react';
import { Copy, Check, Loader2 } from 'lucide-react';
import { api } from '../utils/api';

export const TextPreview = ({ filename, title, onClose }) => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchText = async () => {
      try {
        const data = await api.extractText(filename);
        
        if (data.content) {
          const fullText = data.content.map(page => 
            `--- Page ${page.page} ---\n${page.text}\n`
          ).join('\n');
          setText(fullText);
        }
      } catch (error) {
        setText(error.message || 'Error loading text preview');
      } finally {
        setLoading(false);
      }
    };

    fetchText();
  }, [filename]);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
        <div className="p-4 border-b flex items-center justify-between">
          <h3 className="font-semibold text-lg">Text Preview: {title || filename}</h3>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
        <div className="p-4 overflow-y-auto flex-1">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="animate-spin text-blue-500" size={48} />
            </div>
          ) : (
            <pre className="whitespace-pre-wrap font-mono text-sm text-gray-700 bg-gray-50 p-4 rounded">
              {text}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};
