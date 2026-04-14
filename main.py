import os
import json
from fastapi import FastAPI, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import cloudinary
import cloudinary.uploader

# Assicurati che nel tuo file database.py ci siano i campi livello_vetro e colore_sfondo!
from database import SessionLocal, Artista, Link

app = FastAPI()

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configurazione Cloudinary
cloudinary.config( 
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'), 
  api_key = os.getenv('CLOUDINARY_API_KEY'), 
  api_secret = os.getenv('CLOUDINARY_API_SECRET') 
)

# Dipendenza per il Database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper per le icone dei social
# Helper per le icone dei social
def ottieni_classe_icona(piattaforma):
    if not piattaforma:
        return 'fas fa-link'
        
    p = str(piattaforma).strip().lower()
    
    if 'instagram' in p: return 'fab fa-instagram'
    if 'spotify' in p: return 'fab fa-spotify'
    if 'youtube' in p: return 'fab fa-youtube'
    if 'tiktok' in p: return 'fab fa-tiktok'
    if 'facebook' in p: return 'fab fa-facebook'
    if 'twitter' in p or 'x' == p: return 'fab fa-x-twitter' # 'x' esatta per evitare falsi positivi
    if 'apple' in p: return 'fab fa-apple'
    if 'amazon' in p: return 'fab fa-amazon'
    if 'soundcloud' in p: return 'fab fa-soundcloud'
    if 'twitch' in p: return 'fab fa-twitch'
    if 'linkedin' in p: return 'fab fa-linkedin'
    if 'sito' in p or 'web' in p: return 'fas fa-globe'
    
    return 'fas fa-link'

# 1. Rotta principale per visualizzare la pagina dell'artista
@app.get("/{artista_id:int}")
async def mostra_pagina(request: Request, artista_id: int, db: Session = Depends(get_db)):
    # Cerchiamo l'artista tramite l'ID univoco
    artista = db.query(Artista).filter(Artista.id == artista_id).first()
    
    if not artista:
        raise HTTPException(status_code=404, detail="Artista non trovato nel Database")

    return templates.TemplateResponse(
        request=request, 
        name="artista.html", 
        context={
            "artista": artista,
            "links": artista.links,
            "icona": ottieni_classe_icona,
            "url_profilo": artista.url_profilo,
            "url_sfondo": artista.url_sfondo
        }
    )

# 2. Rotta per la verifica della password dell'editor
@app.post("/{artista_id:int}/verifica-password")
async def verifica_password(artista_id: int, password: str = Form(...), db: Session = Depends(get_db)):
    artista = db.query(Artista).filter(Artista.id == artista_id).first()
    if not artista or artista.password_editor != password:
        raise HTTPException(status_code=403, detail="Accesso Negato")
    return {"status": "ok"}

# 3. Rotta per il salvataggio di tutte le modifiche
@app.post("/{artista_id:int}/salva")
async def salva_modifiche(
    artista_id: int, 
    password: str = Form(...), 
    nuovo_nome: str = Form(None), 
    links: str = Form(...),
    foto_profilo: UploadFile = File(None), 
    sfondo: UploadFile = File(None),
    rimuovi_profilo: str = Form("false"),
    rimuovi_sfondo: str = Form("false"),
    livello_vetro: str = Form("3"),          # Riceve il livello del vetro
    colore_sfondo: str = Form("#121212"),    # Riceve il colore in esadecimale (es. #ff0000)
    db: Session = Depends(get_db)
):
    # Verifica sicurezza
    artista = db.query(Artista).filter(Artista.id == artista_id).first()
    if not artista or artista.password_editor != password:
        raise HTTPException(status_code=403, detail="Accesso Negato")
        
    # Controllo omonimia (se ha cambiato nome)
    if nuovo_nome and nuovo_nome.strip() and nuovo_nome.lower() != artista.nome.lower():
        esistente = db.query(Artista).filter(Artista.nome.ilike(nuovo_nome.strip())).first()
        if esistente:
            raise HTTPException(status_code=400, detail="Questo nome d'arte è già preso!")
        artista.nome = nuovo_nome.strip()
        
    # Gestione rimozione vecchie immagini
    if rimuovi_profilo == "true":
        artista.url_profilo = None
    if rimuovi_sfondo == "true":
        artista.url_sfondo = None

    # Aggiornamento Stili (Vetro e Colore)
    artista.livello_vetro = livello_vetro
    artista.colore_sfondo = colore_sfondo

    # Ricostruzione Links
    dati_links = json.loads(links)
    db.query(Link).filter(Link.artista_id == artista.id).delete()
    for l in dati_links:
        db.add(Link(piattaforma=l['piattaforma'], url=l['url'], artista_id=artista.id))
        
    # Upload nuova Foto Profilo su Cloudinary
    if foto_profilo and foto_profilo.filename:
        risultato = cloudinary.uploader.upload(
            foto_profilo.file, 
            folder="hub_artisti", 
            public_id=f"artista_{artista.id}_profilo", 
            overwrite=True
        )
        artista.url_profilo = risultato.get("secure_url")
            
    # Upload nuovo Sfondo su Cloudinary
    if sfondo and sfondo.filename:
        risultato = cloudinary.uploader.upload(
            sfondo.file, 
            folder="hub_artisti", 
            public_id=f"artista_{artista.id}_sfondo", 
            overwrite=True
        )
        artista.url_sfondo = risultato.get("secure_url")
            
    # Salva tutto in modo permanente nel database
    db.commit()
    
    # Ritorna l'URL per forzare il refresh della pagina sul client
    return {"status": "successo", "nuovo_url": f"/{artista.id}"}
