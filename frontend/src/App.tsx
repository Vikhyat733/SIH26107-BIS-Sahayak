import { useState } from 'react';
import { Search, ShieldCheck, FlaskConical, BadgeCheck, FileCheck2, Send, Languages, AlertTriangle } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

type ComplianceCheck = {
    parameter: string;
    reported_value: string;
    requirement: string;
    unit: string;
    status: string;
    reason: string;
    evidence: string | null;
};

type ComplianceData = {
    overall_status: string;
    standard: {
        number: string;
        title: string;
    };
    product: string;
    grade?: string;
    document: {
        filename: string;
        type: string;
    };
    summary: string;
    checks: ComplianceCheck[];
    missing_fields: string[];
    warnings: string[];
    verification: {
        method: string;
        source: string;
    };
};

type LabMetadata = {
    standard: string | null;
    location: string | null;
};

type CertificationData = {
    product: string;
    standard: string;
    certification_status: string;
    qco: {
        applicable: boolean;
        title: string;
        source_url: string;
    };
    scheme: {
        scheme_name: string;
        scheme_number: string;
        source_url: string;
    };
    next_steps: string[];
};

type EvidenceItem = {
    standard_number?: string;
    id?: string;
    title?: string;
    relevance?: number;
    retrieval_reason?: string;
    evidence?: { text: string; section?: string }[];
    text?: string;
    section?: string;
    source?: string;
    document_title?: string;
    source_url?: string;
    name?: string;
    address?: string;
    remark?: string;
    standard?: string;
    scope?: string;
    product?: string;
    lab_code?: string;
    testing_charges?: string;
    validity_date?: string;
    [key: string]: unknown;
};

type SourceItem = {
    name?: string;
    url?: string;
    document?: string;
    [key: string]: unknown;
};

type Result = { 
    answer: string; 
    confidence: number;
    sources: SourceItem[];
    evidence: EvidenceItem[]; 
    needs_verification: boolean; 
    intent?: string;
    certification_data?: CertificationData;
    compliance_data?: ComplianceData;
    lab_metadata?: LabMetadata;
};

export default function App() {
  const [query, setQuery] = useState('');
  const [language, setLanguage] = useState('en');
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [labSearchOpen, setLabSearchOpen] = useState(false);
  const [labSearchQuery, setLabSearchQuery] = useState('');
  const [labSearchLocation, setLabSearchLocation] = useState('');
  const [labPage, setLabPage] = useState(1);
  
  const [complianceOpen, setComplianceOpen] = useState(false);
  const [complianceFile, setComplianceFile] = useState<File | null>(null);
  const [complianceStandard, setComplianceStandard] = useState('');
  const [complianceProduct, setComplianceProduct] = useState('');

  async function ask() {
    if (!query.trim()) return;
    setLoading(true); setResult(null); setLabPage(1);
    try {
      const r = await fetch(`${API}/assistant/ask`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query, language}) });
      if (!r.ok) {
        if (r.status >= 400 && r.status < 500) {
          throw new Error('4xx');
        } else {
          throw new Error('5xx');
        }
      }
      setResult(await r.json());
    } catch (err: unknown) {
      let answerMsg = 'Unable to connect to BIS Sahayak backend.';
      const msg = err instanceof Error ? err.message : String(err);
      if (msg === '4xx') answerMsg = 'Request could not be processed.';
      if (msg === '5xx') answerMsg = 'BIS Assistant encountered a server error.';
      setResult({answer: answerMsg, confidence:0, sources:[], evidence:[], needs_verification:true});
    } finally { setLoading(false); }
  }

  async function handleCardClick(title: string) {
    if (title === 'Find Standard') {
      const prod = prompt("Enter product description (e.g. mobile phone):");
      if (!prod) return;
      setLoading(true); setResult(null);
      try {
        const r = await fetch(`${API}/standards/recommend`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({product_description: prod}) });
        if (!r.ok) {
          if (r.status >= 400 && r.status < 500) throw new Error('4xx');
          else throw new Error('5xx');
        }
        const data = await r.json();
        if (data.recommendations && data.recommendations.length > 0) {
            let answerText = data.recommendations.map((x: EvidenceItem) => {
               const product = x.title ? x.title.split('—')[0].split('-')[0].trim().toLowerCase() : prod.toLowerCase();
               return `${x.standard_number || x.id} is identified in the available BIS evidence as covering ${product}.`;
            }).join('\n');
            answerText += '\n\nVerify current applicability and regulatory requirements before compliance action.';
            
            setResult({
              answer: answerText,
              confidence: 0.9,
              sources: data.recommendations.map((x: EvidenceItem)=>({ name: x.source, url: x.source_url, document: x.standard_number })),
              evidence: data.recommendations,
              needs_verification: false,
              intent: 'standard_recommendation'
            });
        } else {
            setResult({
              answer: "No sufficiently supported BIS standard was found for this product in the current knowledge base.\n\nTry describing the product in more detail.",
              confidence: 0,
              sources: [],
              evidence: [],
              needs_verification: true,
              intent: 'standard_recommendation'
            });
        }
      } catch (err: unknown) {
        let answerMsg = 'Unable to connect to BIS Sahayak backend.';
        const msg = err instanceof Error ? err.message : String(err);
        if (msg === '4xx') answerMsg = 'Request could not be processed.';
        if (msg === '5xx') answerMsg = 'BIS Assistant encountered a server error.';
        setResult({
          answer: answerMsg,
          confidence: 0,
          sources: [],
          evidence: [],
          needs_verification: true
        });
      } finally { setLoading(false); }
    } else if (title === 'Compliance Check') {
      setComplianceOpen(true);
    } else if (title === 'Testing Labs') {
      setLabSearchOpen(true);
    }
  }

  async function handleLabSearch() {
    setLabSearchOpen(false);
    setLoading(true); setResult(null); setLabPage(1);
    try {
      const url = new URL(`${API}/labs/search`);
      if (labSearchQuery) url.searchParams.append('query', labSearchQuery);
      if (labSearchLocation) url.searchParams.append('location', labSearchLocation);
      const r = await fetch(url.toString());
      if (!r.ok) throw new Error('Failed to fetch labs');
      const data = await r.json();
      
      if (data.results && data.results.length > 0) {
        setResult({
          answer: data.message || "Verified laboratories found.",
          confidence: 1,
          sources: [],
          evidence: data.results,
          needs_verification: false,
          intent: 'LAB_LOOKUP'
        });
      } else {
        setResult({
          answer: "No verified BIS laboratory result was found for this query.",
          confidence: 0,
          sources: [],
          evidence: [],
          needs_verification: true,
          intent: 'LAB_LOOKUP'
        });
      }
    } catch (err) {
      setResult({
        answer: 'Unable to connect to BIS Sahayak backend.',
        confidence: 0,
        sources: [],
        evidence: [],
        needs_verification: true,
        intent: 'LAB_LOOKUP'
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleComplianceSubmit() {
    setComplianceOpen(false);
    if (!complianceFile) return;
    
    setLoading(true); setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', complianceFile);
      if (complianceStandard) formData.append('standard', complianceStandard);
      if (complianceProduct) formData.append('product', complianceProduct);

      const r = await fetch(`${API}/compliance/audit`, { 
        method: 'POST', 
        body: formData 
      });
      if (!r.ok) {
        if (r.status >= 400 && r.status < 500) throw new Error('4xx');
        else throw new Error('5xx');
      }
      const data = await r.json();
      
      setResult({
        answer: "Compliance Check Completed",
        confidence: 1.0,
        sources: [],
        evidence: [],
        needs_verification: false,
        intent: 'COMPLIANCE_RESULT',
        compliance_data: data
      });
    } catch (err: unknown) {
        setResult({
          answer: 'Unable to connect to BIS Sahayak backend for compliance check.',
          confidence: 0,
          sources: [],
          evidence: [],
          needs_verification: true
        });
    } finally { setLoading(false); }
  }

  const cards = [
    [Search,'Find Standard','Product → applicable Indian Standard'],
    [BadgeCheck,'Certification','BIS certification & scheme guidance'],
    [FlaskConical,'Testing Labs','Testing requirement & lab workflow'],
    [FileCheck2,'Compliance Check','Analyze a test/MTC report'],
    [ShieldCheck,'QCO Checker','Find relevant quality-control orders'],
    [Languages,'Hindi / Multilingual','Accessible BIS assistance'],
  ] as const;

  return <div className="shell">
    <header><div><div className="eyebrow">SIH26107 · Smart Automation</div><h1>BIS Sahayak / ManakMitra</h1><p>AI-assisted Indian Standards & BIS Services for industries and consumers</p></div><div className="status">● Prototype</div></header>
    <main>
      <section className="hero">
        <h2>Ask about Indian Standards & BIS services</h2>
        <p>Get structured, evidence-aware guidance on standards, certification, QCOs, testing and compliance.</p>
        <div className="search">
          <select value={language} onChange={e=>setLanguage(e.target.value)} className="lang-select">
            <option value="en">English</option>
            <option value="hi">हिंदी (Hindi)</option>
          </select>
          <input value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==='Enter'&&ask()} placeholder="e.g. Which standard applies to TMT reinforcement bars?"/>
          <button onClick={ask} disabled={loading}><Send size={18}/>{loading?'Searching':'Ask BIS'}</button>
        </div>
      </section>
      <section className="grid">{cards.map(([Icon,title,desc])=><div className="card" key={title} onClick={()=>handleCardClick(title)} style={{cursor: 'pointer'}}><Icon size={22}/><h3>{title}</h3><p>{desc}</p></div>)}</section>
      
      {labSearchOpen && (
        <div style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000}}>
          <div style={{backgroundColor: 'white', padding: '24px', borderRadius: '8px', width: '400px', maxWidth: '90%'}}>
            <h2 style={{marginTop: 0}}>Find Testing Labs</h2>
            <div style={{marginBottom: '16px'}}>
              <label style={{display: 'block', marginBottom: '4px', fontWeight: 'bold'}}>Product / Standard</label>
              <input style={{width: '100%', padding: '8px', boxSizing: 'border-box'}} value={labSearchQuery} onChange={e=>setLabSearchQuery(e.target.value)} placeholder="Enter product or IS number" />
            </div>
            <div style={{marginBottom: '24px'}}>
              <label style={{display: 'block', marginBottom: '4px', fontWeight: 'bold'}}>Location (optional)</label>
              <input style={{width: '100%', padding: '8px', boxSizing: 'border-box'}} value={labSearchLocation} onChange={e=>setLabSearchLocation(e.target.value)} placeholder="City / State" />
            </div>
            <div style={{display: 'flex', justifyContent: 'flex-end', gap: '8px'}}>
              <button style={{padding: '8px 16px', background: '#ccc', color: '#333', border: 'none', borderRadius: '4px', cursor: 'pointer'}} onClick={() => setLabSearchOpen(false)}>Cancel</button>
              <button style={{padding: '8px 16px', background: '#0056b3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}} onClick={handleLabSearch}>Find Labs</button>
            </div>
          </div>
        </div>
      )}

      {result && (
        <section className="result">
          <div className="resultHead">
            <h2>Assistant response</h2>
            {result.intent === 'LAB_LOOKUP' && result.evidence && result.evidence.length > 0 ? (
              <span className="grounded">Verified BIS LIMS results</span>
            ) : result.intent === 'COMPLIANCE_RESULT' ? (
              <span className="grounded">Verification data available</span>
            ) : (
              <span className={!result.needs_verification?'grounded':'unverified'}>
                {!result.needs_verification?'Evidence found':'Guidance only'}
              </span>
            )}
          </div>
          {result.needs_verification && !(result.intent === 'LAB_LOOKUP' && result.evidence && result.evidence.length > 0) && (
            <div className="warning-box">
              <AlertTriangle size={18} />
              <p>Warning: Evidence insufficient. Verification required before regulatory action.</p>
            </div>
          )}
          <p style={{whiteSpace: 'pre-line'}}>{result.answer}</p>
          
          {result.intent === 'standard_recommendation' && result.evidence && result.evidence.length > 0 && (
            <div className="recommendations-section">
              <br/>
              <h3>Recommended Standards</h3>
              {result.evidence.map((x, i: number) => (
                <div key={i} className="rec-card" style={{border: '1px solid #ccc', padding: '15px', marginBottom: '10px', borderRadius: '4px'}}>
                  <h4 style={{margin: '0 0 5px 0'}}>{x.standard_number || x.id}</h4>
                  <p style={{margin: '0 0 15px 0'}}>{x.title}</p>
                  <p style={{margin: '0 0 5px 0'}}><strong>Relevance:</strong> {(x.relevance ?? 0) > 0.8 ? 'High' : 'Medium'}</p>
                  
                  {x.retrieval_reason && (
                    <p style={{margin: '0 0 10px 0'}}><strong>Why this was retrieved:</strong><br/>{x.retrieval_reason}</p>
                  )}
                  
                  {x.evidence && x.evidence.length > 0 && (
                    <div style={{margin: '15px 0', padding: '10px', backgroundColor: '#f9f9f9', borderRadius: '4px'}}>
                      <h5 style={{margin: '0 0 5px 0'}}>Evidence</h5>
                      <hr style={{margin: '5px 0', border: 'none', borderTop: '1px solid #ddd'}} />
                      {x.evidence.map((e, j: number) => (
                        <p key={j} style={{margin: '5px 0'}}>
                          "{e.text}" <br/>
                          <small style={{color: '#666'}}>- Section {e.section}</small>
                        </p>
                      ))}
                    </div>
                  )}

                  <div style={{margin: '10px 0'}}>
                    <strong>Source</strong><br/>
                    {x.source}
                    {x.source_url && <a href={x.source_url} target="_blank" rel="noreferrer" style={{marginLeft: '10px'}}>[View source]</a>}
                  </div>
                  
                  <p style={{margin: '10px 0 0 0', color: '#ff8800', fontWeight: 'bold'}}>⚠ Verify current applicability</p>
                </div>
              ))}
            </div>
          )}

          {result.intent === 'COMPLIANCE_RESULT' && result.compliance_data && (() => {
            const data = result.compliance_data;
            const statusColor = data.overall_status === 'PASS' ? '#5cb85c' : data.overall_status === 'FAIL' ? '#d9534f' : '#f0ad4e';
            
            return (
              <div className="compliance-section">
                <br/>
                <h3>COMPLIANCE RESULT</h3>
                <div style={{border: '1px solid #ccc', padding: '15px', marginBottom: '15px', borderRadius: '4px', backgroundColor: '#fdfdfd'}}>
                  <h2 style={{color: statusColor, marginTop: 0}}>{data.overall_status}</h2>
                  <p style={{margin: '0 0 5px 0'}}><strong>Standard:</strong> {data.standard?.number} {data.standard?.title && data.standard.title !== 'Unknown' ? `- ${data.standard.title}` : ''}</p>
                  <p style={{margin: '0 0 5px 0'}}><strong>Product:</strong> {data.product}</p>
                  {data.grade && <p style={{margin: '0 0 5px 0'}}><strong>Grade:</strong> {data.grade}</p>}
                  <p style={{margin: '0 0 5px 0'}}><strong>Summary:</strong> {data.summary}</p>
                  
                  {data.overall_status === 'FAIL' && data.warnings && data.warnings.length > 0 && (
                     <div style={{marginTop: '15px', padding: '10px', backgroundColor: '#ffeeee', border: '1px solid #f5c6cb', borderRadius: '4px', color: '#721c24'}}>
                       <strong>Reason:</strong>
                       <ul style={{marginTop: '5px', marginBottom: '0'}}>
                         {data.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
                       </ul>
                     </div>
                  )}
                  {data.overall_status === 'REVIEW' && (
                     <div style={{marginTop: '15px', padding: '10px', backgroundColor: '#fcf8e3', border: '1px solid #faebcc', borderRadius: '4px', color: '#8a6d3b'}}>
                       <strong>Reason:</strong><br/>
                       {data.summary}<br/>
                       <br/>
                       <strong>Action:</strong><br/>
                       Submit a complete test report or provide the missing information.
                     </div>
                  )}
                </div>

                {data.checks && data.checks.length > 0 && (
                  <div style={{marginBottom: '15px'}}>
                    <h4>CHECK RESULTS</h4>
                    <table style={{width: '100%', borderCollapse: 'collapse'}}>
                      <thead>
                        <tr style={{backgroundColor: '#f5f5f5', borderBottom: '2px solid #ddd'}}>
                          <th style={{textAlign: 'left', padding: '8px', border: '1px solid #ddd'}}>Parameter</th>
                          <th style={{textAlign: 'left', padding: '8px', border: '1px solid #ddd'}}>Reported</th>
                          <th style={{textAlign: 'left', padding: '8px', border: '1px solid #ddd'}}>Requirement</th>
                          <th style={{textAlign: 'left', padding: '8px', border: '1px solid #ddd'}}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.checks.map((chk, i: number) => (
                          <tr key={i} style={{borderBottom: '1px solid #ddd'}}>
                            <td style={{padding: '8px', border: '1px solid #ddd'}}>{chk.parameter}</td>
                            <td style={{padding: '8px', border: '1px solid #ddd'}}>{chk.reported_value} {chk.unit}</td>
                            <td style={{padding: '8px', border: '1px solid #ddd'}}>{chk.requirement}</td>
                            <td style={{padding: '8px', border: '1px solid #ddd', color: chk.status === 'PASS' ? 'green' : chk.status === 'FAIL' ? 'red' : 'orange'}}>
                              <strong>{chk.status}</strong>
                              {chk.evidence && <div style={{fontSize: '0.85em', color: '#666', marginTop: '4px'}}>Rule: {chk.evidence}</div>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <div style={{padding: '10px', backgroundColor: '#e9f7ef', border: '1px solid #d4efdf', borderRadius: '4px', color: '#155724'}}>
                  <strong>Evidence / Verification</strong><br/>
                  Verification method: {data.verification?.method || 'Deterministic rule engine'}<br/>
                  Source: {data.verification?.source || 'BIS standard schema'}
                </div>
                
                <p style={{marginTop: '15px', fontStyle: 'italic', color: '#666'}}>
                  Compliance status calculated using deterministic verification rules. AI is used only to explain the result.
                </p>
              </div>
            );
          })()}

          {result.intent === 'CERTIFICATION_QUERY' && result.certification_data && (
            <div className="certification-section">
              <br/>
              <h3>Certification & QCO Status</h3>
              <div style={{border: '1px solid #ccc', padding: '15px', marginBottom: '10px', borderRadius: '4px', backgroundColor: '#fdfdfd'}}>
                <div style={{marginBottom: '10px'}}>
                  <strong>Certification Status:</strong><br/>
                  <span style={{color: result.certification_data.certification_status === 'mandatory' ? '#d9534f' : result.certification_data.certification_status === 'unknown' ? '#f0ad4e' : '#5cb85c', fontWeight: 'bold', fontSize: '1.1em'}}>
                    {result.certification_data.certification_status === 'mandatory' ? 'Mandatory' : 
                     result.certification_data.certification_status === 'voluntary' ? 'Voluntary' : 
                     result.certification_data.certification_status === 'conditional' ? 'Conditional' : 'Not verified'}
                  </span>
                </div>
                <div style={{marginBottom: '10px'}}>
                  <strong>Applicable Standard:</strong><br/>
                  {result.certification_data.standard} - {result.certification_data.product}
                </div>
                <div style={{marginBottom: '10px'}}>
                  <strong>QCO:</strong><br/>
                  {result.certification_data.qco.applicable ? result.certification_data.qco.title : 'Not established'}
                  {result.certification_data.qco.source_url && result.certification_data.qco.applicable && (
                    <span style={{marginLeft: '10px'}}><a href={result.certification_data.qco.source_url} target="_blank" rel="noreferrer">[View source]</a></span>
                  )}
                </div>
                <div style={{marginBottom: '10px'}}>
                  <strong>Certification Scheme:</strong><br/>
                  {result.certification_data.scheme.scheme_name} ({result.certification_data.scheme.scheme_number})
                  {result.certification_data.scheme.source_url && (
                    <span style={{marginLeft: '10px'}}><a href={result.certification_data.scheme.source_url} target="_blank" rel="noreferrer">[View source]</a></span>
                  )}
                </div>
                {result.certification_data.next_steps && result.certification_data.next_steps.length > 0 && (
                  <div style={{marginTop: '15px'}}>
                    <strong>What you need to do:</strong>
                    <ol style={{paddingLeft: '20px', marginTop: '5px', marginBottom: '0'}}>
                      {result.certification_data.next_steps.map((step: string, i: number) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            </div>
          )}

          {result.intent === 'LAB_LOOKUP' && result.evidence && result.evidence.length > 0 && (() => {
            const currentQuery = query || labSearchQuery || '';
            const lowerQuery = currentQuery.toLowerCase();
            
            const meta: Partial<LabMetadata> = result.lab_metadata || {};
            const extStandard = meta.standard || currentQuery;
            const extLocation = (meta.location || labSearchLocation).trim();
            const lowerLoc = extLocation.toLowerCase();

            const getScore = (lab: EvidenceItem) => {
              let score = 0;
              const standard = (lab.standard || '').toLowerCase();
              const scope = (lab.scope || '').toLowerCase();
              const product = (lab.product || '').toLowerCase();
              
              if (lowerQuery && (standard.includes(lowerQuery) || scope.includes(lowerQuery))) score += 100;
              if (lowerQuery && product.includes(lowerQuery)) score += 50;
              return score;
            };

            const matchedLabs: EvidenceItem[] = [];
            const otherLabs: EvidenceItem[] = [];

            result.evidence.forEach((lab) => {
              const name = (lab.name || '').toLowerCase();
              const address = (lab.address || '').toLowerCase();
              const remark = (lab.remark || '').toLowerCase();

              let isLocMatch = false;
              if (lowerLoc && (name.includes(lowerLoc) || remark.includes(lowerLoc) || address.includes(lowerLoc))) {
                isLocMatch = true;
              }
              if (isLocMatch) {
                matchedLabs.push(lab);
              } else {
                otherLabs.push(lab);
              }
            });

            matchedLabs.sort((a, b) => getScore(b) - getScore(a));
            otherLabs.sort((a, b) => getScore(b) - getScore(a));

            const combinedLabs = extLocation ? [...matchedLabs, ...otherLabs] : [...otherLabs];
            
            const totalPages = Math.ceil(combinedLabs.length / 10);
            const startIndex = (labPage - 1) * 10;
            const currentLabs = combinedLabs.slice(startIndex, startIndex + 10);
            
            let renderedMatchedHeader = false;
            let renderedOtherHeader = false;

            return (
              <div className="labs-section">
                <br/>
                <h3>Testing Laboratories</h3>
                <div style={{marginBottom: '15px'}}>
                   <p style={{fontSize: '1.1em', margin: '0 0 5px 0'}}><strong>{combinedLabs.length} BIS laboratories found</strong></p>
                   <p style={{margin: '0 0 2px 0'}}>Standard: {extStandard}</p>
                   {extLocation && <p style={{margin: '0 0 15px 0'}}>Location: {extLocation}</p>}
                </div>
                
                {extLocation && matchedLabs.length === 0 && (
                   <div style={{marginBottom: '15px', color: '#d9534f'}}>
                     No BIS LIMS laboratory matching {extStandard} was found in {extLocation}.
                   </div>
                )}
                
                {currentLabs.map((lab, i: number) => {
                  const isMatched = extLocation && matchedLabs.includes(lab);
                  
                  let header = null;
                  if (isMatched && !renderedMatchedHeader) {
                      renderedMatchedHeader = true;
                      header = <h4 style={{marginTop: '20px', marginBottom: '10px', color: '#0056b3'}}>Labs matching {extLocation}</h4>;
                  } else if (!isMatched && !renderedOtherHeader && extLocation) {
                      renderedOtherHeader = true;
                      header = <h4 style={{marginTop: '20px', marginBottom: '10px', color: '#666'}}>Other BIS LIMS labs for {extStandard}</h4>;
                  }

                  return (
                    <div key={i}>
                      {header}
                      <div className="lab-card" style={{border: '1px solid #ccc', padding: '15px', marginBottom: '10px', borderRadius: '4px', backgroundColor: '#fdfdfd'}}>
                        <h4 style={{margin: '0 0 5px 0'}}>{lab.name}</h4>
                        <p style={{margin: '0 0 5px 0'}}><strong>Code:</strong> {lab.lab_code}</p>
                        <p style={{margin: '0 0 5px 0'}}><strong>Product:</strong> {lab.product}</p>
                        <p style={{margin: '0 0 5px 0'}}><strong>Standard:</strong> {lab.standard}</p>
                        <p style={{margin: '0 0 5px 0'}}><strong>Scope:</strong> {lab.scope}</p>
                        <p style={{margin: '0 0 5px 0'}}><strong>Testing Charges:</strong> {lab.testing_charges}</p>
                        <p style={{margin: '0 0 5px 0'}}><strong>Validity:</strong> {lab.validity_date}</p>
                        {lab.remark && <p style={{margin: '0 0 5px 0'}}><strong>Remarks:</strong> {lab.remark}</p>}
                        {lab.source_url && (
                          <p style={{margin: '10px 0 0 0'}}>
                            <a href={lab.source_url} target="_blank" rel="noreferrer">View on BIS LIMS Source</a>
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
                
                {totalPages > 1 && (
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', padding: '10px', background: '#f5f5f5', borderRadius: '4px'}}>
                    <button 
                      onClick={() => setLabPage(Math.max(1, labPage - 1))} 
                      disabled={labPage === 1}
                      style={{padding: '5px 10px', cursor: labPage === 1 ? 'not-allowed' : 'pointer'}}
                    >
                      [← Previous]
                    </button>
                    <span>[Page {labPage} of {totalPages}]</span>
                    <button 
                      onClick={() => setLabPage(Math.min(totalPages, labPage + 1))} 
                      disabled={labPage === totalPages}
                      style={{padding: '5px 10px', cursor: labPage === totalPages ? 'not-allowed' : 'pointer'}}
                    >
                      [Next →]
                    </button>
                  </div>
                )}
              </div>
            );
          })()}

          {result.intent !== 'standard_recommendation' && result.intent !== 'LAB_LOOKUP' && result.intent !== 'COMPLIANCE_RESULT' && (
            <div className="evidence-section">
              <br/>
              <h3>Evidence</h3>
              {result.evidence && result.evidence.length > 0 ? result.evidence.map((x, i: number) => (
                <div key={i} style={{marginBottom: '10px'}}>
                  <div>────────────────────────</div>
                  <div style={{marginTop: '10px', fontStyle: 'italic', paddingLeft: '10px', borderLeft: '3px solid #ccc'}}>"{x.text}"</div>
                  <div style={{marginTop: '10px'}}><strong>Source:</strong><br/>{x.source}</div>
                  <div style={{marginTop: '10px'}}><strong>Document:</strong><br/>{x.document_title || x.title || x.id}</div>
                  {x.section && <div style={{marginTop: '10px'}}><strong>Section:</strong><br/>{x.section}</div>}
                  {x.source_url && (
                    <div style={{marginTop: '10px'}}>
                      <a href={x.source_url} target="_blank" rel="noreferrer">[View source]</a>
                    </div>
                  )}
                  <div style={{marginTop: '10px'}}>────────────────────────</div>
                </div>
              )) : (
                <div className="warning-box" style={{marginTop: '10px'}}>
                   <p>Answer generated from available BIS information, but a directly attributable evidence excerpt was not available.</p>
                </div>
              )}
            </div>
          )}
        </section>
      )}
      <section className="trust"><ShieldCheck size={22}/><div><b>Trust-first design</b><p>The language model is an explanation layer; authoritative evidence and deterministic checks remain the source of truth.</p></div></section>
      {complianceOpen && (
        <div style={{position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000}}>
          <div style={{backgroundColor: 'white', padding: '24px', borderRadius: '8px', width: '400px', maxWidth: '90%'}}>
            <h2 style={{marginTop: 0}}>Compliance Check</h2>
            <div style={{marginBottom: '16px'}}>
              <label style={{display: 'block', marginBottom: '4px', fontWeight: 'bold'}}>Upload Test Report / MTC</label>
              <input type="file" accept=".pdf,.txt,.json,.csv" style={{width: '100%', boxSizing: 'border-box'}} onChange={e=>setComplianceFile(e.target.files?.[0] || null)} />
            </div>
            <div style={{marginBottom: '16px'}}>
              <label style={{display: 'block', marginBottom: '4px', fontWeight: 'bold'}}>Standard (Optional)</label>
              <input style={{width: '100%', padding: '8px', boxSizing: 'border-box'}} value={complianceStandard} onChange={e=>setComplianceStandard(e.target.value)} placeholder="Auto-detect" />
            </div>
            <div style={{marginBottom: '24px'}}>
              <label style={{display: 'block', marginBottom: '4px', fontWeight: 'bold'}}>Product (Optional)</label>
              <input style={{width: '100%', padding: '8px', boxSizing: 'border-box'}} value={complianceProduct} onChange={e=>setComplianceProduct(e.target.value)} placeholder="Optional" />
            </div>
            <div style={{display: 'flex', justifyContent: 'flex-end', gap: '8px'}}>
              <button style={{padding: '8px 16px', background: '#ccc', color: '#333', border: 'none', borderRadius: '4px', cursor: 'pointer'}} onClick={() => setComplianceOpen(false)}>Cancel</button>
              <button style={{padding: '8px 16px', background: '#0056b3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}} onClick={handleComplianceSubmit} disabled={!complianceFile}>Analyze Document</button>
            </div>
          </div>
        </div>
      )}
    </main>
  </div>
}
