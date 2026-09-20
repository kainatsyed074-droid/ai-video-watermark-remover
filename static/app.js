document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const dropzone = document.getElementById("dropzone");
  const videoInput = document.getElementById("videoInput");
  const uploadSpinner = document.getElementById("uploadSpinner");
  const uploadSection = document.getElementById("uploadSection");
  const editorSection = document.getElementById("editorSection");
  const progressSection = document.getElementById("progressSection");

  // Meta Elements
  const metaFilename = document.getElementById("metaFilename");
  const metaResolution = document.getElementById("metaResolution");
  const metaFps = document.getElementById("metaFps");
  const metaDuration = document.getElementById("metaDuration");
  const btnChangeVideo = document.getElementById("btnChangeVideo");

  // Video & Canvas Elements
  const sourceVideo = document.getElementById("sourceVideo");
  const overlayCanvas = document.getElementById("overlayCanvas");
  const ctx = overlayCanvas.getContext("2d");
  const canvasWrapper = document.getElementById("canvasWrapper");

  // Timeline & Playback Elements
  const btnPlayPause = document.getElementById("btnPlayPause");
  const playIcon = document.getElementById("playIcon");
  const pauseIcon = document.getElementById("pauseIcon");
  const btnMuteUnmute = document.getElementById("btnMuteUnmute");
  const muteIcon = document.getElementById("muteIcon");
  const unmuteIcon = document.getElementById("unmuteIcon");
  const timeScrubber = document.getElementById("timeScrubber");
  const currentTimeDisplay = document.getElementById("currentTimeDisplay");
  const totalTimeDisplay = document.getElementById("totalTimeDisplay");

  // Multi-box management elements
  const boxCountBadge = document.getElementById("boxCountBadge");
  const btnAddBox = document.getElementById("btnAddBox");
  const btnAutoDetect = document.getElementById("btnAutoDetect");
  const btnQuickAutoExport = document.getElementById("btnQuickAutoExport");
  const detectAlert = document.getElementById("detectAlert");
  const detectAlertText = document.getElementById("detectAlertText");
  const boxListContainer = document.getElementById("boxListContainer");
  const activeBoxTitle = document.getElementById("activeBoxTitle");
  const presetSelect = document.getElementById("presetSelect");
  const checkFullVideo = document.getElementById("checkFullVideo");
  const timeRangeInputs = document.getElementById("timeRangeInputs");
  const inputStartTime = document.getElementById("inputStartTime");
  const inputEndTime = document.getElementById("inputEndTime");
  const btnSetStartNow = document.getElementById("btnSetStartNow");
  const btnSetEndNow = document.getElementById("btnSetEndNow");
  const btnDeleteActiveBox = document.getElementById("btnDeleteActiveBox");

  // Active Box Coordinates
  const inputX = document.getElementById("inputX");
  const inputY = document.getElementById("inputY");
  const inputW = document.getElementById("inputW");
  const inputH = document.getElementById("inputH");
  const featherSlider = document.getElementById("featherSlider");
  const featherValue = document.getElementById("featherValue");

  // Preview Elements
  const btnPreviewFrame = document.getElementById("btnPreviewFrame");
  const previewBox = document.getElementById("previewBox");
  const btnClosePreview = document.getElementById("btnClosePreview");
  const previewOrigImg = document.getElementById("previewOrigImg");
  const previewCleanImg = document.getElementById("previewCleanImg");

  // Process & Results
  const btnProcessVideo = document.getElementById("btnProcessVideo");
  const progressTitle = document.getElementById("progressTitle");
  const progressMessage = document.getElementById("progressMessage");
  const progressBarFill = document.getElementById("progressBarFill");
  const progressPercentage = document.getElementById("progressPercentage");
  const progressEta = document.getElementById("progressEta");
  const resultArea = document.getElementById("resultArea");
  const resultVideo = document.getElementById("resultVideo");
  const btnDownload = document.getElementById("btnDownload");
  const btnResetAll = document.getElementById("btnResetAll");
  const errorArea = document.getElementById("errorArea");
  const btnBackToEditor = document.getElementById("btnBackToEditor");

  // Distinct colors for different watermark areas
  const BOX_COLORS = [
    '#00ffff', // Cyan
    '#f43f5e', // Rose / Red-Pink
    '#fbbf24', // Amber / Gold
    '#10b981', // Emerald / Green
    '#a855f7', // Purple
    '#38bdf8'  // Sky Blue
  ];

  // Application State
  let currentVideoId = null;
  let videoInfo = null;
  let presetsData = {};
  let progressPollInterval = null;

  let boxes = [];
  let activeBoxId = null;
  let nextBoxNum = 1;
  let autoTriggerDownload = false;

  // Pointer Interaction State
  let pointerIsDown = false;
  let dragHasMoved = false;
  let dragMode = null; // 'create' | 'move' | 'tl' | 'tr' | 'bl' | 'br'
  let dragStartScreen = { x: 0, y: 0 };
  let dragStartVid = { x: 0, y: 0 };
  let initialBoxSnapshot = null;

  // Mute audio by default on source video to guarantee no browser autoplay block
  sourceVideo.muted = true;
  updateMuteIcon();

  function updateMuteIcon() {
    if (sourceVideo.muted) {
      muteIcon.style.display = "block";
      unmuteIcon.style.display = "none";
    } else {
      muteIcon.style.display = "none";
      unmuteIcon.style.display = "block";
    }
  }

  btnMuteUnmute.addEventListener("click", () => {
    sourceVideo.muted = !sourceVideo.muted;
    updateMuteIcon();
  });

  // -----------------------------------------------------
  // File Upload Handlers
  // -----------------------------------------------------
  dropzone.addEventListener("click", (e) => {
    if (e.target !== videoInput) videoInput.click();
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  videoInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });

  async function handleFileUpload(file) {
    const validExtensions = [".mp4", ".mov", ".mkv", ".webm"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!validExtensions.includes(ext)) {
      alert("Please select a valid video file (.mp4, .mov, .mkv, .webm)");
      return;
    }

    const dropContent = dropzone.querySelector(".dropzone-content");
    dropContent.style.display = "none";
    uploadSpinner.style.display = "block";

    const formData = new FormData();
    formData.append("video", file);

    // Check file size warning for Vercel serverless environment
    if (window.location.hostname.includes("vercel.app") && file.size > 4.5 * 1024 * 1024) {
      alert(
        `Vercel Serverless File Limit:\n\n` +
        `Your video is ${(file.size / (1024 * 1024)).toFixed(1)} MB, but Vercel free cloud hosting only permits uploads up to 4.5 MB.\n\n` +
        `For full-length, full-size 1080p & 4K HD videos with zero limits, please run the tool locally by double-clicking 'start.bat' on your computer.`
      );
      dropContent.style.display = "block";
      uploadSpinner.style.display = "none";
      return;
    }

    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });

      let data;
      const responseText = await response.text();
      try {
        data = JSON.parse(responseText);
      } catch (parseErr) {
        if (response.status === 413) {
          throw new Error("File size exceeds server upload limit (max 4.5MB on Vercel). Run locally with start.bat for unlimited file sizes.");
        }
        const cleanMsg = responseText.replace(/<[^>]*>?/gm, " ").replace(/\s+/g, " ").trim();
        throw new Error(`Server returned status ${response.status}: ${cleanMsg.substring(0, 120) || "Invalid response"}`);
      }

      if (!response.ok || data.error) {
        throw new Error(data.error || "Failed to upload video");
      }

      currentVideoId = data.video_id;
      videoInfo = data.info;

      // Populate meta info
      metaFilename.textContent = data.filename;
      metaResolution.textContent = `${videoInfo.width} × ${videoInfo.height} (${getResolutionTag(videoInfo.width, videoInfo.height)} • Original Resolution Preserved)`;
      metaFps.textContent = `${videoInfo.fps} fps`;
      metaDuration.textContent = formatDuration(videoInfo.duration);

      // Load presets for this resolution
      await loadPresets(videoInfo.width, videoInfo.height);

      // Setup video element
      sourceVideo.src = data.video_url;
      sourceVideo.load();

      function showEditor() {
        uploadSection.style.display = "none";
        editorSection.style.display = "block";

        if (videoInfo && videoInfo.width && videoInfo.height) {
          canvasWrapper.style.aspectRatio = `${videoInfo.width} / ${videoInfo.height}`;
        }

        setTimeout(() => {
          setupCanvas();
          boxes = [];
          nextBoxNum = 1;
          if (data.detected_boxes && data.detected_boxes.length > 0) {
            data.detected_boxes.forEach((det, idx) => {
              const b = createWatermarkBox(null, det.label || `Auto Watermark ${idx + 1}`);
              b.x = det.x;
              b.y = det.y;
              b.w = det.w;
              b.h = det.h;
              b.startTime = det.start_time !== null ? det.start_time : 0.0;
              b.endTime = det.end_time !== null ? det.end_time : Math.round(videoInfo ? videoInfo.duration || 5.0 : 5.0);
              b.fullVideo = (det.start_time === null && det.end_time === null);
            });
            renderBoxList();
            syncActiveBoxControls();
            drawOverlay();
            showDetectAlert(data.detected_boxes[0].label || "Gemini / Dola AI Watermark");
          } else {
            createWatermarkBox("gemini_bottom_right", "Watermark 1");
          }
        }, 80);
      }

      if (sourceVideo.readyState >= 1) {
        showEditor();
      } else {
        sourceVideo.onloadedmetadata = showEditor;
        sourceVideo.oncanplay = () => {
          if (editorSection.style.display === "none") showEditor();
        };
        setTimeout(() => {
          if (editorSection.style.display === "none") showEditor();
        }, 400);
      }

    } catch (err) {
      alert("Upload failed: " + err.message);
      dropContent.style.display = "block";
      uploadSpinner.style.display = "none";
    }
  }

  function getResolutionTag(w, h) {
    const maxDim = Math.max(w, h);
    if (maxDim >= 3840) return "4K UHD";
    if (maxDim >= 2560) return "2K QHD";
    if (maxDim >= 1920) return "1080p FHD";
    if (maxDim >= 1280) return "720p HD";
    return "SD";
  }

  function formatDuration(sec) {
    if (!sec || isNaN(sec)) return "00:00";
    const mins = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${String(mins).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  // -----------------------------------------------------
  // Presets
  // -----------------------------------------------------
  async function loadPresets(w, h) {
    try {
      const res = await fetch(`/api/presets?w=${w}&h=${h}`);
      presetsData = await res.json();
    } catch (err) {
      console.error("Failed to load presets:", err);
    }
  }

  // -----------------------------------------------------
  // Multi-Box Management
  // -----------------------------------------------------
  function getActiveBox() {
    return boxes.find(b => b.id === activeBoxId) || boxes[0] || null;
  }

  function createWatermarkBox(presetKey = "gemini_bottom_right", customName = null) {
    const num = nextBoxNum++;
    const id = "box_" + Date.now() + "_" + Math.random().toString(36).substr(2, 4);
    const color = BOX_COLORS[(num - 1) % BOX_COLORS.length];

    let coords = null;
    if (presetKey && presetsData[presetKey] && presetsData[presetKey].coords) {
      coords = { ...presetsData[presetKey].coords };
    } else {
      coords = {
        x: Math.round(videoInfo.width * 0.78),
        y: Math.round(videoInfo.height * 0.88),
        w: Math.round(videoInfo.width * 0.20),
        h: Math.round(videoInfo.height * 0.10)
      };
    }

    const newBox = {
      id: id,
      name: customName || `Watermark ${num}`,
      color: color,
      preset: presetKey || "custom",
      x: coords.x,
      y: coords.y,
      w: coords.w,
      h: coords.h,
      fullVideo: true,
      startTime: 0.0,
      endTime: Math.round(videoInfo ? videoInfo.duration || 5.0 : 5.0)
    };

    boxes.push(newBox);
    activeBoxId = id;
    renderBoxList();
    syncActiveBoxControls();
    drawOverlay();
    return newBox;
  }

  btnAddBox.addEventListener("click", () => {
    if (!videoInfo) return;
    const num = nextBoxNum;
    const newBox = createWatermarkBox("custom", `Watermark ${num}`);
    if (sourceVideo.currentTime > 0.5) {
      newBox.fullVideo = false;
      newBox.startTime = Math.max(0, Math.round(sourceVideo.currentTime * 10) / 10);
      newBox.endTime = Math.min(Math.round(videoInfo.duration * 10) / 10, newBox.startTime + 4.0);
      syncActiveBoxControls();
      renderBoxList();
    }
  });

  function renderBoxList() {
    boxCountBadge.textContent = `${boxes.length} Area${boxes.length > 1 ? 's' : ''}`;
    boxListContainer.innerHTML = "";

    boxes.forEach((b) => {
      const chip = document.createElement("div");
      chip.className = `box-item-chip ${b.id === activeBoxId ? "active" : ""}`;
      chip.dataset.boxId = b.id;

      const timeLabel = b.fullVideo 
        ? "Full Video" 
        : `${formatDuration(b.startTime)} - ${formatDuration(b.endTime)}`;

      chip.innerHTML = `
        <span class="box-color-dot" style="background: ${b.color}; box-shadow: 0 0 6px ${b.color};"></span>
        <div class="box-info-text">
          <div class="box-name-row">
            <span>${b.name}</span>
            <span style="font-size: 0.72rem; opacity: 0.8;">(${b.w}×${b.h})</span>
          </div>
          <span class="box-time-badge">${timeLabel}</span>
        </div>
        ${boxes.length > 1 ? `
          <button class="btn-chip-delete" title="Delete this watermark area" data-delete-id="${b.id}">
            &times;
          </button>
        ` : ""}
      `;

      chip.addEventListener("click", (e) => {
        if (e.target.closest(".btn-chip-delete")) {
          e.stopPropagation();
          deleteBox(b.id);
          return;
        }
        activeBoxId = b.id;
        renderBoxList();
        syncActiveBoxControls();
        drawOverlay();
      });

      boxListContainer.appendChild(chip);
    });
  }

  function deleteBox(id) {
    if (boxes.length <= 1) return;
    boxes = boxes.filter(b => b.id !== id);
    if (activeBoxId === id) {
      activeBoxId = boxes[0].id;
    }
    renderBoxList();
    syncActiveBoxControls();
    drawOverlay();
  }

  btnDeleteActiveBox.addEventListener("click", () => {
    if (activeBoxId) deleteBox(activeBoxId);
  });

  function syncActiveBoxControls() {
    const box = getActiveBox();
    if (!box) return;

    activeBoxTitle.textContent = `${box.name} Settings`;
    activeBoxTitle.style.color = box.color;
    presetSelect.value = box.preset || "custom";

    checkFullVideo.checked = box.fullVideo;
    timeRangeInputs.style.display = box.fullVideo ? "none" : "grid";
    inputStartTime.value = box.startTime;
    inputEndTime.value = box.endTime;

    inputX.value = box.x;
    inputY.value = box.y;
    inputW.value = box.w;
    inputH.value = box.h;

    btnDeleteActiveBox.style.display = boxes.length > 1 ? "block" : "none";
  }

  presetSelect.addEventListener("change", () => {
    const box = getActiveBox();
    if (!box || !videoInfo) return;

    box.preset = presetSelect.value;
    if (box.preset !== "custom" && presetsData[box.preset] && presetsData[box.preset].coords) {
      const c = presetsData[box.preset].coords;
      box.x = c.x;
      box.y = c.y;
      box.w = c.w;
      box.h = c.h;
      inputX.value = box.x;
      inputY.value = box.y;
      inputW.value = box.w;
      inputH.value = box.h;
    }
    renderBoxList();
    drawOverlay();
  });

  checkFullVideo.addEventListener("change", () => {
    const box = getActiveBox();
    if (!box) return;
    box.fullVideo = checkFullVideo.checked;
    timeRangeInputs.style.display = box.fullVideo ? "none" : "grid";
    renderBoxList();
    drawOverlay();
  });

  inputStartTime.addEventListener("input", (e) => {
    const box = getActiveBox();
    if (!box) return;
    box.startTime = Math.max(0, parseFloat(e.target.value) || 0);
    renderBoxList();
    drawOverlay();
  });

  inputEndTime.addEventListener("input", (e) => {
    const box = getActiveBox();
    if (!box) return;
    box.endTime = Math.max(box.startTime, parseFloat(e.target.value) || 0);
    renderBoxList();
    drawOverlay();
  });

  btnSetStartNow.addEventListener("click", () => {
    const box = getActiveBox();
    if (!box) return;
    const now = Math.round(sourceVideo.currentTime * 10) / 10;
    box.startTime = now;
    inputStartTime.value = now;
    if (box.endTime < now) {
      box.endTime = Math.min(Math.round(videoInfo.duration * 10) / 10, now + 4.0);
      inputEndTime.value = box.endTime;
    }
    renderBoxList();
    drawOverlay();
  });

  btnSetEndNow.addEventListener("click", () => {
    const box = getActiveBox();
    if (!box) return;
    const now = Math.round(sourceVideo.currentTime * 10) / 10;
    box.endTime = Math.max(box.startTime + 0.1, now);
    inputEndTime.value = box.endTime;
    renderBoxList();
    drawOverlay();
  });

  function updateActiveBoxFromInputs() {
    const box = getActiveBox();
    if (!box) return;
    box.x = parseInt(inputX.value) || 0;
    box.y = parseInt(inputY.value) || 0;
    box.w = parseInt(inputW.value) || 10;
    box.h = parseInt(inputH.value) || 10;
    box.preset = "custom";
    presetSelect.value = "custom";
    renderBoxList();
    drawOverlay();
  }

  [inputX, inputY, inputW, inputH].forEach(input => {
    input.addEventListener("input", updateActiveBoxFromInputs);
  });

  featherSlider.addEventListener("input", (e) => {
    featherValue.textContent = `${e.target.value} px`;
  });

  // -----------------------------------------------------
  // Canvas & Box Selection (Multi-Box Renderer)
  // -----------------------------------------------------
  function setupCanvas() {
    const rect = canvasWrapper.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      overlayCanvas.width = Math.round(rect.width);
      overlayCanvas.height = Math.round(rect.height);
      drawOverlay();
    }
  }

  const resizeObserver = new ResizeObserver(() => {
    if (editorSection.style.display !== "none" && videoInfo) {
      setupCanvas();
    }
  });
  resizeObserver.observe(canvasWrapper);

  function getCanvasScale() {
    const canvasW = overlayCanvas.width || 1;
    const canvasH = overlayCanvas.height || 1;
    const videoW = (videoInfo && videoInfo.width) || canvasW;
    const videoH = (videoInfo && videoInfo.height) || canvasH;

    const scale = Math.min(canvasW / videoW, canvasH / videoH);
    const renderW = videoW * scale;
    const renderH = videoH * scale;
    const offsetX = (canvasW - renderW) / 2;
    const offsetY = (canvasH - renderH) / 2;

    return { scale, offsetX, offsetY, renderW, renderH };
  }

  function screenToVideo(screenX, screenY) {
    const { scale, offsetX, offsetY } = getCanvasScale();
    const vidX = Math.round((screenX - offsetX) / scale);
    const vidY = Math.round((screenY - offsetY) / scale);
    return {
      vidX: Math.max(0, Math.min((videoInfo ? videoInfo.width : 1920), vidX)),
      vidY: Math.max(0, Math.min((videoInfo ? videoInfo.height : 1080), vidY))
    };
  }

  function hitTest(screenX, screenY) {
    const activeBox = getActiveBox();
    const { scale, offsetX, offsetY } = getCanvasScale();
    const HANDLE_DIST = 14;

    // 1. Check handles on the active box
    if (activeBox && activeBox.w > 0 && activeBox.h > 0) {
      const sx = offsetX + (activeBox.x * scale);
      const sy = offsetY + (activeBox.y * scale);
      const sw = activeBox.w * scale;
      const sh = activeBox.h * scale;

      if (Math.hypot(screenX - sx, screenY - sy) <= HANDLE_DIST) return { type: "tl", targetId: activeBox.id };
      if (Math.hypot(screenX - (sx + sw), screenY - sy) <= HANDLE_DIST) return { type: "tr", targetId: activeBox.id };
      if (Math.hypot(screenX - sx, screenY - (sy + sh)) <= HANDLE_DIST) return { type: "bl", targetId: activeBox.id };
      if (Math.hypot(screenX - (sx + sw), screenY - (sy + sh)) <= HANDLE_DIST) return { type: "br", targetId: activeBox.id };

      // Inside active box
      if (screenX >= sx && screenX <= sx + sw && screenY >= sy && screenY <= sy + sh) {
        return { type: "move", targetId: activeBox.id };
      }
    }

    // 2. Check inside any other existing boxes
    for (let i = boxes.length - 1; i >= 0; i--) {
      const b = boxes[i];
      if (b.id === activeBoxId) continue;
      const sx = offsetX + (b.x * scale);
      const sy = offsetY + (b.y * scale);
      const sw = b.w * scale;
      const sh = b.h * scale;
      if (screenX >= sx && screenX <= sx + sw && screenY >= sy && screenY <= sy + sh) {
        return { type: "switch", targetId: b.id };
      }
    }

    return { type: "outside", targetId: null };
  }

  function drawOverlay() {
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    if (!videoInfo || boxes.length === 0) return;

    const { scale, offsetX, offsetY } = getCanvasScale();
    const curTime = sourceVideo.currentTime;

    // Dim background outside
    ctx.fillStyle = "rgba(0, 0, 0, 0.4)";
    ctx.fillRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    // Clear cutouts for all active watermark boxes
    boxes.forEach(b => {
      const sx = offsetX + (b.x * scale);
      const sy = offsetY + (b.y * scale);
      const sw = b.w * scale;
      const sh = b.h * scale;
      ctx.clearRect(sx, sy, sw, sh);
    });

    // Render each box
    boxes.forEach(b => {
      const sx = offsetX + (b.x * scale);
      const sy = offsetY + (b.y * scale);
      const sw = b.w * scale;
      const sh = b.h * scale;

      const isActiveBox = (b.id === activeBoxId);
      const isTimeActive = b.fullVideo || (curTime >= b.startTime && curTime <= b.endTime);

      ctx.save();
      if (!isTimeActive) {
        ctx.globalAlpha = 0.35;
      }

      // Colored tint inside box
      ctx.fillStyle = b.color + "22";
      ctx.fillRect(sx, sy, sw, sh);

      // Border outline
      ctx.strokeStyle = b.color;
      if (isActiveBox) {
        ctx.lineWidth = 2.5;
        ctx.setLineDash([8, 4]);
        ctx.strokeRect(sx, sy, sw, sh);
        ctx.setLineDash([]);
      } else {
        ctx.lineWidth = 1.5;
        ctx.strokeRect(sx, sy, sw, sh);
      }

      // Tag badge above box
      const tagText = `${b.name} (${b.w}×${b.h})${!b.fullVideo ? ` [${b.startTime}s-${b.endTime}s]` : ''}`;
      ctx.font = "bold 11px sans-serif";
      const textWidth = ctx.measureText(tagText).width + 16;
      const tagY = sy >= 24 ? sy - 24 : sy + sh + 4;

      ctx.fillStyle = b.color;
      ctx.fillRect(sx, tagY, textWidth, 20);
      ctx.fillStyle = "#000000";
      ctx.fillText(tagText, sx + 8, tagY + 14);

      // Draw corner handles on active box
      if (isActiveBox) {
        const handleSize = 8;
        const corners = [
          [sx, sy],
          [sx + sw, sy],
          [sx, sy + sh],
          [sx + sw, sy + sh]
        ];

        corners.forEach(([cx, cy]) => {
          ctx.fillStyle = "#ffffff";
          ctx.strokeStyle = b.color;
          ctx.lineWidth = 2;
          ctx.fillRect(cx - handleSize/2, cy - handleSize/2, handleSize, handleSize);
          ctx.strokeRect(cx - handleSize/2, cy - handleSize/2, handleSize, handleSize);
        });
      }

      ctx.restore();
    });
  }

  // Pointer Interaction (Draw, Move, Resize, Switch, or Click-to-Play)
  overlayCanvas.addEventListener("pointerdown", (e) => {
    if (!videoInfo || boxes.length === 0) return;
    overlayCanvas.setPointerCapture(e.pointerId);

    pointerIsDown = true;
    dragHasMoved = false;

    const rect = overlayCanvas.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;

    const hit = hitTest(screenX, screenY);
    const { vidX, vidY } = screenToVideo(screenX, screenY);

    dragStartScreen = { x: screenX, y: screenY };
    dragStartVid = { x: vidX, y: vidY };

    if (hit.type === "switch") {
      activeBoxId = hit.targetId;
      renderBoxList();
      syncActiveBoxControls();
      dragMode = "move";
      const box = getActiveBox();
      initialBoxSnapshot = { ...box };
      drawOverlay();
      return;
    }

    dragMode = hit.type; // 'move', 'tl', 'tr', 'bl', 'br', or 'outside'
    const box = getActiveBox();
    initialBoxSnapshot = { ...box };
  });

  overlayCanvas.addEventListener("pointermove", (e) => {
    const rect = overlayCanvas.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;

    if (!pointerIsDown) {
      // Hover cursor updates
      const hit = hitTest(screenX, screenY);
      if (hit.type === "tl" || hit.type === "br") overlayCanvas.style.cursor = "nwse-resize";
      else if (hit.type === "tr" || hit.type === "bl") overlayCanvas.style.cursor = "nesw-resize";
      else if (hit.type === "move") overlayCanvas.style.cursor = "move";
      else if (hit.type === "switch") overlayCanvas.style.cursor = "pointer";
      else overlayCanvas.style.cursor = "crosshair";
      return;
    }

    const dist = Math.hypot(screenX - dragStartScreen.x, screenY - dragStartScreen.y);
    if (dist > 6) {
      dragHasMoved = true;
    }

    if (!dragHasMoved) return;

    const box = getActiveBox();
    if (!box) return;

    const { vidX, vidY } = screenToVideo(screenX, screenY);
    const maxW = videoInfo.width;
    const maxH = videoInfo.height;

    if (dragMode === "outside") {
      // Dragging outside draws a new bounding area for the active watermark
      box.x = Math.max(1, Math.min(dragStartVid.x, vidX));
      box.y = Math.max(1, Math.min(dragStartVid.y, vidY));
      box.w = Math.max(10, Math.min(maxW - 1 - box.x, Math.abs(vidX - dragStartVid.x)));
      box.h = Math.max(10, Math.min(maxH - 1 - box.y, Math.abs(vidY - dragStartVid.y)));
      box.preset = "custom";
      presetSelect.value = "custom";
    } else if (dragMode === "move") {
      const deltaX = vidX - dragStartVid.x;
      const deltaY = vidY - dragStartVid.y;
      box.x = Math.max(1, Math.min(maxW - 1 - initialBoxSnapshot.w, initialBoxSnapshot.x + deltaX));
      box.y = Math.max(1, Math.min(maxH - 1 - initialBoxSnapshot.h, initialBoxSnapshot.y + deltaY));
      box.preset = "custom";
      presetSelect.value = "custom";
    } else if (dragMode === "br") {
      box.w = Math.max(10, Math.min(maxW - 1 - box.x, vidX - box.x));
      box.h = Math.max(10, Math.min(maxH - 1 - box.y, vidY - box.y));
    } else if (dragMode === "tl") {
      const origRight = initialBoxSnapshot.x + initialBoxSnapshot.w;
      const origBottom = initialBoxSnapshot.y + initialBoxSnapshot.h;
      box.x = Math.max(1, Math.min(origRight - 10, vidX));
      box.y = Math.max(1, Math.min(origBottom - 10, vidY));
      box.w = origRight - box.x;
      box.h = origBottom - box.y;
    } else if (dragMode === "tr") {
      const origLeft = initialBoxSnapshot.x;
      const origBottom = initialBoxSnapshot.y + initialBoxSnapshot.h;
      box.y = Math.max(1, Math.min(origBottom - 10, vidY));
      box.h = origBottom - box.y;
      box.w = Math.max(10, Math.min(maxW - 1 - origLeft, vidX - origLeft));
    } else if (dragMode === "bl") {
      const origRight = initialBoxSnapshot.x + initialBoxSnapshot.w;
      const origTop = initialBoxSnapshot.y;
      box.x = Math.max(1, Math.min(origRight - 10, vidX));
      box.w = origRight - box.x;
      box.h = Math.max(10, Math.min(maxH - 1 - origTop, vidY - origTop));
    }

    inputX.value = box.x;
    inputY.value = box.y;
    inputW.value = box.w;
    inputH.value = box.h;

    renderBoxList();
    drawOverlay();
  });

  overlayCanvas.addEventListener("pointerup", (e) => {
    if (pointerIsDown) {
      overlayCanvas.releasePointerCapture(e.pointerId);

      // If user merely clicked without dragging and was outside all boxes: toggle Play / Pause!
      if (!dragHasMoved && dragMode === "outside") {
        togglePlay();
      }

      pointerIsDown = false;
      dragHasMoved = false;
      dragMode = null;
      renderBoxList();
      drawOverlay();
    }
  });

  overlayCanvas.addEventListener("pointercancel", () => {
    pointerIsDown = false;
    dragHasMoved = false;
    dragMode = null;
    drawOverlay();
  });

  // -----------------------------------------------------
  // Timeline & Playback Control
  // -----------------------------------------------------
  function togglePlay() {
    if (sourceVideo.paused) {
      sourceVideo.play().then(() => {
        playIcon.style.display = "none";
        pauseIcon.style.display = "block";
      }).catch(err => {
        console.warn("Autoplay blocked, playing muted:", err);
        sourceVideo.muted = true;
        updateMuteIcon();
        sourceVideo.play().then(() => {
          playIcon.style.display = "none";
          pauseIcon.style.display = "block";
        }).catch(e => console.error("Playback failed:", e));
      });
    } else {
      sourceVideo.pause();
      playIcon.style.display = "block";
      pauseIcon.style.display = "none";
    }
  }

  btnPlayPause.addEventListener("click", togglePlay);

  sourceVideo.addEventListener("timeupdate", () => {
    const cur = sourceVideo.currentTime;
    const dur = sourceVideo.duration || (videoInfo ? videoInfo.duration : 1);
    if (dur > 0 && !isNaN(dur)) {
      timeScrubber.value = (cur / dur) * 100;
      currentTimeDisplay.textContent = formatDuration(cur);
      totalTimeDisplay.textContent = formatDuration(dur);
    }
    drawOverlay();
  });

  sourceVideo.addEventListener("ended", () => {
    playIcon.style.display = "block";
    pauseIcon.style.display = "none";
  });

  timeScrubber.addEventListener("input", (e) => {
    const pct = parseFloat(e.target.value) / 100;
    const dur = sourceVideo.duration || (videoInfo ? videoInfo.duration : 1);
    if (dur && !isNaN(dur)) {
      sourceVideo.currentTime = Math.max(0, Math.min(dur, pct * dur));
    }
    drawOverlay();
  });

  // -----------------------------------------------------
  // Live Frame Preview (All Watermarks)
  // -----------------------------------------------------
  btnPreviewFrame.addEventListener("click", async () => {
    if (!currentVideoId || boxes.length === 0) return;

    btnPreviewFrame.disabled = true;
    btnPreviewFrame.innerHTML = "Generating Preview...";

    const algorithm = document.querySelector('input[name="algorithm"]:checked').value;
    const feather = parseInt(featherSlider.value) || 5;

    const payloadBoxes = boxes.map(b => ({
      x: b.x,
      y: b.y,
      w: b.w,
      h: b.h,
      start_time: b.fullVideo ? null : b.startTime,
      end_time: b.fullVideo ? null : b.endTime
    }));

    try {
      const res = await fetch("/api/preview_frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: currentVideoId,
          timestamp: sourceVideo.currentTime,
          boxes: payloadBoxes,
          method: algorithm,
          feather: feather
        })
      });

      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Preview failed");

      previewOrigImg.src = data.original_url;
      previewCleanImg.src = data.cleaned_url;
      previewBox.style.display = "block";
      previewBox.scrollIntoView({ behavior: "smooth", block: "nearest" });

    } catch (err) {
      alert("Preview error: " + err.message);
    } finally {
      btnPreviewFrame.disabled = false;
      btnPreviewFrame.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-svg"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
        Preview Current Frame
      `;
    }
  });

  btnClosePreview.addEventListener("click", () => {
    previewBox.style.display = "none";
  });

  // -----------------------------------------------------
  // Auto-Detect AI Watermark (Gemini / Dola AI)
  // -----------------------------------------------------
  function showDetectAlert(msg) {
    if (detectAlert && detectAlertText) {
      detectAlertText.textContent = `✨ ${msg} automatically detected & selected!`;
      detectAlert.style.display = "flex";
      setTimeout(() => {
        if (detectAlert) detectAlert.style.display = "none";
      }, 7000);
    }
  }

  async function performAutoDetect(autoExportAfter = false) {
    if (!currentVideoId || !videoInfo) {
      alert("Please upload a video first.");
      return;
    }

    if (btnAutoDetect) {
      btnAutoDetect.disabled = true;
      btnAutoDetect.innerHTML = "⏳ Detecting...";
    }

    try {
      const res = await fetch("/api/auto_detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: currentVideoId })
      });
      const data = await res.json();
      if (data.status === "success" && data.boxes && data.boxes.length > 0) {
        boxes = [];
        nextBoxNum = 1;
        data.boxes.forEach((det, idx) => {
          const b = createWatermarkBox(null, det.label || `Auto Watermark ${idx + 1}`);
          b.x = det.x;
          b.y = det.y;
          b.w = det.w;
          b.h = det.h;
          b.startTime = det.start_time !== null ? det.start_time : 0.0;
          b.endTime = det.end_time !== null ? det.end_time : Math.round(videoInfo ? videoInfo.duration || 5.0 : 5.0);
          b.fullVideo = (det.start_time === null && det.end_time === null);
        });
        renderBoxList();
        syncActiveBoxControls();
        drawOverlay();
        showDetectAlert(data.boxes[0].label || "Gemini / Dola AI Watermark");

        if (autoExportAfter) {
          autoTriggerDownload = true;
          setTimeout(() => {
            btnProcessVideo.click();
          }, 350);
        }
      } else {
        alert("No specific watermark detected automatically. You can manually drag on the video to select the watermark area.");
      }
    } catch (err) {
      console.error("Auto detect failed:", err);
      alert("Auto-detection error: " + err.message);
    } finally {
      if (btnAutoDetect) {
        btnAutoDetect.disabled = false;
        btnAutoDetect.innerHTML = "🤖 Auto-Detect & Remove";
      }
    }
  }

  if (btnAutoDetect) {
    btnAutoDetect.addEventListener("click", () => performAutoDetect(true));
  }

  if (btnQuickAutoExport) {
    btnQuickAutoExport.addEventListener("click", () => {
      if (!currentVideoId) {
        alert("Please upload a video first.");
        return;
      }
      performAutoDetect(true);
    });
  }

  // -----------------------------------------------------
  // Process Full Video & Export HD
  // -----------------------------------------------------
  btnProcessVideo.addEventListener("click", async () => {
    if (!currentVideoId || boxes.length === 0) {
      alert("Please upload a video and select at least one watermark area.");
      return;
    }

    autoTriggerDownload = true;

    const algoEl = document.querySelector('input[name="algorithm"]:checked');
    const algorithm = (algoEl && algoEl.value) ? algoEl.value : "delogo";
    const feather = parseInt(featherSlider.value) || 5;

    const payloadBoxes = boxes.map(b => ({
      x: b.x,
      y: b.y,
      w: b.w,
      h: b.h,
      start_time: b.fullVideo ? null : b.startTime,
      end_time: b.fullVideo ? null : b.endTime
    }));

    editorSection.style.display = "none";
    progressSection.style.display = "block";
    progressSection.scrollIntoView({ behavior: "smooth" });

    progressTitle.textContent = `Removing Watermark...`;
    progressMessage.textContent = "Removing watermark from selected area...";
    progressBarFill.style.width = "0%";
    progressPercentage.textContent = "0%";
    progressEta.textContent = "Processing...";
    resultArea.style.display = "none";
    if (errorArea) errorArea.style.display = "none";

    try {
      const res = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: currentVideoId,
          boxes: payloadBoxes,
          method: algorithm,
          feather: feather
        })
      });

      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Failed to start processing");

      pollProgress(data.task_id);

    } catch (err) {
      alert("Error: " + err.message);
      progressSection.style.display = "none";
      editorSection.style.display = "block";
    }
  });

  function pollProgress(taskId) {
    if (progressPollInterval) clearInterval(progressPollInterval);

    progressPollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/progress/${taskId}`);
        const task = await res.json();

        if (task.error) {
          clearInterval(progressPollInterval);
          alert(task.error);
          return;
        }

        const pct = Math.round(task.progress || 0);
        progressBarFill.style.width = `${pct}%`;
        progressPercentage.textContent = `${pct}%`;
        progressMessage.textContent = task.message || "Removing watermark...";

        if (task.status === "completed") {
          clearInterval(progressPollInterval);
          progressTitle.textContent = "Watermark Removed Successfully!";
          progressEta.textContent = "Ready for download";
          progressBarFill.style.width = "100%";
          progressPercentage.textContent = "100%";

          resultVideo.src = task.video_url;
          resultVideo.load();
          btnDownload.href = task.download_url;
          resultArea.style.display = "block";
          if (errorArea) errorArea.style.display = "none";

          // Automatic instant download
          if (autoTriggerDownload) {
            autoTriggerDownload = false;
            setTimeout(() => {
              const tempLink = document.createElement("a");
              tempLink.href = task.download_url;
              tempLink.setAttribute("download", "");
              document.body.appendChild(tempLink);
              tempLink.click();
              document.body.removeChild(tempLink);
            }, 300);
          }
        } else if (task.status === "error") {
          clearInterval(progressPollInterval);
          progressTitle.textContent = "Processing Failed";
          progressMessage.textContent = task.message || "An error occurred";
          if (errorArea) errorArea.style.display = "block";
        }
      } catch (e) {
        console.error("Poll error:", e);
      }
    }, 350);
  }

  if (btnBackToEditor) {
    btnBackToEditor.addEventListener("click", () => {
      if (progressPollInterval) clearInterval(progressPollInterval);
      progressSection.style.display = "none";
      editorSection.style.display = "block";
      editorSection.scrollIntoView({ behavior: "smooth" });
    });
  }

  // -----------------------------------------------------
  // Reset & Change Video
  // -----------------------------------------------------
  btnChangeVideo.addEventListener("click", resetEditor);
  btnResetAll.addEventListener("click", resetEditor);

  function resetEditor() {
    if (progressPollInterval) clearInterval(progressPollInterval);
    sourceVideo.pause();
    sourceVideo.src = "";
    resultVideo.pause();
    resultVideo.src = "";
    currentVideoId = null;
    videoInfo = null;
    boxes = [];
    activeBoxId = null;
    nextBoxNum = 1;
    videoInput.value = "";
    previewBox.style.display = "none";
    progressSection.style.display = "none";
    editorSection.style.display = "none";
    uploadSection.style.display = "block";
    dropzone.querySelector(".dropzone-content").style.display = "block";
    uploadSpinner.style.display = "none";
  }
});
