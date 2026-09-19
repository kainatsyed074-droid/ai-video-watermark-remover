# 🎬 AI Video Watermark Remover

AI videos (Gemini / Veo, Dola AI, Runway, Sora, Luma, Kling, etc.) se watermarks aur logos ko remove karne ke liye powerful aur aasaan desktop web tool.

---

## ✨ Features

- **Multiple Watermark Zones (Multi-Box Support)**:
  - Video mein 1 se zyada watermarks (3–4 mukhtalif jagahon par) ek sath remove karein (**➕ Add Area**).
  - Har watermark ka apna timeline range set karein (kab shuru ho aur kab khatam ho) ya poori video par apply karein.
- **Har Qisam Ka Watermark Remove Karein**:
  - **Gemini / Veo (Bottom-Right)**
  - **Dola AI (Bottom-Right)**
  - **Custom Bounding Box**: Video par mouse se drag karke kisi bhi jagah ka watermark ya logo select karein.
  - **Corner Presets**: Top-Right, Top-Left, Bottom-Right, Bottom-Left, Bottom-Center.
- **Original HD Resolution (100% Quality Preserved)**:
  - Video ka resolution (1080p Full HD, 4K UHD, 720p), aspect ratio aur frame rate (FPS) 100% barkarar rehta hai.
  - Audio track direct passthrough hota hai (koi quality loss ya audio out-of-sync nahi hota).
- **Multiple Smart Removal Algorithms & Auto-Fallback**:
  - 🚀 **FFmpeg Delogo**: Ultra-fast and crisp edge interpolation with automatic border protection.
  - 🧠 **AI Inpainting (Telea)**: Fast marching reconstruction based on surrounding textures.
  - 🌊 **AI Inpainting (Navier-Stokes)**: Fluid-dynamics edge continuation for solid & gradient backgrounds.
  - 🌫️ **Feathered Smart Blur**: Soft Gaussian blur without any harsh rectangular cut lines.
- **Live Frame Preview**: Puri video process karne se pehle current frame par Before vs After result check karein.
- **Real-Time Progress Bar & Safe Recovery**: Rendering percentage, live status updates, aur 1-click "Back to Editor" option.
- **1-Click Download**: Clean HD video instant download karein.

---

## 🚀 How to Run / Chalane Ka Tareeqa

### Tareeqa 1: Direct Double Click
1. Simply double-click **`start.bat`**.
2. Aapka browser automatic `http://localhost:5000` par open ho jayega.

### Tareeqa 2: Command Line (PowerShell / CMD)
```bash
# Agar requirements install karni hon:
install_dependencies.bat

# App start karne ke liye:
start.bat
```

---

## 📖 Step-by-Step Guide: Video Watermark Remove Kaise Karein

1. **Step 1 - Video Upload Karein**:
   - `start.bat` chalane ke baad browser me apni AI video drag & drop karein ya "Browse Video File" par click karein.
2. **Step 2 - Watermark Select Karein**:
   - Agar video Gemini ya Dola AI ki hai, to preset dropdown me se **Gemini / Veo** ya **Dola AI** select karein.
   - Ya phir video player ke upar mouse se drag karke watermark ke upar box bana dein.
   - Apni pasand ka removal algorithm select karein (Default: *FFmpeg Delogo* ya *AI Inpainting*).
3. **Step 3 - Live Preview Check Karein**:
   - **"Preview Current Frame"** par click karke dekhein ke watermark kitna saaf remove hua hai.
4. **Step 4 - Export & Download**:
   - **"Remove Watermark & Export HD Video"** par click karein.
   - Progress bar 100% hone par **"Download Clean HD Video"** button par click karein.
