import React, { useState } from 'react';
import { FileText, Trash2, Upload } from 'lucide-react';
import { api } from '../utils/api';

export const FileUploader = ({
  uploadedFiles,
  onFilesUploaded,
  onFileDeleted,
  isUploading,
  setIsUploading,
  showNotification,
  disabled = false
}) => {
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (event.type === 'dragenter' || event.type === 'dragover') {
      setDragActive(true);
    } else if (event.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const uploadFile = async (file) => {
    try {
      const data = await api.uploadFile(file);
      return { success: true, data };
    } catch (error) {
      return { success: false, error: error.message, originalFile: file };
    }
  };

  const handleFiles = async (files) => {
    setIsUploading(true);
    const fileArray = Array.from(files);
    const results = await Promise.all(fileArray.map(uploadFile));

    const successfulUploads = results.filter((result) => result.success).map((result) => result.data);
    const failedUploads = results.filter((result) => !result.success);

    setIsUploading(false);
    onFilesUploaded(successfulUploads, failedUploads);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
    if (disabled) {
      return;
    }
    if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
      handleFiles(event.dataTransfer.files);
    }
  };

  const handleChange = (event) => {
    event.preventDefault();
    if (disabled) {
      return;
    }
    if (event.target.files && event.target.files.length > 0) {
      handleFiles(event.target.files);
    }
  };

  const deleteFile = async (filename) => {
    try {
      await api.deleteFile(filename);
      onFileDeleted(filename);
      showNotification('File deleted successfully', 'success');
    } catch (error) {
      showNotification(error.message, 'error');
    }
  };

  return (
    <div className="w-full">
      <div
        className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-upload"
          multiple
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleChange}
          disabled={disabled}
          className="hidden"
        />
        <label
          htmlFor="file-upload"
          className={`block ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
        >
          <Upload className="mx-auto mb-4 text-gray-400" size={48} />
          <p className="text-lg font-medium text-gray-700 mb-2">
            Drop files here or click to browse
          </p>
          <p className="text-sm text-gray-500">
            Supports PDF, PNG, and JPG files. Uploads remain available after refresh.
            {disabled ? ' Upload changes are paused while processing is running.' : ''}
          </p>
        </label>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="mt-6 space-y-2">
          <h3 className="font-semibold text-gray-700 mb-3">Available Files ({uploadedFiles.length})</h3>
          {uploadedFiles.map((file) => (
            <div
              key={file.saved_filename}
              className="flex items-center justify-between bg-gray-50 p-3 rounded-lg gap-3"
            >
              <div className="flex items-center gap-3 min-w-0">
                <FileText className="text-blue-500 shrink-0" size={20} />
                <div className="min-w-0">
                  <p className="font-medium text-gray-800 truncate">{file.original_filename}</p>
                  <p className="text-xs text-gray-500">
                    {((file.size_bytes || 0) / 1024).toFixed(2)} KB
                    {file.last_processed_at ? ` • Processed ${new Date(file.last_processed_at).toLocaleString()}` : ''}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-green-600 text-sm font-medium">Ready</span>
                <button
                  onClick={() => deleteFile(file.saved_filename)}
                  disabled={disabled}
                  className="text-red-600 hover:text-red-800 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label={`Delete ${file.original_filename}`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {isUploading && (
        <p className="text-sm text-blue-600 mt-4">Uploading files…</p>
      )}
    </div>
  );
};
