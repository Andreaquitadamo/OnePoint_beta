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

# Montiamo la cartella static (se ti servirà in futuro)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Inizializzazione Cloudinary con le chiavi segrete
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

# Funzione per assegnare l'icona giusta in base al nome della piattaforma
def ottieni_classe_icona(piattaforma):
    p = str(piattaforma).strip().lower()
    mappa_icone = {
        'instagram': 'fab fa-instagram', 'spotify': 'fab fa-spotify', 'youtube': 'fab fa-youtube',
        'tiktok': 'fab fa-tiktok', 'facebook': 'fab fa-facebook', 'twitter': 'fab fa-twitter',
        'x': 'fab fa-x-twitter', 'apple music': 'fab fa-itunes-note', 'amazon music': 'fab fa-amazon',
        'soundcloud': 'fab fa-soundcloud', 'twitch': 'fab fa-twitch', 'sito web': 'fas fa-globe',
        'website': 'fas fa-globe', 'linkedin': 'fab fa-linkedin'
    }
    return mappa_icone.get(p, 'fas fa-link') # Icona di default se non riconosce la piattaforma

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
            "url_profilo": artista.url_profilo,
            "url_sfondo": artista.url_sfondo
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
    nome_artista: str, 
    password: str = Form(...), 
    nuovo_nome: str = Form(None), 
    links: str = Form(...),
    foto_profilo: UploadFile = File(None), 
    sfondo: UploadFile = File(None),
    rimuovi_profilo: str = Form("false"),  # Sensore per rimozione foto profilo
    rimuovi_sfondo: str = Form("false"),   # Sensore per rimozione sfondo
    db: Session = Depends(get_db)
):
    # 1. Verifica Sicurezza
    artista = db.query(Artista).filter(Artista.nome.ilike(nome_artista)).first()
    if not artista or artista.password_editor != password:
        raise HTTPException(status_code=403, detail="Accesso Negato")
        
    # 2. Logica Cambio Nome d'Arte
    if nuovo_nome and nuovo_nome.strip() and nuovo_nome.lower() != nome_artista.lower():
        esistente = db.query(Artista).filter(Artista.nome.ilike(nuovo_nome.strip())).first()
        if esistente:
            raise HTTPException(status_code=400, detail="Questo nome d'arte è già preso!")
        artista.nome = nuovo_nome.strip()
        
    # 3. Logica Rimozione Immagini
    if rimuovi_profilo == "true":
        artista.url_profilo = None
    if rimuovi_sfondo == "true":
        artista.url_sfondo = None

    # 4. Aggiornamento dei Link
    dati_links = json.loads(links)
    db.query(Link).filter(Link.artista_id == artista.id).delete()
    for l in dati_links:
        db.add(Link(piattaforma=l['piattaforma'], url=l['url'], artista_id=artista.id))
        
    # 5. Caricamento Nuove Immagini su Cloudinary (se caricate)
    if foto_profilo and foto_profilo.filename:
        risultato = cloudinary.uploader.upload(foto_profilo.file, folder="hub_artisti", public_id=f"artista_{artista.id}_profilo", overwrite=True)
        artista.url_profilo = risultato.get("secure_url")
            
    if sfondo and sfondo.filename:
        risultato = cloudinary.uploader.upload(sfondo.file, folder="hub_artisti", public_id=f"artista_{artista.id}_sfondo", overwrite=True)
        artista.url_sfondo = risultato.get("secure_url")
            
    # Salvataggio finale sul Database
    db.commit()
    
    # Restituiamo il nuovo URL per far ricaricare la pagina all'utente
    return {"status": "successo", "nuovo_url": f"/{artista.nome}"}
