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

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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

# Rotta principale aggiornata per usare l'ID intero
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

# Verifica password ancorata all'ID
@app.post("/{artista_id:int}/verifica-password")
async def verifica_password(artista_id: int, password: str = Form(...), db: Session = Depends(get_db)):
    artista = db.query(Artista).filter(Artista.id == artista_id).first()
    if not artista or artista.password_editor != password:
        raise HTTPException(status_code=403, detail="Accesso Negato")
    return {"status": "ok"}

# Salvataggio ancorato all'ID
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
    livello_vetro: str = Form("3"),  # <--- AGGIUNTO QUI
    db: Session = Depends(get_db)
):
    artista = db.query(Artista).filter(Artista.id == artista_id).first()
    if not artista or artista.password_editor != password:
        raise HTTPException(status_code=403, detail="Accesso Negato")
        
    if nuovo_nome and nuovo_nome.strip() and nuovo_nome.lower() != artista.nome.lower():
        esistente = db.query(Artista).filter(Artista.nome.ilike(nuovo_nome.strip())).first()
        if esistente:
            raise HTTPException(status_code=400, detail="Questo nome d'arte è già preso!")
        artista.nome = nuovo_nome.strip()
        
    if rimuovi_profilo == "true":
        artista.url_profilo = None
    if rimuovi_sfondo == "true":
        artista.url_sfondo = None

    # --- AGGIORNA IL LIVELLO VETRO NEL DB ---
    artista.livello_vetro = livello_vetro

    dati_links = json.loads(links)
    db.query(Link).filter(Link.artista_id == artista.id).delete()
    for l in dati_links:
        db.add(Link(piattaforma=l['piattaforma'], url=l['url'], artista_id=artista.id))
        
    if foto_profilo and foto_profilo.filename:
        risultato = cloudinary.uploader.upload(foto_profilo.file, folder="hub_artisti", public_id=f"artista_{artista.id}_profilo", overwrite=True)
        artista.url_profilo = risultato.get("secure_url")
            
    if sfondo and sfondo.filename:
        risultato = cloudinary.uploader.upload(sfondo.file, folder="hub_artisti", public_id=f"artista_{artista.id}_sfondo", overwrite=True)
        artista.url_sfondo = risultato.get("secure_url")
            
    db.commit()
    
    # Ricarica la pagina basandosi sull'ID
    return {"status": "successo", "nuovo_url": f"/{artista.id}"}
