import os
import json
import shutil
from fastapi import FastAPI, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import SessionLocal, Artista, Link

# 1. Creiamo l'app
app = FastAPI()

# 2. Ci assicuriamo che la cartella "static" esista FISICAMENTE sul disco
os.makedirs("static", exist_ok=True)

# 3. Montiamo SUBITO la cartella "static" dicendo a FastAPI come chiamarla
app.mount("/static", StaticFiles(directory="static"), name="static")

# 4. Impostiamo la cartella dei templates
templates = Jinja2Templates(directory="templates")

# --- FINE CONFIGURAZIONE INIZIALE ---

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
    
    # Controlliamo se l'artista ha caricato immagini
    percorso_profilo = f"static/{artista.nome}_profilo.png"
    percorso_sfondo = f"static/{artista.nome}_sfondo.png"
    
    url_profilo = f"/static/{artista.nome}_profilo.png" if os.path.exists(percorso_profilo) else None
    url_sfondo = f"/static/{artista.nome}_sfondo.png" if os.path.exists(percorso_sfondo) else None

    return templates.TemplateResponse(
        request=request, 
        name="artista.html", 
        context={
            "artista": artista,
            "links": artista.links,
            "icona": ottieni_classe_icona,
            "url_profilo": url_profilo,
            "url_sfondo": url_sfondo
        }
    )

# --- NUOVO ENDPOINT: CONTROLLO BLINDATO DELLA PASSWORD ---
@app.post("/{nome_artista}/verifica-password")
async def verifica_password(
    nome_artista: str, 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    artista = db.query(Artista).filter(Artista.nome.ilike(nome_artista)).first()
    if not artista:
        raise HTTPException(status_code=404, detail="Artista non trovato")
        
    if artista.password_editor != password:
        raise HTTPException(status_code=403, detail="Password errata.")
        
    return {"status": "ok"}
# ---------------------------------------------------------

@app.post("/{nome_artista}/salva")
async def salva_modifiche(
    nome_artista: str, 
    password: str = Form(...),
    links: str = Form(...),
    foto_profilo: UploadFile = File(None),
    sfondo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    artista = db.query(Artista).filter(Artista.nome.ilike(nome_artista)).first()
    if not artista:
        raise HTTPException(status_code=404, detail="Artista non trovato")
        
    # Doppio controllo di sicurezza in fase di salvataggio
    if artista.password_editor != password:
        raise HTTPException(status_code=403, detail="Password errata.")
        
    try:
        dati_links = json.loads(links)
    except:
        raise HTTPException(status_code=400, detail="Formato link non valido")
        
    db.query(Link).filter(Link.artista_id == artista.id).delete()
    for l in dati_links:
        nuovo_link = Link(piattaforma=l['piattaforma'], url=l['url'], artista_id=artista.id)
        db.add(nuovo_link)
        
    if foto_profilo and foto_profilo.filename:
        with open(f"static/{artista.nome}_profilo.png", "wb") as buffer:
            shutil.copyfileobj(foto_profilo.file, buffer)
            
    if sfondo and sfondo.filename:
        with open(f"static/{artista.nome}_sfondo.png", "wb") as buffer:
            shutil.copyfileobj(sfondo.file, buffer)
            
    db.commit()
    return {"status": "successo"}
