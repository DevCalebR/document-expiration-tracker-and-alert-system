import React from 'react';
import { AlertCircle, Check, AlertTriangle } from 'lucide-react';

export const Notification = ({ message, type, onClose }) => {
  const bgColor = type === 'error' ? 'bg-red-500' : 
                  type === 'success' ? 'bg-green-500' : 
                  type === 'warning' ? 'bg-yellow-500' : 
                  'bg-blue-500';
  
  return (
    <div className={`fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-2 z-50 animate-slide-in`}>
      {type === 'error' && <AlertCircle size={20} />}
      {type === 'success' && <Check size={20} />}
      {type === 'warning' && <AlertTriangle size={20} />}
      <span>{message}</span>
      <button onClick={onClose} className="ml-2 hover:opacity-80 text-xl leading-none">&times;</button>
    </div>
  );
};
