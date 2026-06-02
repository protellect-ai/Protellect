from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class VariantCache(Base):
    __tablename__ = 'variant_cache'

    # Primary Identifiers
    id = Column(Integer, primary_key=True)
    vcf_id = Column(String, nullable=False, unique=True, index=True) # e.g., chr7:g.5518138:A:T
    
    # Source Data
    clinvar_significance = Column(String)
    gnomad_af = Column(Float)
    omim_disease = Column(String)
    uniprot_annotations = Column(JSON)
    
    # Protellect Conflict Flags
    is_conflicting = Column(Boolean, default=False)
    conflict_reason = Column(String, nullable=True)
    
    # Caching Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def evaluate_conflicts(self):
        """
        Conflict detection logic: 
        ClinVar pathogenic flags combined with gnomAD AF > 0.01% (0.0001) 
        are flagged as potential discrepancies.
        """
        self.is_conflicting = False
        self.conflict_reason = None

        clinvar_is_pathogenic = False
        if self.clinvar_significance and any(term in self.clinvar_significance.lower() for term in ['pathogenic', 'likely pathogenic']):
            clinvar_is_pathogenic = True
            
        gnomad_is_benign = (self.gnomad_af is not None and self.gnomad_af > 0.0001)

        if clinvar_is_pathogenic and gnomad_is_benign:
            self.is_conflicting = True
            self.conflict_reason = f"ClinVar classifies as Pathogenic, but gnomAD Allele Frequency is {self.gnomad_af} (>0.01%)."


from sqlalchemy.orm import Session

def get_or_create_variant(session: Session, vcf_id: str, fetch_api_callback=None) -> VariantCache:
    """
    Checks the local cache first. If it doesn't exist, fetches from APIs,
    evaluates conflicts, saves to database, and returns the result.
    """
    # 1. Check local cache
    cached_variant = session.query(VariantCache).filter_by(vcf_id=vcf_id).first()
    if cached_variant:
        return cached_variant

    # 2. Cache miss - fetch from live APIs (Simulated callback)
    if not fetch_api_callback:
        raise ValueError("Variant not in cache and no API callback provided.")
    
    raw_data = fetch_api_callback(vcf_id)

    # 3. Create new cache record
    new_variant = VariantCache(
        vcf_id=vcf_id,
        clinvar_significance=raw_data.get('clinvar_significance'),
        gnomad_af=raw_data.get('gnomad_af'),
        omim_disease=raw_data.get('omim_disease'),
        uniprot_annotations=raw_data.get('uniprot_annotations')
    )

    # 4. Evaluate discrepancies
    new_variant.evaluate_conflicts()

    # 5. Save to DB & return
    session.add(new_variant)
    session.commit()
    
    return new_variant
