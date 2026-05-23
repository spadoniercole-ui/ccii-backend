from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) # es: "admin_spazio", "admin_azienda", "operatore", "consultatore"

    # Relazione: un ruolo può essere assegnato a molti utenti
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Chiave esterna per il collegamento al ruolo
    role_id = Column(Integer, ForeignKey("roles.id"))

    # Relazione: un utente ha un solo ruolo
    role = relationship("Role", back_populates="users")
