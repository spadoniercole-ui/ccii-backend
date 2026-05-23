from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"))
    
    # 🔐 Campo per la scadenza della password (gestito nel login)
    data_scadenza_password = Column(DateTime, nullable=True)

    role = relationship("Role", back_populates="users")

class Spazio(Base):
    __tablename__ = "spazi"

    id = Column(Integer, primary_key=True, index=True)
    licenza_id = Column(Integer, nullable=True)
    nome_spazio = Column(String, nullable=True)
    tipologia = Column(String, nullable=True) # 👈 Colonna per non stravolgere l'impostazione
    
    # 🗓️ Campo per la scadenza della licenza (gestito nel login)
    data_scadenza_licenza = Column(DateTime, nullable=True)
