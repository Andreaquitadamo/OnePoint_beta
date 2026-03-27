from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Configurazione del database SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./hub_artisti.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Tabella degli Artisti
class Artista(Base):
    __tablename__ = "artisti"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    password_editor = Column(String)
    # Collegamento ai link (se eliminiamo l'artista, si eliminano i suoi link)
    links = relationship("Link", back_populates="proprietario", cascade="all, delete-orphan")

# Tabella dei Link Social
class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True, index=True)
    piattaforma = Column(String)
    url = Column(String)
    artista_id = Column(Integer, ForeignKey("artisti.id"))
    proprietario = relationship("Artista", back_populates="links")

# Questo comando crea fisicamente il file e le tabelle se non esistono
Base.metadata.create_all(bind=engine)