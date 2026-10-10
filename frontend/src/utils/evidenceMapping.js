export function parseEvidence(x, resultSources, index) {
    let standardCode = x.standard_number || x.id || (resultSources && resultSources[index] ? resultSources[index].document : null);
    let docTitle = x.document_title || x.title;
    let sourceOrg = x.source || 'Unknown Source';
    let sourceUrl = x.source_url;
    let verificationStatus = x.verification_status;
    let excerpts = [];
    let rawText = x.text;
    if (rawText && typeof rawText === 'string' && rawText.startsWith('{')) {
        try {
            let parsedText = JSON.parse(rawText);
            standardCode = parsedText.standard_code || standardCode;
            docTitle = parsedText.title || docTitle;
            sourceOrg = parsedText.source || sourceOrg;
            sourceUrl = parsedText.source_url || sourceUrl;
            verificationStatus = parsedText.verification_status || verificationStatus;
            if (parsedText.evidence)
                excerpts = parsedText.evidence;
        }
        catch (e) {
            let matchCode = rawText.match(/"standard_code"\s*:\s*"([^"]+)"/);
            if (matchCode)
                standardCode = matchCode[1] || standardCode;
            let matchTitle = rawText.match(/"title"\s*:\s*"([^"]+)"/);
            if (matchTitle)
                docTitle = matchTitle[1] || docTitle;
            let matchExcerpt = rawText.match(/"evidence"\s*:\s*\[\s*\{\s*"text"\s*:\s*"((?:[^"\\]|\\.)*)/);
            if (matchExcerpt) {
                let textStr = matchExcerpt[1];
                textStr = textStr.replace(/\.\.\.$/, '') + "...";
                excerpts = [{ text: textStr }];
            }
        }
    }
    else if (rawText && typeof rawText === 'string') {
        excerpts = [{ text: rawText, section: x.section }];
    }
    standardCode = standardCode || docTitle || 'BIS Document';
    return {
        standardCode,
        docTitle,
        sourceOrg,
        sourceUrl,
        verificationStatus,
        excerpts
    };
}
