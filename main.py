from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from database import Base

# --- MODELLI ESISTENTI ---
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    users = relationship("User", back_populates="role")

class TipoSpazio(Base):
    __tablename__ = "tipi_spazio"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    spazi = relationship("Spazio", back_populates="tipo_spazio")

class Spazio(Base):
    __tablename__ = "spazi"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    data_scadenza_licenza = Column(DateTime, nullable=True)
    licenza_id = Column(Integer, ForeignKey("licenze.id"), nullable=True)
    tipo_spazio_id = Column(Integer, ForeignKey("tipi_spazio.id"), nullable=True)
    users = relationship("User", back_populates="spazio")
    tipo_spazio = relationship("TipoSpazio", back_populates="spazi")
    licenza = relationship("Licenza", back_populates="spazi")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    role_id = Column(Integer, ForeignKey("roles.id"))
    spazio_id = Column(Integer, ForeignKey("spazi.id"))
    role = relationship("Role", back_populates="users")
    spazio = relationship("Spazio", back_populates="users")

class Licenza(Base):
    __tablename__ = "licenze"
    id = Column(Integer, primary_key=True, index=True)
    intestatario = Column(String, nullable=False)
    max_spazi = Column(Integer, default=1)
    max_utenti_totali = Column(Integer, default=1)
    max_aziende_totali = Column(Integer, default=1)
    data_scadenza = Column(DateTime, nullable=False)
    spazi = relationship("Spazio", back_populates="licenza")

# --- NUOVI MODELLI PER MODULO 8 (XBRL) ---

class XbrlStaging(Base):
    __tablename__ = "xbrl_staging"
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    raw_content = Column(Text, nullable=False) # Il file salvato come testo
    status = Column(String, default="PENDING_VALIDATION") # PENDING_VALIDATION, VALIDATED, ANALYZED
    data_importazione = Column(DateTime, default=func.now())

class MappaturaVariabili(Base):
    __tablename__ = "mappatura_variabili"
    id = Column(Integer, primary_key=True)
    tag_xbrl_grezzo = Column(String, unique=True, nullable=False) # Es: "itcc-ci:PatrimonioNetto"
    tag_sistema_target = Column(String, nullable=False)         # Es: "patrimonio_netto"
    data_creazione = Column(DateTime, default=func.now())
