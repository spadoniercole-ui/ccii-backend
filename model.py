from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum, Table
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

# --- TABELLE DI GIUNZIONE (MANY-TO-MANY) PER I PROFILI ---

# Associazione tra Profili e Moduli
profilo_moduli = Table(
    'profilo_moduli',
    Base.metadata,
    Column('profilo_id', Integer, ForeignKey('profili_utente.id', ondelete='CASCADE'), primary_key=True),
    Column('modulo_id', Integer, ForeignKey('moduli_sistema.id', ondelete='CASCADE'), primary_key=True)
)

# Associazione tra Profili e Report
profilo_report = Table(
    'profilo_report',
    Base.metadata,
    Column('profilo_id', Integer, ForeignKey('profili_utente.id', ondelete='CASCADE'), primary_key=True),
    Column('report_id', Integer, ForeignKey('report_sistema.id', ondelete='CASCADE'), primary_key=True)
)

# --- ENUM PER I RUOLI BASE ---
class RuoloBaseEnum(enum.Enum):
    ADMIN_SPAZIO = "ADMIN_SPAZIO"
    OPERATORE = "OPERATORE"
    CONSULTATORE = "CONSULTATORE"

# --- MODELLI DEL DATABASE ---

class Licenza(Base):
    __tablename__ = 'licenze'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    intestatario = Column(String, nullable=False)
    max_spazi = Column(Integer, default=1)
    max_utenti_totali = Column(Integer, default=3)      # Limite complessivo della licenza
    max_aziende_totali = Column(Integer, default=3)     # Scaglioni: 3, 10, o oltre (es. 9999)
    data_scadenza = Column(Date, nullable=False)
    
    # Relazione con gli spazi attivati
    spazi = relationship("Spazio", back_populates="licenza")

class Spazio(Base):
    __tablename__ = 'spazi'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    licenza_id = Column(Integer, ForeignKey('licenze.id', ondelete='RESTRICT'), nullable=False)
    nome_spazio = Column(String, nullable=False)
    tipologia = Column(String, nullable=False) # Studio, Azienda, Ente, Associazione
    
    licenza = relationship("Licenza", back_populates="spazi")
    utenti = relationship("Utente", back_populates="spazio")

class ModuloSistema(Base):
    __tablename__ = 'moduli_sistema'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    codice = Column(String, unique=True, nullable=False) # es. 'xbrl_import'
    nome = Column(String, nullable=False)                 # es. 'Importazione XBRL'

class ReportSistema(Base):
    __tablename__ = 'report_sistema'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    codice = Column(String, unique=True, nullable=False) # es. 'pdf_crisi'
    nome = Column(String, nullable=False)                 # es. 'Report Crisi d'Impresa'

class ProfiloUtente(Base):
    __tablename__ = 'profili_utente'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_profilo = Column(String, nullable=False) # es. 'Revisore Standard'
    
    # Relazioni Many-to-Many con i cataloghi staccati
    moduli = relationship("ModuloSistema", secondary=profilo_moduli)
    report = relationship("ReportSistema", secondary=profilo_report)
    utenti = relationship("Utente", back_populates="profilo")

class Utente(Base):
    __tablename__ = 'utenti'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    spazio_id = Column(Integer, ForeignKey('spazi.id', ondelete='CASCADE'), nullable=False)
    profilo_id = Column(Integer, ForeignKey('profili_utente.id', ondelete='SET NULL'), nullable=True)
    
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    ruolo_base = Column(Enum(RuoloBaseEnum), nullable=False)
    tentativi_falliti = Column(Integer, default=0)
    
    spazio = relationship("Spazio", back_populates="utenti")
    profilo = relationship("ProfiloUtente", back_populates="utenti")
