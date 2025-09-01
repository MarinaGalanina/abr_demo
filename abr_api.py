# abr_api.py
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from typing import Optional
import pandas as pd
import os
import shutil
from uuid import uuid4
import os
os.makedirs("Results_for_waves", exist_ok=True)
from abr_analyzer import process_file

from fastapi.responses import HTMLResponse


    
app = FastAPI(
    title="ABR Wave Detection API",
    description="Dla każdej z pięciu fal (I–V) wyznaczane są charakterystyczne przedziały czasowe, w których może wystąpić dana fala. Algorytm przeszukuje sygnał w tych oknach, szukając lokalnych maksimów (szczytów) oraz odpowiadających im minimów w pobliżu. Latencja fali to czas wystąpienia szczytu, a amplituda to różnica między wartością szczytu i dołka. Jeżeli fala nie zostanie znaleziona przy wyższym progu, algorytm obniża próg amplitudy i próbuje ponownie. Wynikiem działania są wartości latencji i amplitudy dla każdej wykrytej fali, a także wykres sygnału z zaznaczonymi punktami detekcji.",
    version="1.0.0"
)

app.mount("/results", StaticFiles(directory="Results_for_waves"), name="results")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return """
    <html>
        <head>
            <title>ABR Wave Detection API</title>
        </head>
        <body>
            <h1>ABR Wave Detection API 🚀</h1>
            <p>This API detects ABR waves from CSV files with amplitude traces and time values.</p>
            <p>You can try it out via the <a href="/docs">interactive Swagger docs</a> or the <a href="/redoc">ReDoc docs</a>.</p>
        </body>
    </html>
    """


@app.post("/detect", summary="Dla każdej z pięciu fal (I–V) wyznaczane są charakterystyczne przedziały czasowe, w których może wystąpić dana fala. Algorytm przeszukuje sygnał w tych oknach, szukając lokalnych maksimów (szczytów) oraz odpowiadających im minimów w pobliżu. Latencja fali to czas wystąpienia szczytu, a amplituda to różnica między wartością szczytu i dołka. Jeżeli fala nie zostanie znaleziona przy wyższym progu, algorytm obniża próg amplitudy i próbuje ponownie. Wynikiem działania są wartości latencji i amplitudy dla każdej wykrytej fali, a także wykres sygnału z zaznaczonymi punktami detekcji.")
async def detect_waves(
    signal_csv: UploadFile = File(..., description="CSV with amplitude traces"),
    time_csv: Optional[UploadFile] = File(None, description="(Optional) CSV with time values")

):
    temp_dir = f"temp_data/{uuid4().hex}"
    os.makedirs(temp_dir, exist_ok=True)

    # zapisujemy plik sygnału
    signal_path = os.path.join(temp_dir, signal_csv.filename)
    with open(signal_path, "wb") as f:
        f.write(await signal_csv.read())

    if time_csv is not None:
        # użytkownik podał własny plik czasu
        time_path = os.path.join(temp_dir, time_csv.filename)
        with open(time_path, "wb") as f:
            f.write(await time_csv.read())
    else:
        # brak pliku → używamy domyślnego time_data.csv
        time_path = "time_data.csv"  # plik musi być w katalogu głównym projektu

    # przetwarzamy
    df = process_file(signal_path, time_path)

    # poprawka: tylko nazwy plików w URL
    if "plot_filename" in df.columns:
        df["plot_url"] = df["plot_filename"].apply(
            lambda fn: f"/results/{os.path.basename(fn)}" if pd.notna(fn) else None
        )
    if "raw_plot_filename" in df.columns:
        df["raw_plot_url"] = df["raw_plot_filename"].apply(
            lambda fn: f"/results/{os.path.basename(fn)}" if pd.notna(fn) else None
        )

    # sprzątamy temp
    shutil.rmtree(temp_dir, ignore_errors=True)

    return df.to_dict(orient="records")


@app.on_event("shutdown")
def cleanup_temp():
    shutil.rmtree("temp_data", ignore_errors=True)





