import os
import pandas as pd
from database import SessionLocal, Artista, Link, Base, engine

def esegui_migrazione():
    file_input = 'risultati_social_artisti_prova.xlsx'
    
    if not os.path.exists(file_input):
        print(f"[ERRORE] Il file '{file_input}' non si trova nella cartella!")
        return

    print("--- INIZIO MIGRAZIONE DATI DA EXCEL A SQLITE ---")
    
    # Assicuriamoci che le tabelle esistano
    Base.metadata.create_all(bind=engine)
    
    # Apriamo la sessione col database
    db = SessionLocal()
    
    try:
        xls = pd.ExcelFile(file_input, engine='openpyxl')
        lista_artisti = xls.sheet_names
        
        artisti_aggiunti = 0
        link_aggiunti = 0

        for nome_foglio in lista_artisti:
            nome_artista_str = str(nome_foglio).strip()
            df = pd.read_excel(xls, sheet_name=nome_foglio)
            
            # Recuperiamo la password (se per qualche motivo manca, mettiamo un default)
            pwd_artista = "AQHS-0000"
            if 'Password_Editor' in df.columns and not pd.isna(df['Password_Editor'].iloc[0]):
                pwd_artista = str(df['Password_Editor'].iloc[0]).strip()
                
            # 1. Controlliamo se l'artista esiste già nel DB per evitare duplicati
            artista_db = db.query(Artista).filter(Artista.nome.ilike(nome_artista_str)).first()
            
            if not artista_db:
                # Creiamo l'artista
                artista_db = Artista(nome=nome_artista_str, password_editor=pwd_artista)
                db.add(artista_db)
                db.commit() # Salviamo subito per generare l'ID
                db.refresh(artista_db)
                artisti_aggiunti += 1
                print(f" [+] Creato artista: {nome_artista_str} (Password: {pwd_artista})")
            else:
                print(f" [!] Artista {nome_artista_str} già presente nel DB, aggiorno i link...")
                # Puliamo i vecchi link per rimetterli freschi dall'Excel
                db.query(Link).filter(Link.artista_id == artista_db.id).delete()
            
            # 2. Inseriamo i link
            for _, row in df.iterrows():
                piattaforma = str(row['Piattaforma']).strip()
                link = str(row['Link Corretto']).strip()
                
                if link and link != "nan" and link != "Non trovato" and link != "Non fornito" and link.startswith("http"):
                    nuovo_link = Link(piattaforma=piattaforma, url=link, artista_id=artista_db.id)
                    db.add(nuovo_link)
                    link_aggiunti += 1
                    
            db.commit() # Salviamo tutti i link di questo artista
            
        print(f"\n[SUCCESSO] Migrazione completata!")
        print(f"-> Artisti nel DB: {artisti_aggiunti}")
        print(f"-> Link importati: {link_aggiunti}")

    except Exception as e:
        print(f"[ERRORE CRITICO] Qualcosa è andato storto: {e}")
    finally:
        db.close() # Chiudiamo la connessione pulitamente

if __name__ == "__main__":
    esegui_migrazione()