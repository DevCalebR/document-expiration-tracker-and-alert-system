import React, { useState } from 'react';
import { Upload, FileText, Trash2 } from 'lucide-react';
import { api } from '../utils/api';

export const FileUploader = ({ onFilesUploaded, isUploading, setIsUploading, user, showNotification }) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const uploadFile = async (file) => {
    try {
      const data = await api.uploadFile(file);
      return { success: true, data, originalFile: file };
    } catch (error) {
      return { success: false, error: error.message, originalFile: file };
    }
  };

  const handleFiles = async (files) => {
    setIsUploading(true);
    const fileArray = Array.from(files);
    
    const results = await Promise.all(fileArray.map(uploadFile));
    
    const successfulUploads = results.filter(r => r.success);
    const failedUploads = results.filter(r => !r.success);

    setUploadedFiles(prev => [...prev, ...successfulUploads.map(r => ({
      name: r.originalFile.name,
      size: r.originalFile.size,
      savedFilename: r.data.saved_filename,
      status: 'uploaded'
    }))]);

    setIsUploading(false);
    onFilesUploaded(successfulUploads.map(r => r.data), failedUploads);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const deleteFile = async (filename) => {
    try {
      await api.deleteFile(filename);
      setUploadedFiles(prev => prev.filter(f => f.savedFilename !== filename));
      showNotification('File deleted successfully', 'success');
    } catch (error) {
      showNotification('Failed to delete file', 'error');
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
          className="hidden"
        />
        <label htmlFor="file-upload" className="cursor-pointer">
          <Upload className="mx-auto mb-4 text-gray-400" size={48} />
          <p className="text-lg font-medium text-gray-700 mb-2">
            Drop files here or click to browse
          </p>
          <p className="text-sm text-gray-500">
            Supports PDF, PNG, and JPG files (bulk upload supported)
          </p>
        </label>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="mt-6 space-y-2">
          <h3 className="font-semibold text-gray-700 mb-3">Uploaded Files ({uploadedFiles.length})</h3>
          {uploadedFiles.map((file, idx) => (
            <div key={idx} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
              <div className="flex items-center gap-3">
                <FileText className="text-blue-500" size={20} />
                <div>
                  <p className="font-medium text-gray-800">{file.name}</p>
                  <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(2)} KB</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-green-600 text-sm font-medium">✓ Uploaded</span>
                {user.role === 'admin' && (
                  <button
                    onClick={() => deleteFile(file.savedFilename)}
                    className="text-red-600 hover:text-red-800"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
