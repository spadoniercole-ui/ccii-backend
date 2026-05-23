from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Profilo(Base):
    __tablename__ = "profili"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    
    # Relazione con la tabella ponte
    moduli = relationship("ProfiloModulo", back_populates="profilo")

class Modulo(Base):
    __tablename__ = "moduli"
    
    id = Column(Integer, primary_key=True, index=True)
    codice = Column(String, unique=True, nullable=False)
    prefisso = Column(String(2), nullable=False) # es: CD
    nome = Column(String, nullable=False)

class ProfiloModulo(Base):
    __tablename__ = "profilo_modulo"
    
    id = Column(Integer, primary_key=True, index=True)
    profilo_id = Column(Integer, ForeignKey("profili.id"), nullable=False)
    modulo_id = Column(Integer, ForeignKey("moduli.id"), nullable=False)
    
    # Campi per il versionamento e tracciabilità
    data_inizio = Column(DateTime, default=func.now(), nullable=False)
    data_fine = Column(DateTime, nullable=True) # Se None, è la versione attiva
    versione = Column(Integer, default=1, nullable=False)
    is_old = Column(Integer, default=0) # 0 = attivo, 1 = archiviato
    
    # Indice per ottimizzare la ricerca delle versioni attive
    __table_args__ = (
        Index('idx_profilo_modulo_active', 'profilo_id', 'modulo_id', 'data_fine'),
    )
    
    profilo = relationship("Profilo", back_populates="moduli")
    modulo = relationship("Modulo")
