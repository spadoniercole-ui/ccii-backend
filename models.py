from sqlalchemy import Text # Assicurati che Text sia importato in cima se non c'è
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base

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
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # Uniformato a hashed_password per evitare NameError o conflitti logici
    hashed_password = Column(String, nullable=False) 
    is_superuser = Column(Boolean, default=False)
    data_scadenza_password = Column(DateTime, nullable=True)
    
    role_id = Column(Integer, ForeignKey("roles.id"))
    spazio_id = Column(Integer, ForeignKey("spazi.id"))
    
    role = relationship("Role", back_populates="users")
    spazio = relationship("Spazio", back_populates="users")

class Configurazione(Base):
    __tablename__ = "configurazioni"
    id = Column(Integer, primary_key=True)
    chiave = Column(String, nullable=False)
    valore = Column(String, nullable=False)
    scope_type = Column(String)
    scope_id = Column(Integer, nullable=True)

class Profilo(Base):
    __tablename__ = "profili"
    id = Column(Integer, primary_key=True)
    nome = Column(String, unique=True)
    moduli = relationship("ProfiloModulo", back_populates="profilo")

class ProfiloModulo(Base):
    __tablename__ = "profilo_modulo"
    id = Column(Integer, primary_key=True)
    profilo_id = Column(Integer, ForeignKey("profili.id"))
    data_inizio = Column(DateTime, default=func.now())
    data_fine = Column(DateTime, nullable=True)
    versione = Column(Integer, default=1)
    is_old = Column(Integer, default=0)
    profilo = relationship("Profilo", back_populates="moduli")

class Licenza(Base):
    __tablename__ = "licenze"
    id = Column(Integer, primary_key=True, index=True)
    intestatario = Column(String, nullable=False)
    max_spazi = Column(Integer, default=1)
    max_utenti_totali = Column(Integer, default=1)
    max_aziende_totali = Column(Integer, default=1)
    data_scadenza = Column(Date, nullable=False)
    
    # Correzione Mapper: Relazione reciproca con Spazio
    spazi = relationship("Spazio", back_populates="licenza")

class XbrlStaging(Base):
    __tablename__ = "xbrl_staging"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    raw_content = Column(Text, nullable=False)
    status = Column(String, default="PENDING_VALIDATION")  # Esito (VALIDATED, INVALID, ecc.)
    anno_riferimento = Column(Integer, nullable=True)      # <-- FONDAMENTALE PER LA GRIGLIA
    azienda = Column(String, nullable=True)               # <-- NUOVO: Mostra il nome in griglia
    data_caricamento = Column(DateTime, default=func.now()) # Sequenza cronologica
