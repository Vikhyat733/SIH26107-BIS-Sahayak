import { parseEvidence } from '../src/utils/evidenceMapping';
import assert from 'assert';

function runTests() {
    console.log("Running evidence mapping tests...");
    
    // Test 1: Standard Evidence Item with truncated JSON
    const truncatedRawText = '{"standard_code": "IS 1786:2008", "title": "High Strength Deformed Steel Bars and Wires", "source": "Bureau of Indian Standards", "source_url": "https://www.bis.gov.in/", "verification_status": "authoritative", "evidence": [{"text": "This standard covers the requirements of deformed steel bars and wires...';
    const x1 = {
        text: truncatedRawText,
        document_title: 'High Strength Deformed Steel Bars and Wires',
        source: 'Bureau of Indian Standards',
        source_url: 'https://www.bis.gov.in/',
        verification_status: 'authoritative',
        document_type: 'standard'
    };
    const sources1 = [
        { document: 'IS 1786:2008' }
    ];
    
    const res1 = parseEvidence(x1, sources1, 0);
    assert.strictEqual(res1.standardCode, 'IS 1786:2008');
    assert.strictEqual(res1.docTitle, 'High Strength Deformed Steel Bars and Wires');
    assert.strictEqual(res1.sourceOrg, 'Bureau of Indian Standards');
    assert.strictEqual(res1.excerpts[0].text, 'This standard covers the requirements of deformed steel bars and wires...');

    // Test 2: General BIS Document without standard code
    const rawTextGen = '{"title": "Hallmarking Guidelines", "source": "Bureau of Indian Standards", "evidence": [{"text": "These are the hallmarking guidelines for jewellers..."}]}';
    const x2 = {
        text: rawTextGen,
        document_title: 'Hallmarking Guidelines',
        source: 'Bureau of Indian Standards',
        document_type: 'general'
    };
    const sources2 = [
        { document: 'Hallmarking Guidelines' }
    ];

    const res2 = parseEvidence(x2, sources2, 0);
    assert.strictEqual(res2.standardCode, 'Hallmarking Guidelines');
    assert.strictEqual(res2.docTitle, 'Hallmarking Guidelines');
    
    console.log("All tests passed!");
}

runTests();
