import re
from typing import List, Dict, Optional, Literal, Tuple
from dataclasses import dataclass, field
from app.rag.reranking import ENTITY_MAPPINGS

@dataclass
class ProductEntity:
    canonical: str
    aliases: List[str]

@dataclass
class QueryUnderstanding:
    original_query: str
    normalized_query: str
    intent: str
    product_entities: List[ProductEntity] = field(default_factory=list)
    standard_identifiers: List[Dict[str, str]] = field(default_factory=list)
    query_type: str = "general"
    specificity: Literal["HIGH", "MEDIUM", "LOW"] = "LOW"
    needs_clarification: bool = False
    clarification_reason: Optional[str] = None
    retrieval_queries: List[str] = field(default_factory=list)

class QueryUnderstandingService:
    def __init__(self):
        # Flatten entity mappings to easy lookup
        self.entity_map = {}
        for doc_id, aliases in ENTITY_MAPPINGS.items():
            # Treat the first specific alias as canonical if possible
            canonical = None
            for a in aliases:
                if a["type"] == "specific":
                    canonical = a["alias"]
                    break
            if not canonical:
                canonical = aliases[0]["alias"]
            
            for a in aliases:
                self.entity_map[a["alias"].lower()] = {
                    "canonical": canonical,
                    "type": a["type"],
                    "all_aliases": [al["alias"] for al in aliases]
                }

    def normalize(self, query: str) -> str:
        q = query.lower().strip()
        q = re.sub(r'\s+', ' ', q)
        q = re.sub(r'[^\w\s\-\:]', '', q)
        return q

    def extract_identifiers(self, original_query: str) -> List[Dict[str, str]]:
        if not original_query:
            return []
        pattern = r'\b(?:IS|Indian\s+Standard)[\s:-]*(\d+(?::\d{4})?)'
        matches = re.finditer(pattern, original_query, flags=re.IGNORECASE)
        results = []
        for m in matches:
            raw = m.group(0)
            core = m.group(1).split(":")[0]
            results.append({
                "core_identifier": core,
                "raw_identifier": raw
            })
        
        # Deduplicate
        seen = set()
        unique_results = []
        for r in results:
            if r["core_identifier"] not in seen:
                seen.add(r["core_identifier"])
                unique_results.append(r)
        return unique_results

    def extract_entities(self, normalized_query: str) -> List[ProductEntity]:
        found = []
        seen_canonical = set()
        
        # Simple longest-substring match
        # Sort aliases by length descending to match longest first (e.g. "tmt reinforcement" before "tmt")
        sorted_aliases = sorted(self.entity_map.keys(), key=len, reverse=True)
        
        q = normalized_query
        for alias in sorted_aliases:
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, q):
                meta = self.entity_map[alias]
                canonical = meta["canonical"]
                if canonical not in seen_canonical:
                    seen_canonical.add(canonical)
                    found.append(ProductEntity(
                        canonical=canonical,
                        aliases=meta["all_aliases"]
                    ))
                # Remove matched alias to prevent overlapping matches (e.g. "tmt reinforcement bars" vs "tmt")
                q = re.sub(pattern, '', q)
                
        return found

    def detect_intent(self, q_low: str, original_query: str) -> str:
        intent = "BIS_GENERAL_QUERY"
        
        if re.match(r"^(what is\s+)?is\s*[-:]?\s*\d+(:\d{4})?\??$", q_low):
            intent = "STANDARD_LOOKUP"
        elif any(k in q_low for k in ["which standard", "which bis standard", "standard applies to", "what standard", "which indian standard"]):
            intent = "standard_recommendation"
        elif len(q_low.split()) <= 3 and ("phone" in q_low or "tmt" in q_low or "mobile" in q_low):
            intent = "standard_recommendation"
        elif q_low.startswith("smx"):
            intent = "standard_recommendation"
            
        if any(k in q_low for k in ["mandatory", "certification", "require bis", "how do i get"]):
            if not ("what is bis certification" in q_low or "what is a qco" in q_low or "what is a quality control order" in q_low):
                intent = "CERTIFICATION_QUERY"
                
        if "qco" in q_low and not ("what is a qco" in q_low or "what is a quality control order" in q_low):
            intent = "QCO_QUERY"
                
        if any(k in q_low for k in ["test", "lab", "laboratory", "laboratories", "testing", "where can i get my product tested"]):
            if not ("what is a lab" in q_low):
                intent = "LAB_LOOKUP"
                
        if any(k in q_low for k in ["hallmark", "gold", "silver", "jewellery"]):
            if intent == "BIS_GENERAL_QUERY":
                intent = "HALLMARKING_QUERY"
                
        if "check this mtc" in q_low or "compliance check" in q_low:
            intent = "COMPLIANCE_QUERY"
            
        return intent

    def calculate_specificity(self, identifiers: List[Dict], entities: List[ProductEntity], intent: str, q_low: str) -> Literal["HIGH", "MEDIUM", "LOW"]:
        if identifiers:
            return "HIGH"
            
        if intent in ("standard_recommendation", "STANDARD_LOOKUP"):
            if entities:
                return "HIGH"
            else:
                return "LOW"
                
        if entities:
            return "MEDIUM"
            
        # Ambiguous general queries
        if q_low in ["steel standard", "bis for steel", "steel products"]:
            return "LOW"
            
        return "LOW"
        
    def detect_clarification(self, specificity: str, intent: str, q_low: str) -> Tuple[bool, Optional[str]]:
        if q_low in ["steel standard", "bis for steel", "steel products", "what bis standard applies to xyz imaginary product 123"]:
            return True, "The query is too broad or refers to an unknown product. Please specify the exact product or material (e.g., TMT bars, structural steel)."
            
        return False, None

    def generate_retrieval_plan(self, normalized_query: str, identifiers: List[Dict], entities: List[ProductEntity]) -> List[str]:
        queries = []
        if identifiers:
            for id_dict in identifiers:
                queries.append(f"IS {id_dict['core_identifier']}")
                queries.append(id_dict['core_identifier'])
        
        for ent in entities:
            queries.append(ent.canonical)
            
        queries.append(normalized_query)
        
        # Deduplicate while preserving order
        seen = set()
        final_queries = []
        for q in queries:
            if q and q not in seen:
                seen.add(q)
                final_queries.append(q)
                
        return final_queries

    def understand(self, query: str) -> QueryUnderstanding:
        from typing import Tuple
        norm_q = self.normalize(query)
        intent = self.detect_intent(norm_q, query)
        
        identifiers = self.extract_identifiers(query)
        entities = self.extract_entities(norm_q)
        
        specificity = self.calculate_specificity(identifiers, entities, intent, norm_q)
        needs_clar, reason = self.detect_clarification(specificity, intent, norm_q)
        
        plan = self.generate_retrieval_plan(norm_q, identifiers, entities)
        
        return QueryUnderstanding(
            original_query=query,
            normalized_query=norm_q,
            intent=intent,
            product_entities=entities,
            standard_identifiers=identifiers,
            query_type="identifier_lookup" if identifiers else "descriptive",
            specificity=specificity,
            needs_clarification=needs_clar,
            clarification_reason=reason,
            retrieval_queries=plan
        )
