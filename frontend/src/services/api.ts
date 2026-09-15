import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000,
});

export interface StandardMatch {
  standard_id: number;
  standard_number: string;
  title: string;
  applicability_score: number;
  confidence: number;
  reasoning: string[];
  supporting_clauses: Array<{
    clause_number: string;
    heading: string;
    text: string;
    page?: number;
    relevance_score?: number;
  }>;
  status?: string;
  confirmed_attributes?: string[];
  missing_information?: string[];
  clarification_questions?: string[];
  metadata?: any;
}

export interface ProductUnderstandingData {
  product_name: string;
  normalized_product_name?: string;
  product_description?: string;
  product_family?: string;
  materials: string[];
  components?: string[];
  intended_use: string;
  application?: string;
  industry_context?: string;
  physical_form?: string;
  technical_attributes: Record<string, any>;
  regulatory_characteristics?: Record<string, any>;
  possible_domains?: string[];
  unknown_attributes?: string[];
  confidence: number;
  clarification_required?: boolean;
  clarification_questions?: string[];
  search_terms?: string[];
  category?: string;
  sub_category?: string;
  market?: string;
  possible_standard_categories?: string[];
  missing_information?: string[];
}

export interface CertificationStep {
  step_number: number;
  step_name: string;
  description: string;
  estimated_time?: string;
  required_documents?: string[];
  responsible_party?: string;
}

export interface CertificationInfoData {
  standard_id: number;
  standard_number: string;
  certification_scheme?: string;
  license_required: boolean;
  marking_requirements: Array<{
    requirement_type: string;
    description: string;
    is_mandatory: boolean;
  }>;
  testing_requirements: Array<{
    requirement_type: string;
    description: string;
    is_mandatory: boolean;
  }>;
  factory_audit_required: boolean;
  documentation_requirements: string[];
  certification_process: CertificationStep[];
  validity_period?: string;
  sources: any[];
}

export interface TestingInfoData {
  standard_id: number;
  standard_number: string;
  testing_requirements: Array<{
    test_type: string;
    description: string;
    is_mandatory: boolean;
    test_method?: string;
    acceptable_standards?: string[];
  }>;
  laboratories: Array<{
    lab_name: string;
    address: string;
    contact_person?: string;
    phone?: string;
    email?: string;
    is_bis_recognized: boolean;
    accreditation_body?: string;
    testing_facilities?: string[];
  }>;
  turnaround_time?: string;
  sample_requirements?: any;
  confidence?: number;
}

export interface LaboratoryData {
  id: number;
  lab_name: string;
  address: string;
  location: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  website?: string;
  accreditation_body: string;
  accreditation_number?: string;
  is_bis_recognized: boolean;
  bis_recognition_number?: string;
  accredited_scopes: string[];
  testing_facilities: string[];
  geographical_coverage: string;
  sample_collection_facility: boolean;
  distance_km?: number | null;
  distance_str?: string;
}

export interface ComplianceGapData {
  standard_id: number;
  standard_number: string;
  standard_title: string;
  compliance_percentage: number;
  confidence: number;
  risk_level: string;
  fulfilled_requirements: Array<{
    id?: string;
    description: string;
    type?: string;
    source_reference?: any;
    details?: any;
  }>;
  missing_requirements: Array<{
    id?: string;
    description: string;
    type?: string;
    source_reference?: any;
    details?: any;
  }>;
  partial_requirements: Array<{
    id?: string;
    description: string;
    type?: string;
    source_reference?: any;
    details?: any;
  }>;
  recommendations: string[];
}

export interface ResearchStageData {
  stage: string;
  status: string;
  description: string;
}

export interface InvestigatedSourceData {
  url: string;
  domain: string;
  title: string;
  authority_tier: number;
  authority_score: number;
  is_cached?: boolean;
  retrieved_at?: string;
}

export interface AnalysisResponse {
  success: boolean;
  execution_time_seconds: number;
  product_understanding: ProductUnderstandingData;
  clarification_required?: boolean;
  clarification_questions?: string[];
  applicable_standards: StandardMatch[];
  potential_standards?: StandardMatch[];
  related_standards?: Array<{
    standard_id: number;
    standard_number: string;
    title: string;
    relation?: string;
  }>;
  rejected_candidates?: Array<{
    standard_id: number;
    standard_number: string;
    title: string;
    reason: string;
    score: number;
  }>;
  research_trace?: {
    queries_executed?: Array<any>;
    urls_fetched?: Array<any>;
    sources_accepted?: Array<any>;
    sources_rejected?: Array<any>;
  };
  certification_info: CertificationInfoData[];
  testing_information: TestingInfoData[];
  laboratory_recommendations: LaboratoryData[];
  compliance_analysis: ComplianceGapData[];
  web_search_results: Array<{
    title: string;
    url: string;
    snippet: string;
    domain: string;
    authority_score: number;
  }>;
  research_stages?: ResearchStageData[];
  sources_investigated?: InvestigatedSourceData[];
  is_live_research?: boolean;
  session_id?: string;
  pipeline?: {
    sources_examined?: number;
    authoritative_sources_used?: number;
    retrieved_candidates: number;
    scope_filtered: number;
    applicable: number;
    rejected: number;
    is_live_research?: boolean;
    web_search_used: boolean;
  };
  overall_assessment: string;
  recommendations: string[];
  what_you_need_to_do?: {
    has_applicable_standard: boolean;
    standard_number?: string;
    title?: string;
    status: string;
    message?: string;
    qco_status: string;
    qco_message: string;
    certification_scheme: string;
    bis_certification_status: string;
    testing_status: string;
    tests: Array<{
      test_name: string;
      clause: string;
      test_method: string;
      requirement_type: string;
      evidence_source: string;
      is_mandatory: boolean;
    }>;
    next_actions: Array<{
      step_number: number;
      step_name: string;
      description: string;
      responsible_party: string;
    }>;
  };
  canonical_decision?: Record<string, any>;
}

export const api = {
  // Stats
  async getStats() {
    const res = await apiClient.get('/stats');
    return res.data;
  },

  // Analysis
  async analyzeProduct(data: {
    product_description: string;
    document_text?: string;
    location?: string;
    include_web_search?: boolean;
  }): Promise<AnalysisResponse> {
    const res = await apiClient.post<AnalysisResponse>('/analyze', data);
    return res.data;
  },

  // Product Understanding
  async extractProductUnderstanding(product_description: string) {
    const res = await apiClient.post('/products/analyze', { product_description });
    return res.data;
  },

  // Standards
  async getStandards(params?: { q?: string; status?: string; limit?: number; offset?: number }) {
    const res = await apiClient.get('/standards', { params });
    return res.data;
  },

  async getStandardDetail(id: number) {
    const res = await apiClient.get(`/standards/${id}`);
    return res.data;
  },

  // Laboratories
  async getLaboratories(params?: { location?: string; scope?: string; limit?: number }) {
    const res = await apiClient.get('/laboratories', { params });
    return res.data;
  },

  // Compliance Gap Analysis
  async analyzeCompliance(data: {
    standard_id: number;
    document_text: string;
    document_title?: string;
    product_category?: string;
  }) {
    const res = await apiClient.post('/compliance/analyze', data);
    return res.data;
  },

  // Document Upload
  async uploadDocument(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Web Search
  async searchWeb(query: string, max_results = 5) {
    const res = await apiClient.post('/web/search', { query, max_results });
    return res.data;
  },

  // Sources
  async getSources() {
    const res = await apiClient.get('/sources');
    return res.data;
  },

  // Evaluation
  async getEvaluationMetrics() {
    const res = await apiClient.get('/evaluation/metrics');
    return res.data;
  },

  async runEvaluation() {
    const res = await apiClient.post('/evaluation/run');
    return res.data;
  },

  // Chat
  async sendChatMessage(messages: Array<{ role: string; content: string }>, standard_id?: number) {
    const res = await apiClient.post('/chat', { messages, standard_id });
    return res.data;
  },

  // Audit Logs
  async getAuditLogs(params?: { action?: string; limit?: number; offset?: number }) {
    const res = await apiClient.get('/audit', { params });
    return res.data;
  },
};

