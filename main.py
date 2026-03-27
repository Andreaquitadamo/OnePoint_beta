import os
import json
from fastapi import FastAPI, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import cloudinary
import cloudinary.uploader

from database import SessionLocal, Artista, Link

app = FastAPI()

# Montiamo la cartella static per sicurezza (ci servirà solo per il logo_creatore.png)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Inizializzazione Cloudinary con variabili d'ambiente
cloudinary.config( 
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'), 
  api_key = os.getenv('CLOUDINARY_API_KEY'), 
  api_secret = os.getenv('CLOUDINARY_API_SECRET') 
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ottieni_classe_icona(piattaforma):
    p = str(piattaforma).strip().lower()
    mappa_icone = {
        'instagram': 'fab fa-instagram', 'spotify': 'fab fa-spotify', 'youtube': 'fab fa-youtube',
        'tiktok': 'fab fa-tiktok', 'facebook': 'fab fa-facebook', 'twitter': 'fab fa-twitter',
        'x': 'fab fa-x-twitter', 'apple music': 'fab fa-itunes-note', 'amazon music': 'fab fa-amazon',
        'soundcloud': 'fab fa-soundcloud', 'twitch': 'fab fa-twitch', 'sito web': 'fas fa-globe',
        'website': 'fas fa-globe', 'linkedin': 'fab fa-linkedin'
    }
    return mappa_icone.get(p, 'fas fa-link')

@app.get("/{nome_artista}")
async def mostra_pagina(request: Request, nome_artista: str, db: Session = Depends(get_db)):
    artista = db.query(Artista).filter(Artista.nome.ilike(nome_artista)).first()
    
    if not artista:
        raise HTTPException(status_code=404, detail="Artista non trovato nel Database")

    return templates.TemplateResponse(
        request=request, 
        name="artista.html", 
        context={
            "artista": artista,
            "links": artista.links,
            "icona": ottieni_classe_icona,
            "url_profilo": artista.url_profilo, # Ora lo prende dritto dal database!
            "url_sfondo": artista.url_sfondo    # Ora lo prende dritto dal database!
        }
    )

@app.post("/{nome_artista}/verifica-password")
async def verifica_password(nome_artista: str, password: str = Form(...), db: Session = Depends(get_db)):
    artista = db.query(Artista).filter(Artista.nome.ilike(nome_artista)).first()
    if not artista or artista.password_editor != password:
        raise HTTPException(status_code=403, detail="Accesso Negato")
    return {"status": "ok"}

@app.post("/{nome_artista}/salva")
async def salva_modifiche(
    nome_artista: str, password: str = Form(...), links: str = Form(...),
    foto_profilo: UploadFile = File(None), sfondo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    artista = db.query(Artista).filter(Artista.nome.ilike(nome_artista)).first()
    if not artista or artista.password_editor != password:
        raise HTTPException(status_code=403, detail="Accesso Negato")
        
    dati_links = json.loads(links)
        
    db.query(Link).filter(Link.artista_id == artista.id).delete()
    for l in dati_links:
        db.add(Link(piattaforma=l['piattaforma'], url=l['url'], artista_id=artista.id))
        
    # --- LA MAGIA DEL CLOUD ---
    if foto_profilo and foto_profilo.filename:
        risultato = cloudinary.uploader.upload(foto_profilo.file, folder="hub_artisti", public_id=f"{artista.nome}_profilo", overwrite=True)
        artista.url_profilo = risultato.get("secure_url") # Salva il link di Cloudinary nel DB
            
    if sfondo and sfondo.filename:
        risultato = cloudinary.uploader.upload(sfondo.file, folder="hub_artisti", public_id=f"{artista.nome}_sfondo", overwrite=True)
        artista.url_sfondo = risultato.get("secure_url")
            
    db.commit()
    return {"status": "successo"}
