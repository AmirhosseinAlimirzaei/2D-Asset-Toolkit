# ⚒️ 2D Asset Toolkit

<div align="center">

![Version](https://img.shields.io/badge/version-v1.0.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.8+-green?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-orange?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-Windows%20|%20macOS%20|%20Linux-lightgrey?style=for-the-badge)
![Studio](https://img.shields.io/badge/LilyxGames-Studio-ff8c00?style=for-the-badge)

**A powerful all-in-one desktop toolkit for 2D game artists and developers.**

Browse, trim, resize, and remove backgrounds from your sprites and assets — all in a single dark-themed app.

[📖 Handbook & Docs](https://YOUR_USERNAME.github.io/2d-asset-toolkit/) · [⬇️ Download](#-quick-start) · [🧠 AI Models](#-ai-models) · [🐛 Report Bug](https://github.com/YOUR_USERNAME/2d-asset-toolkit/issues)

---

<img src="images/explorer.png" alt="2D Asset Toolkit — File Explorer" width="800">

</div>

---

## 🎯 What is this?

**2D Asset Toolkit** is a free, open-source desktop application built with Python and Tkinter, designed specifically for 2D game artists. It combines five essential tools into a single, cohesive dark-themed interface:

| Tool | Description |
|------|-------------|
| 📂 **File Explorer** | Browse folders, preview images, sort by name/size/resolution |
| ✂️ **Smart Trimmer** | Auto-crop transparent & color borders from sprites |
| 📐 **Image Resizer** | Batch-resize with 7 aspect-ratio-preserving modes |
| 🧠 **BG Remover** | AI-powered background removal using [rembg](https://github.com/danielgatis/rembg) |
| ⚙️ **Install Manager** | One-click installation of AI models with real terminal feedback |

No cloud services. No subscriptions. Everything runs locally on your machine.

---

## ✨ Features

### 📂 File Explorer

<div align="center">
<img src="images/explorer.png" alt="File Explorer" width="750">
</div>

<br>

- Drag & drop folders or click to browse
- **Three view modes**: Details list, Medium thumbnails, Large thumbnails
- Sort by name, file size (↑↓), or image resolution (↑↓)
- Live image preview with auto-scaling
- File metadata at a glance: size, type, resolution
- Back / Up navigation with breadcrumb path
- Supports **PNG, JPG, JPEG, WebP**

---

### ✂️ Smart Image Trimmer

<div align="center">
<img src="images/trimmer.png" alt="Smart Trimmer" width="750">
</div>

<br>

- **Alpha Threshold** (0–254) — control transparency detection aggressiveness
- **Color Trim** — remove pixels matching a target color (white, black, or custom)
- **Fuzz Tolerance** (0–255) — how close a color must be to get trimmed
- **Padding** — add pixels back around edges to prevent tight clipping
- Batch process entire folders recursively
- Overwrite originals or save to `trimmed/` subfolder
- Real-time log with before/after dimensions

---

### 📐 Image Resizer

<div align="center">
<img src="images/resizer.png" alt="Image Resizer" width="750">
</div>

<br>

- **7 resize modes**, all preserving aspect ratio:
  - Fit (no upscale) · Fit + Upscale · Exact Canvas (transparent pad)
  - Long Edge · Short Edge · Width Only · Height Only
- **Size presets**: 128², 256², 512², 1024², 2048², 1920×1080, 1280×720
- **Output formats**: PNG, JPEG, WebP, or keep original
- **Resampling filters**: LANCZOS, BICUBIC, BILINEAR, NEAREST (pixel art)
- Batch process with recursive folder support

---

### 🧠 Background Remover

<div align="center">
<img src="images/bg_remover.png" alt="Background Remover" width="750">
</div>

<br>

- AI-powered removal using [rembg](https://github.com/danielgatis/rembg)
- **7 ONNX models** for different use cases:

  | Model | Best For |
  |-------|----------|
  | 🚀 `isnet-general-use` | High precision, general purpose |
  | ⚡ `u2net` | Standard all-rounder |
  | 💨 `u2netp` | Fast / lightweight |
  | 🎯 `u2net_human_seg` | Characters & human figures |
  | 🎌 `isnet-anime` | Anime & cartoon art |
  | 🖤 `silueta` | Silhouette-focused |
  | 👕 `u2net_cloth_seg` | Clothing segmentation |

- Live status indicators (✅ installed / ❌ missing)
- **Alpha Matting** for cleaner edges
- **Auto-trim** after removal using built-in smart trim
- Progress bar and detailed per-file log

---

### ⚙️ Install Manager

<div align="center">
<img src="images/install.png" alt="Install Manager" width="750">
</div>

<br>

- One-click rembg installation via pip
- Per-model download buttons — opens a **real CMD/Terminal window**
- Real-time status checks for all models
- Shows Python path, model folder, platform info
- Quick button to open the model folder in your file manager
- Cross-platform: Windows CMD, macOS Terminal, Linux terminals

---

## 🖼️ All Screenshots

<div align="center">

| | | |
|:---:|:---:|:---:|
| <img src="images/explorer.png" width="360"><br>**📂 Explorer** | <img src="images/trimmer.png" width="360"><br>**✂️ Trimmer** | <img src="images/resizer.png" width="360"><br>**📐 Resizer** |
| <img src="images/bg_remover.png" width="360"><br>**🧠 BG Remover** | <img src="images/install.png" width="360"><br>**⚙️ Install** | |

</div>

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** — [Download here](https://www.python.org/downloads/)
- Make sure to check **"Add Python to PATH"** during installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/2d-asset-toolkit.git
cd 2d-asset-toolkit
