"""
Lexicon Repository - Firestore lexicon collection queries
Primary dictionary source for IKA generation
"""
from google.cloud import firestore
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class LexiconRepository:
    """Manages Firestore lexicon collection queries"""
    
    def __init__(self, firestore_client: firestore.Client, collection_name: str = "lexicon"):
        self.db = firestore_client
        self.collection_name = collection_name
        self.collection_ref = self.db.collection(collection_name)
    
    def find_by_source_text(self, source_text: str) -> Optional[Dict]:
        """
        Find lexicon entry by source_text (English, case-insensitive).
        Returns the first matching document.
        """
        source_lower = source_text.lower().strip()
        
        # Try normalized field first if it exists
        try:
            query = self.collection_ref.where("source_text_lc", "==", source_lower).limit(1)
            docs = list(query.stream())
            if docs:
                return self._doc_to_dict(docs[0])
        except Exception:
            pass
        
        # Fallback: fetch and filter (for 659 entries, this is acceptable)
        try:
            all_docs = self.collection_ref.stream()
            for doc in all_docs:
                data = doc.to_dict()
                if data.get("source_text", "").lower() == source_lower:
                    return self._doc_to_dict(doc)
        except Exception as e:
            logger.error(f"Fallback lookup failed: {e}")
        
        return None
    
    def find_by_target_text(self, target_text: str) -> Optional[Dict]:
        """
        Find lexicon entry by target_text (Ika, case-insensitive).
        Used for audio_url lookup.
        """
        target_lower = target_text.lower().strip()
        
        # Try normalized field first
        try:
            query = self.collection_ref.where("target_text_lc", "==", target_lower).limit(1)
            docs = list(query.stream())
            if docs:
                return self._doc_to_dict(docs[0])
        except Exception:
            pass
        
        # Fallback: fetch and filter
        try:
            all_docs = self.collection_ref.stream()
            for doc in all_docs:
                data = doc.to_dict()
                if data.get("target_text", "").lower() == target_lower:
                    return self._doc_to_dict(doc)
        except Exception as e:
            logger.error(f"Fallback lookup by target failed: {e}")
        
        return None
    
    def find_by_pos(self, pos: str, domain: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Find lexicon entries by part of speech (POS).
        Optionally filter by domain.
        
        Args:
            pos: Part of speech (noun, verb, adjective, etc.)
            domain: Optional domain filter
            limit: Maximum number of results
        
        Returns:
            List of lexicon entries
        """
        try:
            query = self.collection_ref.where("pos", "==", pos).limit(limit)
            if domain:
                query = query.where("domain", "==", domain)
            
            docs = list(query.stream())
            return [self._doc_to_dict(doc) for doc in docs]
        except Exception as e:
            logger.warning(f"POS lookup failed (pos field may not exist): {e}")
            return []
    
    def find_by_domain(self, domain: str, limit: int = 20) -> List[Dict]:
        """Find lexicon entries by domain"""
        try:
            query = self.collection_ref.where("domain", "==", domain).limit(limit)
            docs = list(query.stream())
            return [self._doc_to_dict(doc) for doc in docs]
        except Exception as e:
            logger.error(f"Domain lookup failed: {e}")
            return []
    
    def get_all(self) -> List[Dict]:
        """Get all lexicon entries (for small lexicons)"""
        try:
            docs = self.collection_ref.stream()
            return [self._doc_to_dict(doc) for doc in docs]
        except Exception as e:
            logger.error(f"Failed to get all entries: {e}")
            return []

    def search_by_source_prefix(self, prefix: str, limit: int = 25) -> List[Dict]:
        """
        Find lexicon entries whose English (source_text) starts with the given prefix.
        Case-insensitive. Used for dictionary lookup.
        """
        prefix_lower = prefix.lower().strip()
        if not prefix_lower:
            return []
        out: List[Dict] = []
        try:
            for doc in self.collection_ref.stream():
                data = doc.to_dict()
                src = (data.get("source_text") or "").lower()
                if src.startswith(prefix_lower):
                    out.append(self._doc_to_dict(doc))
                    if len(out) >= limit:
                        break
        except Exception as e:
            logger.error(f"Dictionary prefix lookup failed: {e}")
        return out

    def _doc_to_dict(self, doc: firestore.DocumentSnapshot) -> Dict:
        """Convert Firestore document to dictionary"""
        data = doc.to_dict()
        data["doc_id"] = doc.id
        return data
