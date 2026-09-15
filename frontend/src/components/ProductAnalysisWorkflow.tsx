import { useState } from 'react';

export const ProductAnalysisWorkflow = () => {
  const [productDescription, setProductDescription] = useState('');
  const [documentText, setDocumentText] = useState('');
  const [location, setLocation] = useState('');
  const [standards, setStandards] = useState<string[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsAnalyzing(true);
    setError(null);

    try {
      // In a real implementation, this would call the backend API
      // For now, we'll simulate the analysis with mock data
      const mockResults = await simulateAnalysis({
        product_description: productDescription,
        document_text: documentText,
        location: location,
        standards: standards
      });

      setResults(mockResults);
    } catch (err) {
      setError('Analysis failed. Please try again.');
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (!results) {
    return (
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Product Analysis Workflow</h2>
          <p className="text-gray-600">
            Enter product details to get comprehensive BIS certification analysis including
            applicable standards, requirements, testing information, laboratories, and compliance gaps.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Product Description</label>
            <textarea
              value={productDescription}
              onChange={(e) => setProductDescription(e.target.value)}
              rows={4}
              className="w-full border border-gray-300 rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Describe your product, its intended use, key features, etc."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Document Text (Optional)</label>
            <textarea
              value={documentText}
              onChange={(e) => setDocumentText(e.target.value)}
              rows={6}
              className="w-full border border-gray-300 rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Paste document text for compliance analysis (e.g., product manual, specification sheet)"
            />
          </div>

          <div className="flex flex-col sm:flex-row sm:items-start sm:space-x-4">
            <div className="w-full sm:w-1/2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Location (for lab search)</label>
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full border border-gray-300 rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="City, State (e.g., New Delhi, Delhi)"
              />
            </div>

            <div className="w-full sm:w-1/2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Standards (Optional, comma-separated)</label>
              <input
                value={standards.join(', ')}
                onChange={(e) => setStandards(
                  e.target.value.split(',').map(s => s.trim()).filter(s => s.length > 0)
                )}
                className="w-full border border-gray-300 rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., IS 12345, IS 67890"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isAnalyzing}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {isAnalyzing ? 'Analyzing...' : 'Start Analysis'}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 mb-4">
            <p>{error}</p>
          </div>
        )}
      </form>
    );
  }

  return (
    <div className="space-y-8">
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="bg-blue-50 px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-800">Analysis Results</h3>
        </div>
        <div className="p-6 space-y-6">
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-gray-800 mb-2">Product Understanding</h4>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-600">{results?.product_understanding?.product_name || 'Analyzing product description...'}</p>
                <p className="text-sm text-gray-500 mt-1">
                  Category: {results?.product_understanding?.category || 'N/A'} |
                  Confidence: {(results?.product_understanding?.confidence || 0).toFixed(2)}
                </p>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-800 mb-2">Applicable Standards</h4>
              <div className="bg-gray-50 p-4 rounded-lg">
                {results?.applicable_standards?.length ? (
                  <ul className="space-y-2">
                    {results.applicable_standards.map((std: any, index: number) => (
                      <li key={index} className="flex justify-between items-start">
                        <span className="font-medium">{std.standard_number}</span>
                        <span className="text-gray-600">{std.title}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-600">No applicable standards found</p>
                )}
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-800 mb-2">Certification Requirements</h4>
              <div className="bg-gray-50 p-4 rounded-lg">
                {results?.certification_info?.length ? (
                  <ul className="space-y-2">
                    {results.certification_info.map((cert: any, index: number) => (
                      <li key={index} className="p-3 bg-white rounded mb-2">
                        <h5 className="font-medium text-gray-800">{cert.standard_number} Certification</h5>
                        <p className="text-sm text-gray-600 mb-1">
                          License Required: {cert.license_required ? 'Yes' : 'No'} |
                          Process: {cert.certification_process || 'Standard'}
                        </p>
                        {cert.requirements?.length && (
                          <ul className="text-sm text-gray-500 mt-2 space-y-1">
                            {cert.requirements.map((req: string, idx: number) => (
                              <li key={idx}>• {req}</li>
                            ))}
                          </ul>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-600">No certification information available</p>
                )}
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-800 mb-2">Testing Requirements</h4>
              <div className="bg-gray-50 p-4 rounded-lg">
                {results?.testing_information?.length ? (
                  <ul className="space-y-2">
                    {results.testing_information.map((test: any, index: number) => (
                      <li key={index} className="p-3 bg-white rounded mb-2">
                        <h5 className="font-medium text-gray-800">{test.standard_number} Testing</h5>
                        <p className="text-sm text-gray-600 mb-1">
                          Sample Size: {test.sample_size_requirement || 'Not specified'} |
                          Duration: {test.test_duration || 'Not specified'}
                        </p>
                        {test.testing_requirements?.length && (
                          <ul className="text-sm text-gray-500 mt-2 space-y-1">
                            {test.testing_requirements.map((req: string, idx: number) => (
                              <li key={idx}>• {req}</li>
                            ))}
                          </ul>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-600">No testing information available</p>
                )}
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-800 mb-2">Laboratory Recommendations</h4>
              <div className="bg-gray-50 p-4 rounded-lg">
                {results?.laboratory_recommendations?.length ? (
                  <ul className="space-y-2">
                    {results.laboratory_recommendations.map((lab: any, index: number) => (
                      <li key={index} className="p-3 bg-white rounded mb-2">
                        <div className="flex justify-between items-start mb-2">
                          <h5 className="font-medium text-gray-800">{lab.name}</h5>
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            lab.is_bis_recognized ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {lab.is_bis_recognized ? 'BIS Recognized' : 'Not Recognized'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mb-1">
                          {lab.location} | {lab.contact_info?.phone || 'Contact: N/A'}
                        </p>
                        <p className="text-xs text-gray-500">
                          Accreditations: {lab.accreditations?.join(', ') || 'None specified'}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-600">No laboratory recommendations found</p>
                )}
              </div>
            </div>

            {results?.compliance_analysis?.length && (
              <div>
                <h4 className="font-medium text-gray-800 mb-2">Compliance Analysis</h4>
                <div className="bg-gray-50 p-4 rounded-lg">
                  {results.compliance_analysis.map((comp: any, index: number) => (
                    <div key={index} className="mb-4 p-3 bg-white rounded">
                      <h5 className="font-medium text-gray-800">{comp.standard_number} Compliance</h5>
                      <div className="flex items-center mt-2">
                        <div className="w-1/2">
                          <p className="text-sm font-medium">Compliance: {comp.compliance_percentage.toFixed(1)}%</p>
                          <div className="bg-gray-200 rounded-full h-2.5 mt-1">
                            <div
                              className={`h-2.5 rounded-full ${
                                comp.compliance_percentage >= 80 ? 'bg-emerald-500' : comp.compliance_percentage >= 60 ? 'bg-amber-500' : 'bg-rose-500'
                              }`}
                              style={{ width: `${comp.compliance_percentage}%` }}
                            ></div>
                          </div>
                        </div>
                        <div className="ml-4 text-sm">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            comp.risk_level === 'Low' ? 'bg-green-100 text-green-800' :
                            comp.risk_level === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {comp.risk_level} Risk
                          </span>
                        </div>
                      </div>
                      {comp.missing_requirements?.length && (
                        <div className="mt-3">
                          <p className="font-medium text-gray-700 mb-1">Missing Requirements:</p>
                          <ul className="text-sm text-gray-600 space-y-1">
                            {comp.missing_requirements.map((req: string, idx: number) => (
                              <li key={idx}>• {req}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {comp.recommendations?.length && (
                        <div className="mt-3">
                          <p className="font-medium text-gray-700 mb-1">Recommendations:</p>
                          <ul className="text-sm text-gray-600 space-y-1">
                            {comp.recommendations.map((rec: string, idx: number) => (
                              <li key={idx}>• {rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Mock function to simulate API call - in real implementation, this would be replaced with actual API calls
const simulateAnalysis = async (input: any): Promise<any> => {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 1500));

  // Return mock data that matches our expected result structure
  return {
    product_understanding: {
      product_name: input.product_description.split(' ')[0] || 'Sample Product',
      category: 'Electronics & IT Equipment',
      intended_use: 'Consumer use',
      confidence: 0.85
    },
    applicable_standards: [
      { standard_number: 'IS 13252', title: 'Information Technology Equipment - Safety' },
      { standard_number: 'IS 14785', title: 'Fire Extinguishers - Portable Type' }
    ],
    certification_info: [
      {
        standard_number: 'IS 13252',
        license_required: true,
        certification_process: 'Type Testing + Factory Inspection',
        requirements: [
          'Product safety testing according to IS 13252',
          'EMC testing as per relevant standards',
          'Factory quality audit'
        ]
      }
    ],
    testing_information: [
      {
        standard_number: 'IS 13252',
        testing_requirements: [
          'Electric strength test',
          'Temperature rise test',
          'Leakage current test',
          'Mechanical strength test'
        ],
        sample_size_requirement: '3 units',
        test_duration: '2-3 weeks'
      }
    ],
    laboratory_recommendations: [
      {
        name: 'Central Power Research Institute (CPRI)',
        location: 'Bangalore, Karnataka',
        is_bis_recognized: true,
        contact_info: {
          phone: '+91-80-22272000',
          email: 'info@cpri.in'
        },
        accreditations: ['NABL', 'BIS'],
        test_scope: ['Electrical Safety', 'EMC', 'Environmental']
      },
      {
        name: 'Electronics Regional Test Laboratory (ERTL)',
        location: 'East Delhi, Delhi',
        is_bis_recognized: true,
        contact_info: {
          phone: '+91-11-22042241',
          email: 'ertl@nic.in'
        },
        accreditations: ['NABL', 'BIS'],
        test_scope: ['Electrical Safety', 'Environmental']
      }
    ],
    compliance_analysis: [
      {
        standard_number: 'IS 13252',
        compliance_percentage: 75,
        risk_level: 'Medium',
        missing_requirements: [
          'EMC testing documentation incomplete',
          'Temperature rise test report missing for variant B'
        ],
        recommendations: [
          'Complete EMC testing for all product variants',
          'Provide temperature rise test data for variant B',
          'Update user manual with safety warnings'
        ]
      }
    ],
    citation_verification: [],
    web_search_results: []
  };
};