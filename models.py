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

# ... (il resto delle classi rimane invariato)
