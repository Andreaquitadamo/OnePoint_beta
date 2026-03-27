import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Pesca l'URL di Supabase dalle impostazioni segrete del server
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hub_artisti.db")

# Fix automatico: SQLAlchemy vuole "postgresql://" invece di "postgres://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Motore di connessione
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Artista(Base):
    __tablename__ = "artisti"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    password_editor = Column(String)
    
    # NUOVE COLONNE PER IL CLOUD
    url_profilo = Column(String, nullable=True) 
    url_sfondo = Column(String, nullable=True)  
    
    links = relationship("Link", back_populates="artista")

class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True, index=True)
    piattaforma = Column(String)
    url = Column(String)
    artista_id = Column(Integer, ForeignKey("artisti.id"))
    artista = relationship("Artista", back_populates="links")

Base.metadata.create_all(bind=engine)
