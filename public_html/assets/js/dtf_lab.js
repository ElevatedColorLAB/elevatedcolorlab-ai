// Update PROXY_URL to point to your PHP API
const PROXY_URL = 'api-proxy.php';

// Map tool names to API service names based on your PHP proxy
const serviceMap = {
    'upscaler': 'upscaler',       // Port 8001
    'vectorizer': 'vectorizer',   // Port 8002
    'bg_remover': 'bg_remover',   // Port 8005
    'knockout': 'image_prep',     // Port 8008
    'transparency': 'image_prep', // Port 8008
    'crop': 'image_prep',         // Port 8008
    'halftone': 'halftone',       // Port 8006
    'digitizer': 'digitizer'      // Port 8007
};

const appState = {
    editor: { 
        img: null, file: null, zoom: 1, panX: 0, panY: 0, history: [],
        width: 0, height: 0 
    },
    queue: [],
    sheet: { 
        width: 22, 
        length: 24, 
        zoom: 1, 
        panX: 0, 
        panY: 0, 
        manualPan: false, 
        draggedItem: null,
        allowRotation: true,
        tightPacking: false, // Default to OFF
        aggressiveRotation: false,
        autoArrange: true,
        edgeSpacing: { horizontal: 0.25, vertical: 0.5 },
        isRollMedia: true,
        deadSpaceReduction: true,
        showGrid: false
    },
    pricing: { cost: 0.025 }
};

function init() {
    checkServices();
    switchMode('editor');
    window.addEventListener('resize', () => { resetEditorZoom(); fitGS(); });
    
    // Initialize packing options
    document.getElementById('tight-packing').addEventListener('change', function() {
        appState.sheet.tightPacking = this.checked;
        const container = document.getElementById('gang-sheet');
        if (this.checked) {
            container.classList.add('tight-packing');
        } else {
            container.classList.remove('tight-packing');
        }
    });
    
    document.getElementById('allow-rotation').addEventListener('change', function() {
        appState.sheet.allowRotation = this.checked;
    });
    
    document.getElementById('aggressive-rotation').addEventListener('change', function() {
        appState.sheet.aggressiveRotation = this.checked;
    });
    
    document.getElementById('auto-arrange').addEventListener('change', function() {
        appState.sheet.autoArrange = this.checked;
    });
    
    document.getElementById('show-grid').addEventListener('change', function() {
        appState.sheet.showGrid = this.checked;
        updateGridOverlay();
    });
    
    // Initialize edge spacing
    updateEdgeSpacing();
    
    // Initialize queue count
    updateQueueCount();
    
    // Auto-center gang sheet on page load
    setTimeout(() => {
        if (document.getElementById('view-gangsheet').classList.contains('hidden')) {
            // Wait for mode switch if needed
            const checkCenter = () => {
                if (!document.getElementById('view-gangsheet').classList.contains('hidden')) {
                    fitGS();
                }
            };
            // Check when switching to gang sheet mode
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.addEventListener('click', function() {
                    if (this.id === 'tab-gangsheet') {
                        setTimeout(fitGS, 100);
                    }
                });
            });
        }
    }, 100);
}

function checkServices() {
    // Test connection to main app
    const formData = new FormData();
    formData.append('service', 'main_app');
    formData.append('endpoint', '/health');
    
    fetch(PROXY_URL, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('vps-dot').classList.replace('bg-yellow-500', 'bg-green-500');
        document.getElementById('vps-status').innerText = "Services Online";
    })
    .catch(error => {
        console.error('Service check failed:', error);
        document.getElementById('vps-dot').classList.replace('bg-yellow-500', 'bg-red-500');
        document.getElementById('vps-status').innerText = "Services Offline";
    });
}

window.switchMode = (mode) => {
    document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${mode}`).classList.add('active');
    document.getElementById('view-editor').classList.add('hidden');
    document.getElementById('view-gangsheet').classList.add('hidden');
    document.getElementById(`view-${mode}`).classList.remove('hidden');
    if (mode === 'gangsheet') {
        document.getElementById('top-cost-display').classList.remove('hidden');
        document.getElementById('top-cost-display').classList.add('flex');
        // Auto-center gang sheet when switching to gang sheet mode
        requestAnimationFrame(() => setTimeout(fitGS, 100));
        updateGridOverlay();
    } else {
        document.getElementById('top-cost-display').classList.add('hidden');
        document.getElementById('top-cost-display').classList.remove('flex');
    }
};

// --- EDITOR LOGIC ---
function pushHistory() {
    const src = document.getElementById('editor-img').src;
    if(src) {
        appState.editor.history.push(src);
        if(appState.editor.history.length > 5) appState.editor.history.shift(); 
        document.getElementById('btn-undo').disabled = false;
    }
}

function editorUndo() {
    if(appState.editor.history.length > 0) {
        const prev = appState.editor.history.pop();
        const img = new Image();
        img.onload = () => {
            appState.editor.img = img;
            document.getElementById('editor-img').src = prev;
            analyzeImageHealth(img, 'image/png');
            updateImageStats(img);
        };
        img.src = prev;
        if(appState.editor.history.length === 0) document.getElementById('btn-undo').disabled = true;
    }
}

function loadEditorImage(file) {
    if (!file) return;
    appState.editor.file = file;
    appState.editor.history = []; 
    document.getElementById('btn-undo').disabled = true;
    
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            appState.editor.img = img;
            document.getElementById('editor-img').src = e.target.result;
            document.getElementById('editor-img').classList.remove('hidden');
            document.getElementById('editor-placeholder').classList.add('hidden');
            document.getElementById('btn-dl-img').disabled = false;
            document.getElementById('btn-add-gang').disabled = false;
            
            const wIn = parseFloat((img.naturalWidth / 300).toFixed(2));
            const hIn = parseFloat((img.naturalHeight / 300).toFixed(2));
            
            appState.editor.width = wIn;
            appState.editor.height = hIn;
            
            document.getElementById('prop-orig').innerText = `${img.naturalWidth} x ${img.naturalHeight} px`;
            document.getElementById('image-props').classList.remove('hidden');
            
            document.getElementById('target-width').value = wIn;
            document.getElementById('target-height').value = hIn;
            
            updateImageStats();
            analyzeImageHealth(img, file.type);
            requestAnimationFrame(() => setTimeout(resetEditorZoom, 50));
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function updateTargetSize(changed) {
    const wInput = document.getElementById('target-width');
    const hInput = document.getElementById('target-height');
    const img = appState.editor.img;
    if(!img) return;
    
    const ratio = img.naturalWidth / img.naturalHeight;
    
    if (changed === 'w') {
        appState.editor.width = parseFloat(wInput.value);
        appState.editor.height = parseFloat((appState.editor.width / ratio).toFixed(2));
        hInput.value = appState.editor.height;
    } else {
        appState.editor.height = parseFloat(hInput.value);
        appState.editor.width = parseFloat((appState.editor.height * ratio).toFixed(2));
        wInput.value = appState.editor.width;
    }
    updateImageStats();
    analyzeImageHealth(img, appState.editor.file.type);
}

function updateImageStats() {
    const img = appState.editor.img;
    if(!img) return;
    const dpiX = Math.round(img.naturalWidth / appState.editor.width);
    const dpiY = Math.round(img.naturalHeight / appState.editor.height);
    const avgDpi = Math.min(dpiX, dpiY);
    const dpiEl = document.getElementById('prop-dpi');
    dpiEl.innerText = avgDpi;
    if(avgDpi < 250) dpiEl.className = "text-red-400 font-mono font-bold";
    else if (avgDpi < 300) dpiEl.className = "text-yellow-400 font-mono font-bold";
    else dpiEl.className = "text-green-400 font-mono font-bold";
}

function analyzeImageHealth(img, fileType) {
    const content = document.getElementById('health-content');
    document.getElementById('health-panel').classList.remove('hidden');
    content.innerHTML = '';

    const issues = [];
    const targetPixelsW = appState.editor.width * 300;
    
    if (img.naturalWidth < targetPixelsW * 0.9) {
        const color = img.naturalWidth < targetPixelsW * 0.5 ? 'text-red-400' : 'text-yellow-400';
        issues.push({ icon: `fa-exclamation-triangle ${color}`, text: `Low Res for Print Size`, fix: 'Recommend Upscale to Size', tool: 'upscaler' });
    } else {
        issues.push({ icon: 'fa-check-circle text-green-400', text: 'Resolution: Good', fix: null });
    }

    const cvs = document.createElement('canvas');
    cvs.width = 50; cvs.height = 50; 
    const ctx = cvs.getContext('2d');
    ctx.drawImage(img, 0, 0, 50, 50);
    const data = ctx.getImageData(0, 0, 50, 50).data;
    
    let hasTransparency = false;
    let hasBlack = false;

    for(let i=3; i<data.length; i+=4) {
        if(data[i] < 250) { hasTransparency = true; }
        else if(data[i-3] < 30 && data[i-2] < 30 && data[i-1] < 30) { hasBlack = true; }
    }

    if (hasBlack && !hasTransparency) issues.push({ icon: 'fa-square text-slate-400', text: 'Dark Background', fix: 'Recommend Knockout Black', tool: 'knockout' });
    else if (!hasTransparency) issues.push({ icon: 'fa-square text-white', text: 'Solid Background', fix: 'Recommend Remove BG', tool: 'bg_remover' });
    else issues.push({ icon: 'fa-check-circle text-green-400', text: 'Transparent Background', fix: null });

    issues.forEach(i => {
        const div = document.createElement('div');
        div.className = 'flex items-start gap-2 text-[10px] text-slate-300';
        div.innerHTML = `<i class="fas ${i.icon} mt-0.5"></i> <div class="flex-1"><p class="font-bold">${i.text}</p></div>${i.fix ? `<button onclick="runTool('${i.tool}')" class="rec-btn">Fix</button>` : ''}`;
        content.appendChild(div);
    });
}

async function runTool(tool) {
    if (!appState.editor.img) return alert("Upload an image first.");
    
    const service = serviceMap[tool];
    if (!service) {
        alert(`Tool "${tool}" not configured in API`);
        return;
    }
    
    pushHistory(); 
    const status = document.getElementById('editor-status');
    status.classList.remove('hidden');
    
    let endpoint = '';
    let options = {};
    
    // Map tools to endpoints based on your API structure
    switch(tool) {
        case 'upscaler':
            endpoint = '/upscale';
            options = { target_width: appState.editor.width * 300 };
            break;
        case 'vectorizer':
            endpoint = '/vectorize';
            break;
        case 'bg_remover':
            endpoint = '/remove-bg';
            break;
        case 'knockout':
            endpoint = '/knockout_black';
            break;
        case 'transparency':
            endpoint = '/fix_transparency';
            break;
        case 'crop':
            endpoint = '/crop_transparent';
            break;
        case 'halftone':
            endpoint = '/halftone';
            break;
        default:
            endpoint = '/process';
    }
    
    try {
        const formData = new FormData();
        
        // Convert image to blob for upload
        const imageBlob = await (await fetch(document.getElementById('editor-img').src)).blob();
        formData.append('file', imageBlob, 'image.png');
        
        // Add options as JSON
        if (Object.keys(options).length > 0) {
            formData.append('options', JSON.stringify(options));
        }
        
        formData.append('service', service);
        formData.append('endpoint', endpoint);
        
        const response = await fetch(PROXY_URL, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        // Check if response is JSON or image
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            if (data.image) {
                const newImg = new Image();
                newImg.onload = () => {
                    appState.editor.img = newImg;
                    document.getElementById('editor-img').src = data.image;
                    updateImageStats(newImg);
                    analyzeImageHealth(newImg, 'image/png');
                };
                newImg.src = data.image;
            } else {
                alert("Tool completed but no image returned.");
            }
        } else if (contentType && contentType.includes('image/')) {
            // Handle direct image response
            const imageBlob = await response.blob();
            const imageUrl = URL.createObjectURL(imageBlob);
            const newImg = new Image();
            newImg.onload = () => {
                appState.editor.img = newImg;
                document.getElementById('editor-img').src = imageUrl;
                updateImageStats(newImg);
                analyzeImageHealth(newImg, 'image/png');
                URL.revokeObjectURL(imageUrl);
            };
            newImg.src = imageUrl;
        } else {
            // Try to parse as JSON anyway
            try {
                const data = await response.json();
                if (data.image) {
                    const newImg = new Image();
                    newImg.onload = () => {
                        appState.editor.img = newImg;
                        document.getElementById('editor-img').src = data.image;
                        updateImageStats(newImg);
                        analyzeImageHealth(newImg, 'image/png');
                    };
                    newImg.src = data.image;
                }
            } catch (e) {
                alert("Unexpected response from server");
            }
        }
    } catch (error) {
        console.error('Tool error:', error);
        alert(`Error processing image: ${error.message}`);
    } finally {
        status.classList.add('hidden');
    }
}

function downloadCurrentImage() {
    if (!appState.editor.img) return;
    const link = document.createElement('a');
    link.href = document.getElementById('editor-img').src;
    link.download = 'edited_design.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function addToGangSheet() {
    if (!appState.editor.img) return;
    const item = {
        id: Date.now(),
        url: document.getElementById('editor-img').src,
        width: appState.editor.width,
        height: appState.editor.height,
        qty: 1
    };
    appState.queue.push(item);
    updateQueueUI();
    const btn = document.getElementById('btn-add-gang');
    const orig = btn.innerHTML;
    btn.innerHTML = `<i class="fas fa-check"></i> Added!`;
    btn.classList.replace('bg-indigo-600', 'bg-green-600');
    setTimeout(() => { btn.innerHTML = orig; btn.classList.replace('bg-green-600', 'bg-indigo-600'); }, 1500);
}

// --- GANG SHEET LOGIC ---
function handleDirectUpload(files) {
    if(!files.length) return;
    Array.from(files).forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                const item = {
                    id: Date.now() + Math.random(),
                    url: e.target.result,
                    width: parseFloat((img.naturalWidth / 300).toFixed(2)),
                    height: parseFloat((img.naturalHeight / 300).toFixed(2)),
                    qty: 1
                };
                appState.queue.push(item);
                updateQueueUI();
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
}

function updateQueueUI() {
    const list = document.getElementById('queue-list');
    const badge = document.getElementById('queue-badge');
    const count = appState.queue.reduce((sum, item) => sum + item.qty, 0);
    badge.innerText = count;
    badge.classList.toggle('hidden', count === 0);
    document.getElementById('queue-count').innerText = `${count} Items`;
    
    if(appState.queue.length > 0) {
        document.getElementById('gs-empty-state')?.remove();
        list.innerHTML = '';
        appState.queue.forEach((item, idx) => {
            const div = document.createElement('div');
            div.className = 'bg-slate-800 p-2 rounded border border-slate-700 flex gap-2 items-center fade-in mb-2';
            div.innerHTML = `
                <img src="${item.url}" class="w-10 h-10 object-contain bg-slate-900 rounded">
                <div class="flex-1 min-w-0">
                    <div class="text-[10px] text-slate-400">Size: ${item.width}" x ${item.height}"</div>
                    <input type="number" min="1" value="${item.qty}" class="bg-slate-900 text-white text-xs w-12 border border-slate-600 rounded text-center mt-1" onchange="updateQueueQty(${idx}, this.value)">
                </div>
                <button onclick="removeFromQueue(${idx})" class="text-slate-500 hover:text-red-400 px-2"><i class="fas fa-times"></i></button>
            `;
            list.appendChild(div);
        });
    } else {
        list.innerHTML = `
            <div id="gs-empty-state" class="text-center text-slate-600 text-xs mt-10 flex flex-col items-center gap-3">
                <p class="italic">Queue is empty.</p>
                <p class="text-[10px] text-slate-500 max-w-[180px]">Use Quick Add for print-ready files (300 DPI).</p>
        `;
    }
}

function updateQueueCount() {
    const count = appState.queue.reduce((sum, item) => sum + item.qty, 0);
    document.getElementById('queue-count').innerText = `${count} Items`;
}

window.updateQueueQty = (idx, val) => { 
    appState.queue[idx].qty = parseInt(val) || 1; 
    updateQueueUI(); 
};

window.removeFromQueue = (idx) => { 
    appState.queue.splice(idx, 1); 
    updateQueueUI(); 
};

// Editor Zoom
function updateEditorTransform() {
    document.getElementById('editor-pan-layer').style.transform = `scale(${appState.editor.zoom})`;
    document.getElementById('editor-zoom-display').innerText = Math.round(appState.editor.zoom * 100) + '%';
}

function zoomEditor(d) { 
    appState.editor.zoom = Math.max(0.1, appState.editor.zoom + d); 
    updateEditorTransform(); 
}

function resetEditorZoom() {
    const c = document.getElementById('editor-viewport');
    const i = appState.editor.img;
    if(i && i.naturalWidth > 0 && c.clientWidth > 0) { 
        const margin = 80; 
        const ratioW = (c.clientWidth - margin) / i.naturalWidth;
        const ratioH = (c.clientHeight - margin) / i.naturalHeight;
        appState.editor.zoom = Math.min(ratioW, ratioH, 1); 
        updateEditorTransform(); 
    }
}

// GS Zoom & Auto Center
function updateGSTransform() {
    document.getElementById('gs-pan-layer').style.transform = `translate(${appState.sheet.panX}px, ${appState.sheet.panY}px) scale(${appState.sheet.zoom})`;
    document.getElementById('gs-zoom-val').innerText = Math.round(appState.sheet.zoom*100) + '%';
}

function zoomGS(d) {
    const newZoom = Math.max(0.1, appState.sheet.zoom + d);
    appState.sheet.zoom = newZoom;
    if (!appState.sheet.manualPan) fitGS(); 
    else updateGSTransform();
}

// IMPROVED: True Center Logic with proper centering
function fitGS() {
    const vp = document.getElementById('gs-viewport');
    const sh = document.getElementById('gang-sheet');
    if(!vp || !sh || sh.offsetWidth === 0) return;
    
    // Calculate scale to fit viewport
    const scaleX = (vp.clientWidth - 40) / sh.offsetWidth;
    const scaleY = (vp.clientHeight - 40) / sh.offsetHeight;
    const scale = Math.min(scaleX, scaleY, 1.5);
    
    appState.sheet.zoom = scale;
    appState.sheet.manualPan = false;
    
    // Calculate centered position
    const scaledWidth = sh.offsetWidth * scale;
    const scaledHeight = sh.offsetHeight * scale;
    
    appState.sheet.panX = (vp.clientWidth - scaledWidth) / 2;
    appState.sheet.panY = (vp.clientHeight - scaledHeight) / 2;
    
    updateGSTransform();
}

// --- ENHANCED BIN PACKING ALGORITHM ---
window.autoNest = () => {
    if (appState.queue.length === 0) return;
    
    const container = document.getElementById('gang-sheet');
    container.innerHTML = '';
    
    // Expand Queue
    let items = [];
    appState.queue.forEach(d => { 
        for(let i = 0; i < d.qty; i++) {
            items.push({
                id: d.id + '_' + i,
                url: d.url,
                width: d.width,
                height: d.height,
                area: d.width * d.height,
                aspectRatio: d.width / d.height
            });
        }
    });
    
    // Enhanced sorting: by area, then by aspect ratio (more square first)
    items.sort((a, b) => {
        if (b.area !== a.area) return b.area - a.area;
        // Prefer more square items (aspect ratio closer to 1)
        const aSquareness = Math.min(a.aspectRatio, 1/a.aspectRatio);
        const bSquareness = Math.min(b.aspectRatio, 1/b.aspectRatio);
        return bSquareness - aSquareness;
    });
    
    const PPI = 20;
    const SHEET_W = appState.sheet.width * PPI;
    const PADDING = appState.sheet.tightPacking ? 0 : 2;
    const EDGE_H = appState.sheet.edgeSpacing.horizontal * PPI;
    const EDGE_V = appState.sheet.edgeSpacing.vertical * PPI;
    
    // Adjust effective width for roll media edge spacing
    const effectiveWidth = SHEET_W - (appState.sheet.isRollMedia ? EDGE_H * 2 : 0);
    
    // Initialize with single free rectangle
    let freeRects = [{ 
        x: appState.sheet.isRollMedia ? EDGE_H : 0, 
        y: appState.sheet.isRollMedia ? EDGE_V : 0, 
        width: effectiveWidth, 
        height: 999999 
    }];
    
    let placedItems = [];
    let maxY = appState.sheet.isRollMedia ? EDGE_V : 0;
    let totalItemArea = 0;
    
    // Calculate total area for efficiency calculation
    items.forEach(item => {
        totalItemArea += (item.width * PPI) * (item.height * PPI);
    });
    
    // Place each item with enhanced rotation strategies
    items.forEach(item => {
        const widthPx = item.width * PPI;
        const heightPx = item.height * PPI;
        
        // Find best position with multiple rotation strategies
        let bestPlacement = findBestPlacementEnhanced(freeRects, widthPx, heightPx, item);
        
        if (bestPlacement) {
            // Place the item
            const placedWidth = bestPlacement.rotated ? heightPx : widthPx;
            const placedHeight = bestPlacement.rotated ? widthPx : heightPx;
            
            placeItem(item, bestPlacement.x, bestPlacement.y, placedWidth, placedHeight, bestPlacement.rotated);
            
            // Update maxY for height calculation
            const itemBottom = bestPlacement.y + placedHeight;
            if (itemBottom > maxY) maxY = itemBottom;
            
            // Split the free rectangle
            splitAndPruneFreeRects(freeRects, {
                x: bestPlacement.x,
                y: bestPlacement.y,
                width: placedWidth + PADDING,
                height: placedHeight + PADDING
            });
            
            placedItems.push({
                item: item,
                x: bestPlacement.x,
                y: bestPlacement.y,
                width: placedWidth,
                height: placedHeight,
                rotated: bestPlacement.rotated
            });
        } else {
            console.warn("Could not place item", item);
        }
    });
    
    // Calculate final sheet height with edge spacing
    const totalH_pixels = maxY + (appState.sheet.isRollMedia ? EDGE_V : PPI * 0.5);
    if (document.getElementById('gs-length').value === 'auto') {
        appState.sheet.length = (totalH_pixels / PPI).toFixed(2);
        updateCanvasDim();
    }
    
    // Calculate packing efficiency
    const sheetArea = effectiveWidth * (totalH_pixels - (appState.sheet.isRollMedia ? EDGE_V : 0));
    const efficiency = sheetArea > 0 ? Math.round((totalItemArea / sheetArea) * 100) : 0;
    const wasted = 100 - efficiency;
    document.getElementById('packing-efficiency').innerText = efficiency + '%';
    document.getElementById('wasted-area').innerText = wasted + '%';
    
    // Update cost calculation
    updateCostCalc();
    appState.sheet.manualPan = false;
    
    // Apply tight packing CSS class
    if (appState.sheet.tightPacking) {
        container.classList.add('tight-packing');
    } else {
        container.classList.remove('tight-packing');
    }
    
    // Show edge spacing visualization for roll media
    visualizeEdgeSpacing();
    
    // Update grid overlay
    updateGridOverlay();
    
    // Re-center view
    setTimeout(fitGS, 50);
};

// Enhanced placement finder with adaptive rotation strategies
function findBestPlacementEnhanced(freeRects, width, height, item) {
    let bestRect = null;
    let bestScore = Infinity;
    let bestRotated = false;
    
    // Try multiple strategies based on item characteristics
    const strategies = [];
    
    // Strategy 1: Normal orientation
    strategies.push({ width: width, height: height, rotated: false });
    
    // Strategy 2: Rotated orientation (if allowed)
    if (appState.sheet.allowRotation && Math.abs(width - height) > 1) {
        strategies.push({ width: height, height: width, rotated: true });
    }
    
    // Strategy 3: Aggressive rotation for tall skinny items (if enabled)
    if (appState.sheet.aggressiveRotation && item.aspectRatio < 0.5) {
        strategies.push({ width: height, height: width, rotated: true, bonus: -50 });
    }
    
    // Strategy 4: Aggressive rotation for wide flat items (if enabled)
    if (appState.sheet.aggressiveRotation && item.aspectRatio > 2) {
        strategies.push({ width: height, height: width, rotated: true, bonus: -50 });
    }
    
    for (let strategy of strategies) {
        for (let rect of freeRects) {
            if (rect.width >= strategy.width && rect.height >= strategy.height) {
                // Enhanced scoring: favor placements that fill gaps
                const scoreY = rect.y * 1000; // Primary: minimize height
                const scoreX = rect.x;        // Secondary: minimize width
                const wastedSpace = (rect.width - strategy.width) + (rect.height - strategy.height);
                const fitsPerfectly = (rect.width === strategy.width || rect.height === strategy.height) ? -20 : 0;
                const rotationBonus = strategy.bonus || 0;
                const gapFillingBonus = (rect.width - strategy.width < 10 || rect.height - strategy.height < 10) ? -10 : 0;
                
                const score = scoreY + scoreX + wastedSpace + fitsPerfectly + rotationBonus + gapFillingBonus;
                
                if (score < bestScore) {
                    bestScore = score;
                    bestRect = rect;
                    bestRotated = strategy.rotated;
                }
            }
        }
    }
    
    return bestRect ? { x: bestRect.x, y: bestRect.y, rotated: bestRotated } : null;
}

// Efficient rectangle splitting with pruning
function splitAndPruneFreeRects(freeRects, usedRect) {
    const newRects = [];
    
    for (let rect of freeRects) {
        // Skip if no intersection
        if (usedRect.x >= rect.x + rect.width ||
            usedRect.x + usedRect.width <= rect.x ||
            usedRect.y >= rect.y + rect.height ||
            usedRect.y + usedRect.height <= rect.y) {
            newRects.push(rect);
            continue;
        }
        
        // Split into possible new rectangles
        // Left part
        if (usedRect.x > rect.x) {
            newRects.push({
                x: rect.x,
                y: rect.y,
                width: usedRect.x - rect.x,
                height: rect.height
            });
        }
        
        // Right part
        if (usedRect.x + usedRect.width < rect.x + rect.width) {
            newRects.push({
                x: usedRect.x + usedRect.width,
                y: rect.y,
                width: (rect.x + rect.width) - (usedRect.x + usedRect.width),
                height: rect.height
            });
        }
        
        // Bottom part
        if (usedRect.y + usedRect.height < rect.y + rect.height) {
            newRects.push({
                x: rect.x,
                y: usedRect.y + usedRect.height,
                width: rect.width,
                height: (rect.y + rect.height) - (usedRect.y + usedRect.height)
            });
        }
        
        // Top part
        if (usedRect.y > rect.y) {
            newRects.push({
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: usedRect.y - rect.y
            });
        }
    }
    
    // Prune redundant rectangles
    const prunedRects = pruneFreeRects(newRects);
    
    // Clear and update the array in place
    freeRects.length = 0;
    freeRects.push(...prunedRects);
}

// Prune rectangles that are fully contained within others
function pruneFreeRects(rects) {
    const result = [];
    
    for (let i = 0; i < rects.length; i++) {
        let contained = false;
        
        for (let j = 0; j < rects.length; j++) {
            if (i !== j && 
                rects[j].x <= rects[i].x &&
                rects[j].y <= rects[i].y &&
                rects[j].x + rects[j].width >= rects[i].x + rects[i].width &&
                rects[j].y + rects[j].height >= rects[i].y + rects[i].height) {
                contained = true;
                break;
            }
        }
        
        if (!contained) {
            result.push(rects[i]);
        }
    }
    
    return result;
}

// Place item on canvas with collision detection
function placeItem(item, x, y, width, height, rotated) {
    const container = document.getElementById('gang-sheet');
    const img = document.createElement('img');
    img.src = item.url;
    img.className = 'absolute object-contain hq-render sheet-item';
    img.dataset.id = item.id;
    
    if (rotated) {
        img.style.width = height + 'px';
        img.style.height = width + 'px';
        img.style.transform = 'rotate(90deg)';
        img.style.left = x + 'px';
        img.style.top = y + 'px';
        img.style.transformOrigin = 'center';
    } else {
        img.style.width = width + 'px';
        img.style.height = height + 'px';
        img.style.left = x + 'px';
        img.style.top = y + 'px';
        img.style.transform = 'none';
    }
    
    makeDraggable(img);
    
    // Double-click to rotate (if allowed)
    if (appState.sheet.allowRotation) {
        img.ondblclick = (e) => {
            e.stopPropagation();
            toggleImageRotation(img);
        };
    }
    
    // Right-click to remove
    img.oncontextmenu = (e) => {
        e.preventDefault();
        img.remove();
        updateCostCalc();
        checkAllOverlaps();
    };
    
    container.appendChild(img);
    
    // Check for overlaps after placement
    setTimeout(() => checkImageOverlaps(img), 10);
}

// Toggle image rotation with position adjustment
function toggleImageRotation(img) {
    const isRotated = img.style.transform.includes('rotate(90deg)');
    const currentWidth = parseFloat(img.style.width);
    const currentHeight = parseFloat(img.style.height);
    const currentLeft = parseFloat(img.style.left);
    const currentTop = parseFloat(img.style.top);
    
    if (isRotated) {
        // Rotate back to normal
        img.style.transform = 'rotate(0deg)';
        img.style.width = currentHeight + 'px';
        img.style.height = currentWidth + 'px';
        // Adjust position to keep center
        const dx = (currentWidth - currentHeight) / 2;
        img.style.left = (currentLeft - dx) + 'px';
        img.style.top = (currentTop + dx) + 'px';
    } else {
        // Rotate 90 degrees
        img.style.transform = 'rotate(90deg)';
        img.style.width = currentHeight + 'px';
        img.style.height = currentWidth + 'px';
        // Adjust position to keep center
        const dx = (currentHeight - currentWidth) / 2;
        img.style.left = (currentLeft + dx) + 'px';
        img.style.top = (currentTop - dx) + 'px';
    }
    img.style.transformOrigin = 'center';
    
    // Check for overlaps after rotation
    setTimeout(() => checkImageOverlaps(img), 10);
}

// Check if two rectangles overlap
function rectanglesOverlap(rect1, rect2) {
    return !(rect1.right <= rect2.left || 
            rect1.left >= rect2.right || 
            rect1.bottom <= rect2.top || 
            rect1.top >= rect2.bottom);
}

// Get rectangle from image element
function getImageRect(img) {
    const left = parseFloat(img.style.left) || 0;
    const top = parseFloat(img.style.top) || 0;
    const width = parseFloat(img.style.width) || 0;
    const height = parseFloat(img.style.height) || 0;
    
    return {
        left: left,
        top: top,
        right: left + width,
        bottom: top + height,
        width: width,
        height: height,
        element: img
    };
}

// Check for overlaps for a specific image
function checkImageOverlaps(img) {
    if (!appState.sheet.autoArrange) return;
    
    const rect1 = getImageRect(img);
    const allImages = Array.from(document.getElementById('gang-sheet').querySelectorAll('.sheet-item'));
    let hasOverlap = false;
    
    for (let otherImg of allImages) {
        if (otherImg === img) continue;
        
        const rect2 = getImageRect(otherImg);
        if (rectanglesOverlap(rect1, rect2)) {
            hasOverlap = true;
            break;
        }
    }
    
    if (hasOverlap) {
        img.classList.add('overlapping');
        // Auto-arrange if enabled
        if (appState.sheet.autoArrange) {
            autoArrangeOverlappingImage(img);
        }
    } else {
        img.classList.remove('overlapping');
    }
}

// Check all images for overlaps
function checkAllOverlaps() {
    const allImages = Array.from(document.getElementById('gang-sheet').querySelectorAll('.sheet-item'));
    allImages.forEach(img => checkImageOverlaps(img));
}

// Auto-arrange an overlapping image to nearest valid position
function autoArrangeOverlappingImage(img) {
    const container = document.getElementById('gang-sheet');
    const allImages = Array.from(container.querySelectorAll('.sheet-item'));
    const currentRect = getImageRect(img);
    
    // Try to find a nearby position that doesn't overlap
    const step = 10; // pixels
    const maxAttempts = 100;
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        // Try different positions in a spiral pattern
        const radius = Math.floor(Math.sqrt(attempt));
        const angle = attempt * 0.5;
        const dx = Math.cos(angle) * radius * step;
        const dy = Math.sin(angle) * radius * step;
        
        const newLeft = currentRect.left + dx;
        const newTop = currentRect.top + dy;
        
        // Check if new position is within bounds
        if (newLeft < 0 || newTop < 0) continue;
        if (newLeft + currentRect.width > parseFloat(container.style.width)) continue;
        
        // Check for overlaps at new position
        let overlaps = false;
        const testRect = {
            left: newLeft,
            top: newTop,
            right: newLeft + currentRect.width,
            bottom: newTop + currentRect.height
        };
        
        for (let otherImg of allImages) {
            if (otherImg === img) continue;
            const otherRect = getImageRect(otherImg);
            if (rectanglesOverlap(testRect, otherRect)) {
                overlaps = true;
                break;
            }
        }
        
        if (!overlaps) {
            // Found valid position
            img.style.left = newLeft + 'px';
            img.style.top = newTop + 'px';
            img.classList.remove('overlapping');
            return;
        }
    }
    
    // If no position found, move to bottom
    const maxY = Math.max(...allImages.filter(i => i !== img).map(i => getImageRect(i).bottom), 0);
    img.style.left = '0px';
    img.style.top = (maxY + 10) + 'px';
    img.classList.remove('overlapping');
}

// Detect and fix all overlaps
window.detectAndFixOverlaps = () => {
    const allImages = Array.from(document.getElementById('gang-sheet').querySelectorAll('.sheet-item'));
    let fixedCount = 0;
    
    // Sort by Y position (top to bottom)
    allImages.sort((a, b) => {
        const rectA = getImageRect(a);
        const rectB = getImageRect(b);
        return rectA.top - rectB.top;
    });
    
    // Check and fix each image
    for (let i = 0; i < allImages.length; i++) {
        const img = allImages[i];
        const rect = getImageRect(img);
        
        // Check against all other images
        for (let j = 0; j < allImages.length; j++) {
            if (i === j) continue;
            const otherImg = allImages[j];
            const otherRect = getImageRect(otherImg);
            
            if (rectanglesOverlap(rect, otherRect)) {
                // Move the lower image down
                if (rect.top >= otherRect.top) {
                    img.style.top = (otherRect.bottom + 5) + 'px';
                    fixedCount++;
                }
            }
        }
    }
    
    if (fixedCount > 0) {
        alert(`Fixed ${fixedCount} overlapping images`);
        updateCostCalc();
    } else {
        alert("No overlaps detected");
    }
};

// Improved makeDraggable function with overlap checking
function makeDraggable(el) {
    let isDragging = false;
    let startX, startY, initLeft, initTop;
    
    el.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return;
        e.stopPropagation();
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        initLeft = parseFloat(el.style.left) || 0;
        initTop = parseFloat(el.style.top) || 0;
        el.style.zIndex = 100;
        el.style.cursor = 'grabbing';
        appState.sheet.manualPan = true;
    });
    
    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        const dx = (e.clientX - startX) / appState.sheet.zoom;
        const dy = (e.clientY - startY) / appState.sheet.zoom;
        
        // Optional: Add boundary checking here
        const newLeft = initLeft + dx;
        const newTop = initTop + dy;
        
        // Basic boundary - prevent negative positions
        el.style.left = Math.max(0, newLeft) + 'px';
        el.style.top = Math.max(0, newTop) + 'px';
    });
    
    window.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            el.style.zIndex = '';
            el.style.cursor = 'grab';
            
            // Check for overlaps after dragging
            setTimeout(() => checkImageOverlaps(el), 10);
        }
    });
}

// Update edge spacing
window.updateEdgeSpacing = () => {
    const horizontal = parseFloat(document.getElementById('edge-horizontal').value) || 0.25;
    const vertical = parseFloat(document.getElementById('edge-vertical').value) || 0.5;
    
    appState.sheet.edgeSpacing = { horizontal, vertical };
    visualizeEdgeSpacing();
};

// Visualize edge spacing for roll media
function visualizeEdgeSpacing() {
    const container = document.getElementById('gang-sheet');
    const existingEdges = container.querySelectorAll('.edge-spacing');
    existingEdges.forEach(edge => edge.remove());
    
    if (!appState.sheet.isRollMedia || !appState.sheet.deadSpaceReduction) return;
    
    const PPI = 20;
    const edgeH = appState.sheet.edgeSpacing.horizontal * PPI;
    const edgeV = appState.sheet.edgeSpacing.vertical * PPI;
    const sheetWidth = appState.sheet.width * PPI;
    const sheetHeight = appState.sheet.length * PPI;
    
    // Create edge spacing visualization
    const edges = [
        // Left edge
        { x: 0, y: 0, width: edgeH, height: sheetHeight },
        // Right edge
        { x: sheetWidth - edgeH, y: 0, width: edgeH, height: sheetHeight },
        // Top edge
        { x: 0, y: 0, width: sheetWidth, height: edgeV },
        // Bottom edge
        { x: 0, y: sheetHeight - edgeV, width: sheetWidth, height: edgeV }
    ];
    
    edges.forEach(edge => {
        const div = document.createElement('div');
        div.className = 'edge-spacing';
        div.style.left = edge.x + 'px';
        div.style.top = edge.y + 'px';
        div.style.width = edge.width + 'px';
        div.style.height = edge.height + 'px';
        container.appendChild(div);
    });
}

// Update grid overlay
function updateGridOverlay() {
    const container = document.getElementById('gang-sheet');
    const existingGrid = container.querySelector('.packing-grid-overlay');
    if (existingGrid) existingGrid.remove();
    
    if (appState.sheet.showGrid) {
        const grid = document.createElement('div');
        grid.className = 'packing-grid-overlay';
        container.appendChild(grid);
    }
}

function updateCostCalc() {
    const costEl = document.getElementById('cost-input');
    if(!costEl) return; 
    appState.pricing.cost = parseFloat(costEl.value) || 0.025;
    
    // Calculate actual used area (excluding dead space for roll media)
    let usedArea = 0;
    const allImages = document.getElementById('gang-sheet').querySelectorAll('.sheet-item');
    allImages.forEach(img => {
        const width = parseFloat(img.style.width) / 20; // Convert px to inches
        const height = parseFloat(img.style.height) / 20;
        usedArea += width * height;
    });
    
    // For roll media: use actual sheet area (including mandatory edge spacing)
    const sheetArea = appState.sheet.width * appState.sheet.length;
    
    // Calculate cost based on actual sheet area (not used area)
    const prodCost = (sheetArea * appState.pricing.cost).toFixed(2);

    document.getElementById('total-height').innerText = appState.sheet.length + '"';
    document.getElementById('top-total-cost').innerText = '$' + prodCost;
    document.getElementById('total-price-top').innerText = '$' + prodCost; 
    
    // Calculate and display waste percentage
    if (sheetArea > 0) {
        const wastePercentage = Math.round(((sheetArea - usedArea) / sheetArea) * 100);
        document.getElementById('wasted-area').innerText = wastePercentage + '%';
    }
}

function updateCanvasDim() {
    const el = document.getElementById('gang-sheet');
    el.style.width = (appState.sheet.width * 20) + 'px';
    el.style.height = (appState.sheet.length * 20) + 'px';
    document.getElementById('badge-w').innerText = appState.sheet.width;
    document.getElementById('badge-h').innerText = document.getElementById('gs-length').value === 'auto' ? 'Auto' : appState.sheet.length;
    updateCostCalc();
    
    // Check if this is roll media
    const isRollMedia = !isNaN(parseFloat(appState.sheet.width)) && appState.sheet.width !== 11.7 && appState.sheet.width !== 13;
    appState.sheet.isRollMedia = isRollMedia;
    
    if (isRollMedia) {
        document.getElementById('roll-spacing-controls').classList.remove('hidden');
        document.getElementById('roll-indicator').classList.remove('hidden');
        visualizeEdgeSpacing();
    } else {
        document.getElementById('roll-spacing-controls').classList.add('hidden');
        document.getElementById('roll-indicator').classList.add('hidden');
        // Remove edge spacing visualization
        const existingEdges = el.querySelectorAll('.edge-spacing');
        existingEdges.forEach(edge => edge.remove());
    }
    
    // Auto-center after updating dimensions
    fitGS();
}

document.getElementById('gs-width').addEventListener('change', (e) => {
    const val = e.target.value;
    if(val.includes('|')) {
        const [w,h] = val.split('|').map(Number);
        appState.sheet.width = w; 
        appState.sheet.length = h;
        document.getElementById('gs-length').innerHTML = `<option>${h}" Fixed</option>`;
        document.getElementById('gs-length').disabled = true;
        appState.sheet.isRollMedia = false;
    } else {
        appState.sheet.width = Number(val);
        appState.sheet.length = 24; // Default length for rolls
        document.getElementById('gs-length').disabled = false;
        document.getElementById('gs-length').innerHTML = `<option value="auto">Auto-Calculate</option><option value="24">24"</option><option value="60">60"</option><option value="120">120"</option>`;
        appState.sheet.isRollMedia = true;
    }
    updateCanvasDim();
});

window.exportFile = async () => {
    if(appState.queue.length === 0) return alert("Empty.");
    const { jsPDF } = window.jspdf;
    
    // For roll media, crop to actual content bounds to reduce dead space
    if (appState.sheet.deadSpaceReduction && appState.sheet.isRollMedia) {
        const allImages = document.getElementById('gang-sheet').querySelectorAll('.sheet-item');
        if (allImages.length === 0) return alert("No images to export.");
        
        // Find actual bounds of content
        let minY = Infinity;
        let maxY = 0;
        
        allImages.forEach(img => {
            const top = parseFloat(img.style.top) / 20; // Convert px to inches
            const height = parseFloat(img.style.height) / 20;
            minY = Math.min(minY, top);
            maxY = Math.max(maxY, top + height);
        });
        
        // Add edge spacing to bounds
        minY = Math.max(0, minY - appState.sheet.edgeSpacing.vertical);
        maxY = maxY + appState.sheet.edgeSpacing.vertical;
        
        const contentHeight = maxY - minY;
        
        // Create PDF with cropped height
        const doc = new jsPDF({ 
            orientation: appState.sheet.width > contentHeight ? 'l' : 'p', 
            unit: 'in', 
            format: [appState.sheet.width, contentHeight] 
        });
        
        // Add all images to PDF with adjusted Y positions
        allImages.forEach(img => {
            const left = parseFloat(img.style.left) / 20;
            const top = (parseFloat(img.style.top) / 20) - minY; // Adjust for crop
            const width = parseFloat(img.style.width) / 20;
            const height = parseFloat(img.style.height) / 20;
            
            // Handle rotated images
            if (img.style.transform.includes('rotate(90deg)')) {
                doc.saveGraphicsState();
                doc.translate(left + width/2, top + height/2);
                doc.rotate(90 * Math.PI / 180);
                doc.addImage(img.src, 'PNG', -height/2, -width/2, height, width);
                doc.restoreGraphicsState();
            } else {
                doc.addImage(img.src, 'PNG', left, top, width, height);
            }
        });
        
        doc.save(`GangSheet_${appState.sheet.width}x${contentHeight.toFixed(2)}.pdf`);
    } else {
        // Original export logic for sheets
        const doc = new jsPDF({ 
            orientation: appState.sheet.width > appState.sheet.length ? 'l' : 'p', 
            unit: 'in', 
            format: [appState.sheet.width, appState.sheet.length] 
        });
        
        document.getElementById('gang-sheet').querySelectorAll('img').forEach(img => {
            const left = parseFloat(img.style.left) / 20;
            const top = parseFloat(img.style.top) / 20;
            const width = parseFloat(img.style.width) / 20;
            const height = parseFloat(img.style.height) / 20;
            
            if (img.style.transform.includes('rotate(90deg)')) {
                doc.saveGraphicsState();
                doc.translate(left + width/2, top + height/2);
                doc.rotate(90 * Math.PI / 180);
                doc.addImage(img.src, 'PNG', -height/2, -width/2, height, width);
                doc.restoreGraphicsState();
            } else {
                doc.addImage(img.src, 'PNG', left, top, width, height);
            }
        });
        
        doc.save(`GangSheet_${appState.sheet.width}x${appState.sheet.length}.pdf`);
    }
};

const gsVp = document.getElementById('gs-viewport');
let isPanning = false;
gsVp.addEventListener('wheel', e => { 
    e.preventDefault(); 
    zoomGS(-e.deltaY*0.001); 
});
gsVp.addEventListener('mousedown', (e) => {
    if (e.target.closest('.sheet-item')) return;
    isPanning = true;
    appState.sheet.manualPan = true; 
});
window.addEventListener('mouseup', () => isPanning = false);
window.addEventListener('mousemove', e => { 
    if(isPanning && !document.getElementById('view-gangsheet').classList.contains('hidden')) { 
        appState.sheet.panX += e.movementX; 
        appState.sheet.panY += e.movementY; 
        updateGSTransform(); 
    } 
});

document.addEventListener('DOMContentLoaded', init);
// Expose functions to global scope for inline HTML handlers
window.init = init;
window.loadEditorImage = loadEditorImage;
window.runTool = runTool;
window.editorUndo = editorUndo;
window.zoomEditor = zoomEditor;
window.resetEditorZoom = resetEditorZoom;
window.downloadCurrentImage = downloadCurrentImage;
window.addToGangSheet = addToGangSheet;
window.handleDirectUpload = handleDirectUpload;
window.autoNest = autoNest;
window.detectAndFixOverlaps = detectAndFixOverlaps;
window.exportFile = exportFile;