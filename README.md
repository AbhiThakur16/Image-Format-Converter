AI Image Studio

AI Image Studio is a Python-based image conversion, analysis, editing, and export application built with Streamlit.

The project started as an image format converter and was expanded into a larger image-processing studio with multi-format input, editable raster layers, OCR, object detection, segmentation, project recovery, diagnostics, and professional export controls.

Features

Multi-Format Input

Supported input formats include:

JPG / JPEG

PNG

WEBP

TIFF / TIF

BMP

PDF

SVG

HEIC / HEIF

PDF files can be opened as:

Single Page

All Pages for batch export

SVG files are rasterized for editing.

HEIC / HEIF images are decoded using pillow-heif.

Image Analysis

The application can display:

Image width and height

Total pixel count

Transparency information

Dominant colors

Edge information

Basic shape analysis

Some analysis features are heuristic/rules-based rather than deep-learning models.

Editable Layer System

AI Image Studio can create several types of editable raster layers:

Color Layers

Semantic Layers

Object Layers

Segmentation Layers

Smart Color Layers

Text Detection Layers

OCR Layers

Layer controls include:

Rename

Show / Hide

Opacity

Move Up

Move Down

Duplicate

Delete

Rotate Left

Rotate Right

Flip Horizontal

Flip Vertical

Move X / Y

Scale

Reset Transform

Layer Lock

Undo

Redo

The generated layers are raster pixel layers. They are not original Photoshop or CorelDRAW source layers.

Object Recognition

Object recognition uses a pretrained TorchVision object-detection model.

It can detect common object categories and create separate raster layers for detected objects.

Detection quality depends on:

Image quality

Object size

Model confidence threshold

Whether the object belongs to a supported model category

Segmentation

Object segmentation combines object detection with image segmentation techniques to create approximate object masks.

The application also includes background removal.

Segmentation is approximate and should not be treated as pixel-perfect professional masking.

OCR

OCR is powered by EasyOCR.

Features include:

Text-region detection

OCR text extraction

Confidence values

OCR-based raster layers

Combined extracted text output

OCR accuracy depends on image resolution, language, font, contrast, rotation, and image quality.

Smart Color Editing

Available color tools include:

Replace selected color

Remove selected color

Extract selected color as a layer

Merge colors

Preserve basic shading where supported

Professional Output Settings

The export system supports:

Original Size

Target Total Pixels

Custom Width / Height

Aspect-ratio locking

DPI selection

RGB

CMYK

Grayscale

Fit

Fill & Crop

Stretch

JPEG / WebP quality

PNG compression

TIFF compression

Supported export formats:

PNG

JPEG

WEBP

TIFF

BMP

PDF

PSD (Flattened)

PSD (Layered)

Batch results are provided as individual downloads.

The application intentionally does not create a ZIP file for normal batch downloads.

Layered PSD Export

The Layered PSD exporter can create a PSD containing multiple editable raster pixel layers and layer groups.

Important limitations:

Text layers are not native editable Photoshop text.

Detected shapes are not native vector shape layers.

Exported layers are raster pixel layers.

PSD output is currently RGB.

Original flattened images cannot be used to recover their original editor/source layers.

PDF Support

PDF support is provided through PyMuPDF.

Features include:

Page count detection

Single-page rendering

All-pages rendering

Configurable render DPI

Individual page export

For All Pages mode, Page 1 is used as the editor preview.

Current PDF export is image-based. It does not recreate original PDF vectors, fonts, or editable document structure.

Project Files

AI Image Studio supports its own editable project format:

.aistudio

A project can store:

Original image

Edited image

Layer groups

Layer settings

Export settings

Project metadata

.aistudio is an AI Image Studio project container and is not a replacement for PSD/CDR source files.

Undo / Redo

The layer editor includes history support for operations such as:

Duplicate

Delete

Layer order changes

Rotate

Flip

Move

Scale

Reset Transform

Rename

Visibility

Opacity

Auto-Recovery

Local project recovery is supported through a .recovery directory.

The application can:

Detect unsaved changes

Save recovery data

Restore a recoverable session

Discard recovery data

Local recovery is intended mainly for desktop/local execution.

On Streamlit Cloud, local server storage should not be considered permanent storage.

Diagnostics

Runtime errors can be recorded in:

logs/ai_image_studio_errors.jsonl

The diagnostics system can show:

Application status

Recovery status

Recent error count

Recent errors

Error type

Error message

Operation in which the error occurred

Technical details can be logged without filling the main UI with long tracebacks.

Installation

1. Clone Repository

git clone https://github.com/AbhiThakur16/Image-Format-Converter.git
cd Image-Format-Converter

2. Create Virtual Environment

python -m venv venv

Activate it in PowerShell:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1

3. Install Web / Streamlit Dependencies

pip install -r requirements.txt

Check dependencies:

pip check

4. Run Streamlit Application

streamlit run streamlit_app.py

Streamlit will display a local URL such as:

http://localhost:8501

Production Requirements

requirements.txt

streamlit
Pillow
numpy
opencv-python-headless
easyocr
torch
torchvision
psd-tools
PyMuPDF
pillow-heif

Desktop Requirements

For the Windows desktop build:

pip install -r requirements-desktop.txt

requirements-desktop.txt includes the desktop/build dependencies such as:

customtkinter

pyinstaller

Windows Desktop Application

The project also includes a Windows desktop version.

A PyInstaller build can be created with:

pyinstaller --noconfirm --onefile --windowed --collect-all customtkinter --collect-all psd_tools --name ImageFormatConverter main.py

The generated executable is normally placed in:

dist\ImageFormatConverter.exe

Basic Testing

Run Python syntax checks:

Get-ChildItem -Path . -Filter *.py -File | ForEach-Object {
    python -m py_compile $_.FullName
}

Check dependency consistency:

pip check

Run the Streamlit application:

streamlit run streamlit_app.py

Suggested Test Checklist

Before a release, test:

JPG / PNG upload

PDF Single Page

PDF All Pages

SVG input

HEIC / HEIF input

Color-layer extraction

Semantic layers

Object detection

Segmentation

Background removal

OCR

Color editing

Layer Duplicate / Delete / Reorder

Rotate / Flip / Move / Scale

Undo / Redo

Layer Lock

Reset Transform

.aistudio Save / Open

Auto-Recovery

Diagnostics

PNG export

JPEG export

TIFF export

BMP export

PDF export

Flattened PSD export

Layered PSD export

Important Technical Limitations

AI Image Studio is an image-processing project and does not claim to recreate the complete functionality of Adobe Photoshop or CorelDRAW.

Current limitations include:

Flattened raster images cannot reveal their original source layers.

Semantic separation is approximate.

Object recognition is limited by the pretrained model categories.

Segmentation is approximate.

OCR accuracy varies with image quality.

Current PSD text is not native Photoshop editable text.

Current PSD shapes are not native vector shape layers.

SVG input is rasterized.

PDF pages are rasterized for editing.

CMYK conversion currently uses basic Pillow conversion rather than a printer-specific ICC workflow.

True professional ICC color management is not yet implemented.

True native 16-bit / 32-bit editing is not implemented.

PDF/X export is not implemented.

Vector-preserving output is not implemented.

Cloud deployment may require significant memory for Torch/EasyOCR and high-resolution PDFs.

Technology Stack

Python

Streamlit

Pillow

NumPy

OpenCV

EasyOCR

PyTorch

TorchVision

psd-tools

PyMuPDF

pillow-heif

CustomTkinter

PyInstaller

Repository

GitHub:

https://github.com/AbhiThakur16/Image-Format-Converter

Streamlit Application

Deployed application:

https://abhi-image-format-converter.streamlit.app

Project Status

The project currently includes:

Multi-format image/document input

Image analysis

Editable raster layers

Object recognition

Segmentation

OCR

Smart color tools

Professional export controls

Flattened PSD export

Layered PSD export

Project save/load

Undo/Redo

Layer lock

Reset transform

Auto-recovery

Diagnostics

Web application

Windows desktop build workflow

Author

Abhi

B.Tech Computer Science Engineering — Data Science