# SuperBasic Video Editor

A simple video editor with a GUI that runs on Windows.

## Features

- **Video Upload**: Supports MP4, AVI, MOV, MKV, WMV, FLV files
- **Play Controls**: Play, Pause, Stop and frame-scrubbing
- **Timeline Selection**: Two sliders to select the start and end points of the video
- **Crop Box**: An interactive selection box that can be resized, shrunk, and moved
  - Drag **corners** to resize
  - Drag **edges** to adjust width/height
  - Drag the **inside** to move the box
- **Export**: Export the selected timeframe with crop settings
- **No audio**: Audio is always ignored in the output
- **High-quality MP4**: Uses libx264 codec with CRF 18 for maximum quality
- **Export FPS**: Choose export frame rate (Original, 24, 30, 60, 120, 240)
- **Resolution Display**: Shows the loaded video resolution
- **Fixed Duration**: Lock end marker to start + N frames
- **Crop Presets**: Quick aspect ratio/size presets

## Requirements

- **Python 3.8+**
- **FFmpeg** (must be installed and in PATH)
  - Download from: https://ffmpeg.org/download.html
  - On Windows: add `ffmpeg\bin` to your PATH environment variable

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## How to Use

1. **Upload a video** using the "Upload Video" button
2. **Select a timeframe** with the two sliders (Start and End)
3. **Select a crop area** by dragging in the preview:
   - Drag corner handles to resize
   - Drag edges to adjust width/height
   - Drag the inside to move
4. **Play/Pause/Stop** the video to preview
5. **Export** via the "Export Video" button

## Export Settings

- **Codec**: libx264 (H.264)
- **Quality**: CRF 18 (high quality)
- **Preset**: medium
- **Pixel format**: yuv420p (wide compatibility)
- **Audio**: disabled
- **Frame rate**: User-selectable (Original, 24, 30, 60, 120, 240)

## File Structure

```
video_editor/
├── main.py          # Main application
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## License

This project is licensed under the [MIT License](LICENSE).
