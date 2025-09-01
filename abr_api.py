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

app = FastAPI(
    title="ABR Wave Detection API",
    description="Detect ABR waves from signal and time CSVs.",
    version="1.0.0"
)

app.mount("/results", StaticFiles(directory="Results_for_waves"), name="results")


@app.post("/detect", summary="Detect ABR waves from signal/time CSVs")
async def detect_waves(
    signal_csv: UploadFile = File(..., description="CSV with amplitude traces"),
    time_csv: UploadFile = File(None, description="(Optional) CSV with time values")
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

