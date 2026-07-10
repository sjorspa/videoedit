# SuperBasic Video Editor

Een eenvoudige video editor met een GUI die werkt op Windows.

## Features

- **Video Upload**: Ondersteunt MP4, AVI, MOV, MKV, WMV, FLV bestanden
- **Play Controls**: Play, Pause, Stop en frame-scrubbing
- **Timeline Selectie**: Twee sliders om het begin- en eindpunt van de video te selecteren
- **Crop Box**: Een interactieve selectie box die je kunt vergroten, verkleinen, verschuiven
  - Sleep de **hoeken** om te resizen
  - Sleep de **zijkanten** om de breedte/hoogte aan te passen
  - Sleep de **binnenkant** om de box te verplaatsen
- **Export**: Exporteer de geselecteerde timeframe met de crop instellingen
- **Geen audio**: Audio wordt altijd genegeerd bij de output
- **Hoogwaardige MP4**: Gebruikt libx264 codec met CRF 18 voor maximale kwaliteit

## Vereisten

- **Python 3.8+**
- **FFmpeg** (moet geïnstalleerd zijn en in PATH staan)
  - Download van: https://ffmpeg.org/download.html
  - Op Windows: voeg `ffmpeg\bin` toe aan je PATH environment variable

## Installatie

```bash
pip install -r requirements.txt
```

## Gebruik

```bash
python main.py
```

## Hoe te gebruiken

1. **Upload een video** via de "Upload Video" button
2. **Selecteer een timeframe** met de twee sliders (Start en End)
3. **Selecteer een crop gebied** door te slepen in de preview:
   - Sleep hoekpunten om te resizen
   - Sleep zijkanten om breedte/hoogte aan te passen
   - Sleep de binnenkant om te verplaatsen
4. **Play/Pause/Stop** de video om het resultaat te bekijken
5. **Exporteer** via de "Export Video" button

## Export instellingen

- **Codec**: libx264 (H.264)
- **Kwaliteit**: CRF 18 (hoogwaardig)
- **Preset**: medium
- **Pixel format**: yuv420p (brede compatibiliteit)
- **Audio**: uitgeschakeld

## Bestandsstructuur

```
video_editor/
├── main.py          # Hoofd applicatie
├── requirements.txt # Python dependencies
└── README.md        # Dit bestand
```
