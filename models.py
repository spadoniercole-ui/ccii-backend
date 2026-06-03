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
    # Relazione opzionale per vedere tutti gli spazi di un tipo
    spazi = relationship("Spazio", back_populates="tipo_spazio")

class Spazio(Base):
    __tablename__ = "spazi"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    data_scadenza_licenza = Column(DateTime, nullable=True)

class XbrlStaging(Base):
    __tablename__ = "xbrl_staging"
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    raw_content = Column(LargeBinary)
    status = Column(String) # 'STAGING', 'VALIDATO', 'RICLASSIFICATO'
    data_caricamento = Column(DateTime)

class MappaturaVariabili(Base):
    __tablename__ = "mappatura_variabili"
    id = Column(Integer, primary_key=True)
    tag_xbrl_grezzo = Column(String)
    tag_sistema_target = Column(String)

class BilancioRiclassificato(Base):
    __tablename__ = "bilancio_riclassificato"
    id = Column(Integer, primary_key=True)
    staging_id = Column(Integer) # FK verso XbrlStaging
    valore = Column(Float)
    variabile_sistema = Column(String)
    
    # Chiavi esterne (spostate qui da Licenza)
    licenza_id = Column(Integer, ForeignKey("licenze.id"), nullable=True)
    tipo_spazio_id = Column(Integer, ForeignKey("tipi_spazio.id"), nullable=True)
    
    # Relazioni
    users = relationship("User", back_populates="spazio")
    tipo_spazio = relationship("TipoSpazio", back_populates="spazi")
    licenza = relationship("Licenza", back_populates="spazi")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    is_superuser = Column(Boolean, default=False)
    data_scadenza_password = Column(DateTime, nullable=True)
    
    role_id = Column(Integer, ForeignKey("roles.id"))
    spazio_id = Column(Integer, ForeignKey("spazi.id"))
    
    # Relationships
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
    
    # Relazione inversa
    spazi = relationship("Spazio", back_populates="licenza")
