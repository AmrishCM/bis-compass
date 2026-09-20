import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { ProductAnalysis } from './pages/ProductAnalysis';
import { StandardsDirectory } from './pages/StandardsDirectory';
import { StandardDetail } from './pages/StandardDetail';
import { ComplianceGapAnalyzer } from './pages/ComplianceGapAnalyzer';
import { LaboratoryDirectory } from './pages/LaboratoryDirectory';
import { SourcesManagement } from './pages/SourcesManagement';
import { DocumentManagement } from './pages/DocumentManagement';
import { EvaluationDashboard } from './pages/EvaluationDashboard';
import { AuditHistory } from './pages/AuditHistory';
import { SettingsPage } from './pages/SettingsPage';
import { ConsumerProtection } from './pages/ConsumerProtection';

import { LanguageProvider } from './i18n/LanguageContext';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 60000,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <LanguageProvider>
        <BrowserRouter>
          <div className="relative">
            <a href="#main-content" className="skip-link">
              Skip to main content
            </a>
            <main id="main-content">
              <Routes>
                <Route path="/" element={<Layout />}>
                  <Route index element={<Dashboard />} />
                  <Route path="analyze" element={<ProductAnalysis />} />
                  <Route path="consumer" element={<ConsumerProtection />} />
                  <Route path="standards" element={<StandardsDirectory />} />
                  <Route path="standards/:id" element={<StandardDetail />} />
                  <Route path="compliance" element={<ComplianceGapAnalyzer />} />
                  <Route path="laboratories" element={<LaboratoryDirectory />} />
                  <Route path="sources" element={<SourcesManagement />} />
                  <Route path="documents" element={<DocumentManagement />} />
                  <Route path="evaluation" element={<EvaluationDashboard />} />
                  <Route path="history" element={<AuditHistory />} />
                  <Route path="settings" element={<SettingsPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </LanguageProvider>
    </QueryClientProvider>
  );
}

export default App;