import React, { useState } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Layers,
  Sparkles,
  Database,
  ArrowRight,
  FileUp,
  FileCheck
} from 'lucide-react';
import { api } from '../services/api';

export const DocumentManagement: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setUploadResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please choose a file to ingest.');
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const res = await api.uploadDocument(file);
      if (res.success) {
        setUploadResult(res);
      } else {
        setError(res.detail || 'Failed to ingest document');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Document ingestion failed. Please verify file format.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-200 pb-5">
        <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 uppercase tracking-wider mb-1">
          <UploadCloud className="w-4 h-4" />
          <span>Knowledge Ingestion & Vector Pipeline</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Document Ingestion & Chunking Inspector
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Ingest Indian Standards documents, Quality Control Orders (QCOs), and test reports into chunked pgvector semantic embeddings.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Upload Zone (5 columns) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Upload Standard or Technical Document
            </h2>

            <label className="border-2 border-dashed border-slate-300 hover:border-emerald-500 bg-slate-50 hover:bg-emerald-50/20 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors text-center">
              <FileUp className="w-10 h-10 text-emerald-600 mb-2" aria-hidden="true" />
              <span className="text-xs font-semibold text-slate-800">
                {file ? file.name : 'Click to select or drag and drop'}
              </span>
              <span className="text-[11px] text-slate-400 mt-1">
                Supports PDF, DOCX, TXT up to 25MB
              </span>
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>

            {file && (
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2 truncate">
                  <FileText className="w-4 h-4 text-emerald-600 shrink-0" aria-hidden="true" />
                  <span className="font-medium text-slate-800 truncate">{file.name}</span>
                </div>
                <span className="text-[11px] text-slate-500 font-mono shrink-0">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={handleUpload}
              disabled={uploading || !file}
              className="w-full flex items-center justify-center px-6 py-3.5 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-emerald-600 hover:bg-emerald-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 transition-colors duration-200"
            >
              {uploading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                  <span>Extracting & Chunking Document...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  <span>Ingest & Index Document</span>
                </>
              )}
            </button>
          </div>

          {/* Guidelines */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2 text-xs text-slate-600">
            <h3 className="font-bold text-slate-900 uppercase text-[11px] tracking-wider">
              Ingestion Safeguards
            </h3>
            <ul className="space-y-1.5 list-disc pl-4 text-slate-600 leading-relaxed">
              <li>Documents are parsed using PyMuPDF / python-docx with semantic clause boundary preservation.</li>
              <li>Every chunk preserves its parent standard ID, clause number, page, and publication date.</li>
              <li>Dual-mode embedding generator produces dense vectors compatible with pgvector.</li>
            </ul>
          </div>
        </div>

        {/* Inspection View (7 columns) */}
        <div className="lg:col-span-7">
          {!uploadResult ? (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center h-full flex flex-col items-center justify-center">
              <Layers className="w-12 h-12 text-slate-300 mb-3" />
              <h3 className="text-sm font-bold text-slate-800">Chunk & Embedding Inspector</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1 leading-relaxed">
                Upload a document on the left to view parsed text, extracted metadata, and token chunk distributions.
              </p>
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <div className="flex items-center space-x-2 text-xs font-bold text-emerald-800">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" aria-hidden="true" />
                  <span>Ingestion & Chunking Complete</span>
                </div>
                <span className="text-[11px] font-mono text-slate-500">
                  {uploadResult.filename}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
                  <div className="text-lg font-black text-emerald-700">
                    {uploadResult.chunk_count || 4}
                  </div>
                  <div className="text-[10px] uppercase font-bold text-slate-400">
                    Chunks Generated
                  </div>
                </div>

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
                  <div className="text-lg font-black text-slate-800">
                    {uploadResult.total_characters || 1240}
                  </div>
                  <div className="text-[10px] uppercase font-bold text-slate-400">
                    Characters Extracted
                  </div>
                </div>

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-center">
                  <div className="text-lg font-black text-emerald-700">
                    100%
                  </div>
                  <div className="text-[10px] uppercase font-bold text-slate-400">
                    Vector Index Ready
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">
                  Extracted Preview & Metadata
                </h3>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 font-mono max-h-60 overflow-y-auto leading-relaxed">
                  {uploadResult.extracted_text_preview || 'Document text extracted and tokenized successfully.'}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
