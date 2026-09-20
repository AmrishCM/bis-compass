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

export interface ClarificationQuestionItem {
  id: string;
  question: string;
  type: string; // single_choice, multiple_choice, yes_no, numeric, text
  options: string[];
  why_we_need_this: string;
  decision_impact: string;
  // Legacy fields (backward compat)
  why_needed?: string;
  affects?: string[];
  attribute_key?: string;
}

export interface ClarificationBlock {
  title: string;
  intro: string;
  questions: ClarificationQuestionItem[];
  explanation?: string;
}

export interface ProgressBlock {
  product: string; // "current" | "done" | "pending" | "incomplete"
  standard: string;
  certification: string;
  tests: string;
  laboratory: string;
  application: string;
}

export interface ProductBlock {
  name: string;
  description: string;
  known_details: Record<string, string>;
  missing_decision_critical_details: string[];
}

export interface StandardBlock {
  standard_id?: number;
  standard_number: string;
  title: string;
  status: string;
  why_applies: string[];
  official_source_url: string;
  technical_clauses: Array<{ clause_number: string; heading: string; text: string }>;
}

export interface CertificationBlock {
  status: string; // REQUIRED | VOLUNTARY | NOT VERIFIED
  scheme: string;
  why: string;
  official_basis: string;
  factory_audit_required: boolean;
}

export interface TestItem {
  test_name: string;
  what_it_checks: string;
  test_method: string;
  is_mandatory: boolean;
  source_reference: string;
}

export interface LabItem {
  lab_name: string;
  address: string;
  location: string;
  phone?: string;
  email?: string;
  website?: string;
  is_bis_recognized: boolean;
  accredited_scopes?: string[];
  testing_facilities?: string[];
  match_score?: number;
  match_reasons?: string[];
}

export interface ApplicationStep {
  step_number: number;
  title: string;
  description: string;
}

export interface NextAction {
  action: string;
  details: string;
}

export interface StatusBanner {
  type: string; // "verified" | "clarification" | "incomplete"
  title: string;
  message: string;
}

export interface AnalysisResponse {
  success: boolean;
  session_id?: string;
  state: string; // NEEDS_CLARIFICATION | READY | NO_STANDARD_FOUND
  execution_time_seconds: number;

  // Core blocks
  product: ProductBlock;
  progress: ProgressBlock;
  status_banner: StatusBanner;

  // Phase A — Clarification
  clarification: ClarificationBlock | null;

  // Phase B — Compliance Roadmap
  standard: StandardBlock | null;
  certification: CertificationBlock | null;
  tests: TestItem[];
  laboratories: LabItem[];
  application_steps: ApplicationStep[];
  next_action: NextAction | null;

  // Multi-product
  multi_product_detected?: {
    is_multi_product: boolean;
    detected_products: string[];
    message: string;
  };

  // Dual-Explanation Modes Data
  msme_summary?: {
    title: string;
    plain_language_verdict: string;
    top_action_items: string[];
    estimated_readiness_time: string;
    msme_concession_eligible: boolean;
  };

  auditor_matrix?: {
    standard_id?: number;
    standard_number?: string;
    qco_order_ref?: string;
    clause_citations: Array<{
      clause_number: string;
      heading: string;
      criterion: string;
      test_standard: string;
      pass_criterion: string;
      verification_status: string;
    }>;
    test_protocols: TestItem[];
    confidence_score: number;
  };

  // Sample Preparation Guidance (Section 4)
  sample_preparation_guidance?: {
    sample_quantity: string;
    preparation_and_conditioning: string;
    packaging_and_sealing: string;
    storage_and_handling: string;
    test_parameter_checklist: string[];
    labeling_instruction: string;
  } | null;

  // Profile-Tailored Document & Readiness Checklist (Section 3.2)
  profile_readiness_checklists?: {
    msme: {
      title: string;
      concession_badge: string;
      documents: Array<{ item: string; mandatory: boolean }>;
      in_house_equipment: Array<{ equipment: string; purpose: string }>;
      factory_audit_focus: string;
    };
    startup: {
      title: string;
      concession_badge: string;
      documents: Array<{ item: string; mandatory: boolean }>;
      in_house_equipment: Array<{ equipment: string; purpose: string }>;
      factory_audit_focus: string;
    };
    large: {
      title: string;
      concession_badge: string;
      documents: Array<{ item: string; mandatory: boolean }>;
      in_house_equipment: Array<{ equipment: string; purpose: string }>;
      factory_audit_focus: string;
    };
  } | null;

  // Backward-compat fields
  final_status?: string;
  clarification_required?: boolean;
  clarification_questions?: string[];
  clarification_question_items?: ClarificationQuestionItem[];
  product_profile?: Record<string, any>;
  product_understanding?: ProductUnderstandingData;
  applicable_standards?: StandardMatch[];
  potential_standards?: StandardMatch[];
  related_standards?: Array<any>;
  rejected_candidates?: Array<any>;
  certification_info?: CertificationInfoData[];
  testing_information?: TestingInfoData[];
  laboratory_recommendations?: LaboratoryData[];
  step_by_step_roadmap?: any;
  overall_assessment?: string;
  recommendations?: string[];
  _audit?: Record<string, any>;
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
    additional_details?: string;
    document_text?: string;
    location?: string;
    include_web_search?: boolean;
    session_id?: string;
  }): Promise<AnalysisResponse> {
    const res = await apiClient.post<AnalysisResponse>('/analyze', data);
    return res.data;
  },

  // Clarification (Sections 4, 7, 26, 27)
  async clarifyProduct(data: {
    session_id: string;
    clarification_answer?: string;
    answers?: Record<string, string>;
    question?: string;
    location?: string;
  }): Promise<AnalysisResponse> {
    const res = await apiClient.post<AnalysisResponse>('/analyze/clarify', data);
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

  // Standard Dependencies
  async getStandardDependencies(id: number) {
    const res = await apiClient.get(`/standards/${id}/dependencies`);
    return res.data;
  },

  // Consumer Protection & Hallmarking
  async verifyHUID(data: { huid: string; metal_type?: string; declared_purity?: string }) {
    const res = await apiClient.post('/consumer/verify-huid', data);
    return res.data;
  },

  async verifyCML(data: { cml_number: string; standard_number?: string }) {
    const res = await apiClient.post('/consumer/verify-cml', data);
    return res.data;
  },

  async draftGrievance(data: {
    consumer_name: string;
    consumer_phone: string;
    consumer_email?: string;
    complaint_category: string;
    product_name: string;
    standard_number?: string;
    seller_name: string;
    seller_location: string;
    invoice_number?: string;
    invoice_date?: string;
    incident_description: string;
  }) {
    const res = await apiClient.post('/consumer/grievance/draft', data);
    return res.data;
  },

  // Gazette & Updates Pipeline
  async getGazetteUpdates(params?: { ministry?: string; status?: string; search?: string }) {
    const res = await apiClient.get('/updates/gazette', { params });
    return res.data;
  },

  async triggerGazetteSync() {
    const res = await apiClient.post('/updates/sync');
    return res.data;
  },
};

