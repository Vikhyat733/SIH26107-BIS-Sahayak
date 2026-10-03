import pytest
import os
from unittest.mock import patch, MagicMock
from app.llm import EvidencePacket, EvidenceItem, get_provider, GeneratedAnswer
from app.llm.provider import GeminiProvider

@pytest.fixture
def sample_packet():
    return EvidencePacket(
        query="What is IS 1786?",
        intent="STANDARD_LOOKUP",
        evidence=[
            EvidenceItem(
                document_id="IS_1786_2008",
                title="High strength deformed steel bars",
                excerpt="This standard covers requirements for high strength deformed steel bars.",
                relevance_score=0.9
            )
        ]
    )

def test_evidence_packet_construction(sample_packet):
    assert sample_packet.query == "What is IS 1786?"
    assert len(sample_packet.evidence) == 1
    assert sample_packet.evidence[0].document_id == "IS_1786_2008"

def test_missing_api_key_fallback(sample_packet):
    with patch.dict(os.environ, clear=True):
        provider = GeminiProvider()
        result = provider.generate(sample_packet)
        assert result is None

@patch("app.llm.provider.httpx.Client.post")
def test_successful_generation(mock_post, sample_packet):
    # Mocking successful API response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": '{"answer": "IS 1786 covers high strength deformed steel bars.", "evidence_refs": ["IS_1786_2008"]}'
                }]
            }
        }]
    }
    mock_post.return_value = mock_resp
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        provider = GeminiProvider()
        result = provider.generate(sample_packet)
        
        assert result is not None
        assert result.answer == "IS 1786 covers high strength deformed steel bars."
        assert "IS_1786_2008" in result.evidence_refs

@patch("app.llm.provider.httpx.Client.post")
def test_invalid_evidence_ref_stripped(mock_post, sample_packet):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": '{"answer": "Test", "evidence_refs": ["FAKE_ID"]}'
                }]
            }
        }]
    }
    mock_post.return_value = mock_resp
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        provider = GeminiProvider()
        result = provider.generate(sample_packet)
        
        assert result is not None
        # FAKE_ID should be stripped out because it's not in the packet
        assert len(result.evidence_refs) == 0

@patch("app.llm.provider.httpx.Client.post")
def test_malformed_response_fallback(mock_post, sample_packet):
    mock_resp = MagicMock()
    # Malformed JSON in response
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": 'This is not JSON'
                }]
            }
        }]
    }
    mock_post.return_value = mock_resp
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        provider = GeminiProvider()
        result = provider.generate(sample_packet)
        assert result is None
        
@patch("app.llm.provider.httpx.Client.post")
def test_http_error_fallback(mock_post, sample_packet):
    mock_post.side_effect = Exception("Timeout")
    
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        provider = GeminiProvider()
        result = provider.generate(sample_packet)
        assert result is None
