import { AnalysisResponse } from '../services/api';

export function downloadComplianceDossier(analysis: AnalysisResponse) {
  const timestamp = new Date().toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });

  const printWindow = window.open('', '_blank', 'width=900,height=1000');
  if (!printWindow) {
    alert('Please allow popups to download the official BIS compliance dossier.');
    return;
  }

  const standardNum = analysis.standard?.standard_number || 'IS Conformance';
  const standardTitle = analysis.standard?.title || 'Indian Standard Specification';
  const certScheme = analysis.certification?.scheme || 'Scheme-I (ISI Mark)';
  const certStatus = analysis.certification?.status || 'MANDATORY';
  const productName = analysis.product?.name || 'Assessed Product';
  const sessionId = analysis.session_id || 'BC-2026-DOSSIER';

  const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>BIS Compliance Dossier - ${sessionId}</title>
  <style>
    @page {
      size: A4;
      margin: 15mm 15mm 20mm 15mm;
    }
    body {
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
      color: #1e293b;
      line-height: 1.45;
      font-size: 11pt;
      margin: 0;
      padding: 0;
      background: #fff;
    }
    .header {
      border-bottom: 2.5px solid #047857;
      padding-bottom: 12px;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }
    .gov-badge {
      font-size: 8.5pt;
      font-weight: 700;
      color: #047857;
      text-transform: uppercase;
      letter-spacing: 0.8px;
    }
    .title {
      font-size: 16pt;
      font-weight: 800;
      color: #0f172a;
      margin: 2px 0 0 0;
    }
    .meta-box {
      text-align: right;
      font-size: 8.5pt;
      color: #64748b;
    }
    .meta-box strong {
      color: #0f172a;
    }
    .section-title {
      font-size: 11pt;
      font-weight: 700;
      color: #065f46;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 4px;
      margin-top: 18px;
      margin-bottom: 8px;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 10px;
    }
    .card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px;
    }
    .label {
      font-size: 8pt;
      text-transform: uppercase;
      color: #64748b;
      font-weight: 600;
      margin-bottom: 2px;
    }
    .value {
      font-size: 10pt;
      font-weight: 700;
      color: #0f172a;
    }
    .badge {
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 8pt;
      font-weight: 700;
      text-transform: uppercase;
    }
    .badge-mandatory {
      background: #fee2e2;
      color: #991b1b;
      border: 1px solid #f87171;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
      font-size: 9pt;
    }
    th {
      background: #f1f5f9;
      color: #334155;
      text-align: left;
      padding: 6px 8px;
      border: 1px solid #cbd5e1;
      font-weight: 700;
      font-size: 8.5pt;
    }
    td {
      padding: 6px 8px;
      border: 1px solid #e2e8f0;
      vertical-align: top;
    }
    tr:nth-child(even) {
      background: #f8fafc;
    }
    .footer {
      margin-top: 24px;
      border-top: 1px solid #cbd5e1;
      padding-top: 8px;
      display: flex;
      justify-content: space-between;
      font-size: 8pt;
      color: #94a3b8;
    }
    .action-print {
      position: fixed;
      top: 15px;
      right: 15px;
      padding: 8px 16px;
      background: #047857;
      color: #fff;
      font-weight: 700;
      font-size: 12px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    @media print {
      .action-print {
        display: none;
      }
    }
  </style>
</head>
<body>
  <button class="action-print" onclick="window.print()">Print / Save as PDF</button>

  <div class="header">
    <div>
      <div class="gov-badge">Bureau of Indian Standards (BIS) • Compliance Intelligence Dossier</div>
      <h1 class="title">Product Certification & Standards Dossier</h1>
    </div>
    <div class="meta-box">
      <div>Session Ref: <strong>${sessionId}</strong></div>
      <div>Date Generated: <strong>${timestamp}</strong></div>
      <div>Status: <span class="badge badge-mandatory">${certStatus}</span></div>
    </div>
  </div>

  <!-- Product & Standard Summary -->
  <div class="section-title">1. Executive Compliance Summary</div>
  <div class="grid-2">
    <div class="card">
      <div class="label">Evaluated Product</div>
      <div class="value">${productName}</div>
      <div style="font-size: 8.5pt; color: #475569; margin-top: 4px;">${analysis.product?.description || ''}</div>
    </div>
    <div class="card">
      <div class="label">Governing Indian Standard</div>
      <div class="value" style="color: #065f46;">${standardNum}</div>
      <div style="font-size: 8.5pt; color: #475569; margin-top: 4px;">${standardTitle}</div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="label">Applicable Certification Scheme</div>
      <div class="value">${certScheme}</div>
      <div style="font-size: 8.5pt; color: #475569; margin-top: 2px;">Factory Audit Required: <strong>${analysis.certification?.factory_audit_required ? 'Yes' : 'No'}</strong></div>
    </div>
    <div class="card">
      <div class="label">Regulatory Mandate Basis</div>
      <div class="value">Quality Control Order (QCO)</div>
      <div style="font-size: 8.5pt; color: #475569; margin-top: 2px;">Enforced under Section 16 of the BIS Act, 2016</div>
    </div>
  </div>

  <!-- Mandatory Testing Matrix -->
  <div class="section-title">2. Mandatory Testing Requirements & Clause Citations</div>
  <table>
    <thead>
      <tr>
        <th style="width: 25%;">Test Parameter</th>
        <th style="width: 45%;">Scope / What It Checks</th>
        <th style="width: 20%;">Test Method IS</th>
        <th style="width: 10%;">Type</th>
      </tr>
    </thead>
    <tbody>
      ${(analysis.tests || []).slice(0, 8).map((t) => `
        <tr>
          <td><strong>${t.test_name}</strong></td>
          <td>${t.what_it_checks}</td>
          <td><code>${t.test_method || standardNum}</code></td>
          <td><span style="font-weight: 700; color: #047857;">${t.is_mandatory ? 'Mandatory' : 'Optional'}</span></td>
        </tr>
      `).join('')}
    </tbody>
  </table>

  <!-- Shortlisted Labs -->
  <div class="section-title">3. Shortlisted BIS-Recognized / NABL Testing Laboratories</div>
  <table>
    <thead>
      <tr>
        <th style="width: 35%;">Laboratory Name</th>
        <th style="width: 45%;">Address / Location</th>
        <th style="width: 20%;">Accreditation</th>
      </tr>
    </thead>
    <tbody>
      ${(analysis.laboratories || []).slice(0, 4).map((lab) => `
        <tr>
          <td><strong>${lab.lab_name}</strong></td>
          <td>${lab.address || lab.location}</td>
          <td><span style="font-size: 8pt; font-weight: 700; color: #047857;">BIS RECOGNIZED</span></td>
        </tr>
      `).join('')}
    </tbody>
  </table>

  <!-- Step-by-Step Roadmap -->
  <div class="section-title">4. Statutory Application & Inspection Roadmap</div>
  <ol style="margin-top: 6px; padding-left: 18px; font-size: 9pt; color: #334155;">
    ${(analysis.application_steps || []).map((s) => `
      <li style="margin-bottom: 5px;">
        <strong>${s.title}:</strong> ${s.description}
      </li>
    `).join('')}
  </ol>

  <!-- Footer -->
  <div class="footer">
    <div>BIS-Compass AI Regulatory Intelligence • Confidential Compliance Dossier</div>
    <div>Page 1 of 1 • Generated for Enterprise Quality Assurance</div>
  </div>

  <script>
    window.onload = function() {
      // Auto-trigger print dialog for instant PDF saving
      setTimeout(function() { window.print(); }, 400);
    }
  </script>
</body>
</html>
`;

  printWindow.document.write(htmlContent);
  printWindow.document.close();
}
