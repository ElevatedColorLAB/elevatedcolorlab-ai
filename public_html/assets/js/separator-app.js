// Pro Separation Lab v3.0 - Main Application
// Professional screen print color separation tool

const API_PROXY = 'api-proxy.php';
const API_SERVICE = 'main_app'; // Maps to port 8000 (separator.py)

let state = {
    img: null,
    originalBase64: null,
    currentBase64: null,
    channels: [],
    zoom: 1,
    pan: { x: 0, y: 0 },
    isDragging: false,
    lastMouse: { x: 0, y: 0 },
    fileName: 'image',
    selectedChannels: new Set(),
    currentTool: 'pan',
    manualColors: [],
    adjustments: {
        brightness: 0,
        contrast: 0,
        hue: 0,
        saturation: 0,
        lightness: 0,
        gamma: 1.0,
        input_black: 0,
        input_white: 255
    }
};

const dom = {
    fileInput: document.getElementById('fileElem'),
    canvas: document.getElementById('main-canvas'),
    channelsList: document.getElementById('channels-list'),
    channelsWindow: document.getElementById('channels-window'),
    status: document.getElementById('service-status'),
    loader: document.getElementById('global-loader'),
    loaderMsg: document.getElementById('loader-msg'),
    dropArea: document.getElementById('drop-area'),
    msgModal: document.getElementById('msg-modal'),
    msgText: document.getElementById('msg-text'),
    msgTitle: document.getElementById('msg-title'),
    msgIcon: document.getElementById('msg-icon'),
    cursorPos: document.getElementById('cursor-position'),
    zoomLevel: document.getElementById('zoom-level'),
    imageDims: document.getElementById('image-dimensions'),
    colorInfo: document.getElementById('color-info'),
    gridOverlay: document.getElementById('grid-overlay'),
    histogramCanvas: document.getElementById('histogram-canvas')
};

const ctx = dom.canvas.getContext('2d');

// ============ CORE FUNCTIONS ============

function showMessage(msg, type = 'info', title = 'Message') {
    dom.msgText.textContent = msg;
    dom.msgTitle.textContent = title;
    
    const iconMap = {
        'info': { icon: 'fa-info-circle', color: 'text-violet-400' },
        'success': { icon: 'fa-check-circle', color: 'text-green-400' },
        'error': { icon: 'fa-exclamation-circle', color: 'text-red-400' },
        'warning': { icon: 'fa-exclamation-triangle', color: 'text-yellow-400' }
    };
    
    const iconData = iconMap[type] || iconMap['info'];
    dom.msgIcon.className = `fas ${iconData.icon} text-3xl ${iconData.color}`;
    
    dom.msgModal.classList.add('show');
}

function closeModal() {
    dom.msgModal.classList.remove('show');
}

function showLoader(msg = 'Processing...') {
    dom.loaderMsg.textContent = msg;
    dom.loader.classList.remove('hidden');
}

function hideLoader() {
    dom.loader.classList.add('hidden');
}

async function apiCall(endpoint, body) {
    try {
        const formData = new FormData();
        formData.append('service', API_SERVICE);
        formData.append('endpoint', endpoint);
        formData.append('method', 'POST');
        formData.append('payload', JSON.stringify(body));
        
        const res = await fetch(API_PROXY, {
            method: 'POST',
            body: formData
        });
        
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.error || `Server Error: ${res.status}`);
        }
        
        return await res.json();
    } catch (e) {
        console.error(e);
        throw e;
    }
}

async function checkHealth() {
    try {
        const data = await apiCall('/health', {});
        
        dom.status.innerHTML = '<span class="status-indicator bg-green-500"></span>Online';
        dom.status.className = "text-sm text-green-400 flex items-center";
        
        if (data.pantone_loaded) {
            console.log('✓ Pantone library loaded');
        }
    } catch (e) {
        dom.status.innerHTML = '<span class="status-indicator bg-red-500"></span>Offline';
        console.error('Service offline:', e);
    }
}

function loadFile(file) {
    if (!file || !file.type.startsWith('image/')) {
        showMessage('Please select a valid image file.', 'error', 'Invalid File');
        return;
    }
    
    state.fileName = file.name.replace(/\.[^/.]+$/, '');
    
    const reader = new FileReader();
    reader.onload = (e) => {
        state.originalBase64 = e.target.result;
        state.currentBase64 = e.target.result;
        
        const img = new Image();
        img.onload = () => {
            state.img = img;
            state.pan = { x: 0, y: 0 };
            
            const parent = dom.canvas.parentElement;
            state.zoom = Math.min(
                parent.clientWidth / img.width,
                parent.clientHeight / img.height
            ) * 0.85;
            
            renderCanvas();
            enableButtons();
            updateHistogram();
            
            document.getElementById('placeholder-text').classList.add('hidden');
            document.getElementById('image-info').textContent = `${img.width}×${img.height}px • ${file.size > 1000000 ? (file.size/1000000).toFixed(1) + 'MB' : (file.size/1000).toFixed(0) + 'KB'}`;
            dom.imageDims.innerHTML = `<i class="fas fa-ruler-combined mr-2 text-violet-400"></i>${img.width}×${img.height}`;
            
            updateZoomDisplay();
            showMessage('Image loaded successfully!', 'success', 'Success');
        };
        img.src = state.currentBase64;
    };
    reader.readAsDataURL(file);
}

function renderCanvas() {
    if (!state.img) return;
    
    const container = dom.canvas.parentElement;
    dom.canvas.width = container.clientWidth;
    dom.canvas.height = container.clientHeight;
    dom.canvas.classList.remove('hidden');
    
    ctx.clearRect(0, 0, dom.canvas.width, dom.canvas.height);
    ctx.save();
    
    ctx.translate(dom.canvas.width/2 + state.pan.x, dom.canvas.height/2 + state.pan.y);
    ctx.scale(state.zoom, state.zoom);
    ctx.drawImage(state.img, -state.img.width/2, -state.img.height/2);
    
    if (document.getElementById('chk-composite-view')?.checked && state.channels.length > 0) {
        drawCompositePreview();
    }
    
    ctx.restore();
}

function drawCompositePreview() {
    ctx.globalAlpha = 0.7;
    state.channels.forEach((ch, i) => {
        if (state.selectedChannels.has(i) && ch.printable) {
            // Composite rendering placeholder
        }
    });
    ctx.globalAlpha = 1.0;
}

function enableButtons() {
    const btnIds = [
        'btn-process', 'btn-apply-adjustments', 'btn-reset-adjustments',
        'btn-export-all', 'btn-production-proof', 'btn-add-color'
    ];
    btnIds.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled = false;
    });
}

function getRawBase64(dataUrl) {
    return dataUrl.split(',')[1];
}

function updateImage(b64) {
    state.currentBase64 = 'data:image/png;base64,' + b64;
    const i = new Image();
    i.onload = () => { 
        state.img = i; 
        renderCanvas();
        updateHistogram();
    };
    i.src = state.currentBase64;
}

function updateZoomDisplay() {
    const zoomPercent = Math.round(state.zoom * 100);
    dom.zoomLevel.innerHTML = `<i class="fas fa-search mr-2 text-violet-400"></i>Zoom: ${zoomPercent}%`;
}

function updateHistogram() {
    if (!state.img) return;
    
    const canvas = dom.histogramCanvas;
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = 60;
    
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.strokeStyle = '#8b5cf6';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i < canvas.width; i++) {
        const height = Math.random() * canvas.height;
        if (i === 0) ctx.moveTo(i, canvas.height - height);
        else ctx.lineTo(i, canvas.height - height);
    }
    ctx.stroke();
}

// ============ CHANNEL FUNCTIONS ============

function selectAllChannels() {
    state.channels.forEach((_, i) => state.selectedChannels.add(i));
    updateChannelsDisplay();
    renderCanvas();
}

function deselectAllChannels() {
    state.selectedChannels.clear();
    updateChannelsDisplay();
    renderCanvas();
}

function updateChannelsDisplay() {
    document.querySelectorAll('.channel-row').forEach((row, i) => {
        if (state.selectedChannels.has(i)) {
            row.classList.add('active');
        } else {
            row.classList.remove('active');
        }
    });
}

function selectChannel(index, multiSelect = false) {
    if (!multiSelect) {
        state.selectedChannels.clear();
    }
    
    if (state.selectedChannels.has(index)) {
        state.selectedChannels.delete(index);
    } else {
        state.selectedChannels.add(index);
    }
    
    updateChannelsDisplay();
    updateChannelInfo(index);
    renderCanvas();
}

function updateChannelInfo(index) {
    if (index >= 0 && index < state.channels.length) {
        const ch = state.channels[index];
        document.getElementById('selected-channel-name').textContent = ch.name;
        document.getElementById('channel-coverage').textContent = ch.coverage_percent.toFixed(1) + '%';
        document.getElementById('channel-ink-volume').textContent = (ch.coverage_percent * ch.ink_volume / 100).toFixed(1) + 'ml';
    }
}

function toggleChannelVisibility(event, index) {
    event.stopPropagation();
    const icon = event.currentTarget;
    icon.classList.toggle('visible');
    
    if (state.selectedChannels.has(index)) {
        state.selectedChannels.delete(index);
    } else {
        state.selectedChannels.add(index);
    }
    
    updateChannelsDisplay();
    renderCanvas();
}

function viewChannelSolo(index) {
    state.selectedChannels.clear();
    state.selectedChannels.add(index);
    updateChannelsDisplay();
    updateChannelInfo(index);
    renderCanvas();
}

function renderChannelsPanel() {
    dom.channelsList.innerHTML = '';
    
    if (state.channels.length === 0) {
        dom.channelsList.innerHTML = `
            <div class="text-center text-slate-500 py-8 text-sm">
                <i class="fas fa-info-circle text-2xl mb-2"></i>
                <p>No channels yet</p>
            </div>
        `;
        return;
    }
    
    state.channels.forEach((ch, i) => {
        const div = document.createElement('div');
        div.className = 'channel-row' + (state.selectedChannels.has(i) ? ' active' : '');
        
        div.innerHTML = `
            <div class="channel-eye ${state.selectedChannels.has(i) ? 'visible' : ''}" onclick="toggleChannelVisibility(event, ${i})">
                <i class="fas ${state.selectedChannels.has(i) ? 'fa-eye' : 'fa-eye-slash'}"></i>
            </div>
            <img src="${ch.image}" class="channel-thumb" onclick="viewChannelSolo(${i})" alt="${ch.name}">
            <div class="flex-1">
                <div class="channel-name">${ch.name}${ch.pantone ? ' (PMS)' : ''}</div>
                <div class="channel-info">${ch.coverage_percent.toFixed(1)}% coverage</div>
            </div>
            <div class="flex items-center space-x-2">
                <div class="channel-hex" style="background-color: ${ch.color}" title="${ch.color}"></div>
                <i class="fas ${ch.locked ? 'fa-lock' : 'fa-lock-open'} text-slate-500 cursor-pointer hover:text-white text-xs" title="${ch.locked ? 'Locked' : 'Unlocked'}"></i>
            </div>
        `;
        
        div.onclick = (e) => {
            if (e.target.closest('.channel-eye') || e.target.closest('.channel-thumb') || e.target.closest('i.fa-lock')) return;
            selectChannel(i, e.ctrlKey || e.metaKey);
        };
        
        dom.channelsList.appendChild(div);
    });
}

// ============ COLOR PICKER FUNCTIONS ============

function closeColorPicker() {
    document.getElementById('color-picker-modal').classList.remove('show');
}

function addCustomColor() {
    const hexInput = document.getElementById('color-hex-input');
    const colorInput = document.getElementById('color-picker-input');
    const hex = hexInput.value || colorInput.value;
    
    if (hex && /^#[0-9A-F]{6}$/i.test(hex)) {
        state.manualColors.push(hex);
        renderManualColors();
        closeColorPicker();
    } else {
        showMessage('Please enter a valid hex color code', 'error', 'Invalid Color');
    }
}

function renderManualColors() {
    const list = document.getElementById('manual-colors-list');
    list.innerHTML = '';
    
    state.manualColors.forEach((hex, i) => {
        const div = document.createElement('div');
        div.className = 'relative group';
        div.innerHTML = `
            <div class="w-12 h-12 rounded border-2 border-slate-600 cursor-pointer hover:border-violet-500 transition" style="background-color: ${hex}" title="${hex}"></div>
            <button onclick="removeManualColor(${i})" class="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs opacity-0 group-hover:opacity-100 transition">×</button>
        `;
        list.appendChild(div);
    });
}

function removeManualColor(index) {
    state.manualColors.splice(index, 1);
    renderManualColors();
}

// ============ EVENT HANDLERS ============

function initializeEventListeners() {
    // File Input
    dom.dropArea.onclick = () => dom.fileInput.click();
    dom.fileInput.onchange = (e) => {
        if (e.target.files.length > 0) {
            loadFile(e.target.files[0]);
        }
    };
    
    // Drag & Drop
    dom.dropArea.ondragover = (e) => { 
        e.preventDefault(); 
        dom.dropArea.classList.add('drag-over'); 
    };
    dom.dropArea.ondragleave = () => dom.dropArea.classList.remove('drag-over');
    dom.dropArea.ondrop = (e) => {
        e.preventDefault();
        dom.dropArea.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            loadFile(e.dataTransfer.files[0]);
        }
    };

    // Canvas Interaction
    dom.canvas.onmousedown = (e) => { 
        state.isDragging = true; 
        state.lastMouse = { x: e.clientX, y: e.clientY }; 
        dom.canvas.style.cursor = 'grabbing';
    };
    
    dom.canvas.onmousemove = (e) => {
        if (!state.img) return;
        
        const rect = dom.canvas.getBoundingClientRect();
        const x = Math.round((e.clientX - rect.left - dom.canvas.width/2 - state.pan.x) / state.zoom);
        const y = Math.round((e.clientY - rect.top - dom.canvas.height/2 - state.pan.y) / state.zoom);
        dom.cursorPos.innerHTML = `<i class="fas fa-crosshairs mr-2 text-violet-400"></i>X: ${x}, Y: ${y}`;
        
        if (state.isDragging) {
            state.pan.x += e.clientX - state.lastMouse.x;
            state.pan.y += e.clientY - state.lastMouse.y;
            state.lastMouse = { x: e.clientX, y: e.clientY };
            renderCanvas();
        }
    };
    
    window.onmouseup = () => { 
        state.isDragging = false; 
        dom.canvas.style.cursor = 'grab';
    };
    
    dom.canvas.onwheel = (e) => {
        e.preventDefault();
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        state.zoom *= zoomFactor;
        state.zoom = Math.max(0.1, Math.min(state.zoom, 10));
        renderCanvas();
        updateZoomDisplay();
    };

    // Color Adjustment Sliders
    const adjustmentInputs = ['brightness', 'contrast', 'hue', 'saturation', 'gamma', 'input-black', 'input-white'];
    adjustmentInputs.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.oninput = (e) => {
                const displayId = `${id}-val`;
                const display = document.getElementById(displayId);
                if (display) {
                    let value = e.target.value;
                    if (id === 'hue') value += '°';
                    display.textContent = value;
                }
                
                const key = id.replace('-', '_');
                state.adjustments[key] = parseFloat(e.target.value);
            };
        }
    });

    document.getElementById('color-slider').oninput = (e) => {
        document.getElementById('color-val').textContent = e.target.value;
    };

    // Color Selection Mode
    document.querySelectorAll('input[name="color-sel"]').forEach(radio => {
        radio.onchange = (e) => {
            const mode = e.target.value;
            const manualSection = document.getElementById('manual-colors-section');
            
            if (mode === 'manual') {
                manualSection.classList.remove('hidden');
            } else {
                manualSection.classList.add('hidden');
            }
        };
    });

    // Manual Color Picker
    document.getElementById('btn-add-color').onclick = () => {
        document.getElementById('color-picker-modal').classList.add('show');
    };

    // Apply/Reset Adjustments
    document.getElementById('btn-apply-adjustments').onclick = async () => {
        if (!state.currentBase64) return;
        
        showLoader('Applying color adjustments...');
        try {
            const result = await apiCall('/adjust-colors', {
                image_base64: getRawBase64(state.currentBase64),
                adjustments: state.adjustments
            });
            
            if (result.adjusted_image) {
                updateImage(getRawBase64(result.adjusted_image));
                showMessage('Color adjustments applied successfully!', 'success', 'Success');
            }
        } catch (e) {
            showMessage('Failed to apply adjustments: ' + e.message, 'error', 'Error');
        } finally {
            hideLoader();
        }
    };

    document.getElementById('btn-reset-adjustments').onclick = () => {
        state.adjustments = {
            brightness: 0,
            contrast: 0,
            hue: 0,
            saturation: 0,
            lightness: 0,
            gamma: 1.0,
            input_black: 0,
            input_white: 255
        };
        
        document.getElementById('brightness').value = 0;
        document.getElementById('contrast').value = 0;
        document.getElementById('hue').value = 0;
        document.getElementById('saturation').value = 0;
        document.getElementById('gamma').value = 1.0;
        document.getElementById('input-black').value = 0;
        document.getElementById('input-white').value = 255;
        
        document.getElementById('brightness-val').textContent = '0';
        document.getElementById('contrast-val').textContent = '0';
        document.getElementById('hue-val').textContent = '0°';
        document.getElementById('saturation-val').textContent = '0';
        document.getElementById('gamma-val').textContent = '1.0';
        
        if (state.originalBase64) {
            state.currentBase64 = state.originalBase64;
            const img = new Image();
            img.onload = () => {
                state.img = img;
                renderCanvas();
                updateHistogram();
            };
            img.src = state.currentBase64;
        }
        
        showMessage('Adjustments reset to defaults', 'info', 'Reset');
    };

    // Process Separations
    document.getElementById('btn-process').onclick = async () => {
        if (!state.currentBase64) return;
        
        const colorSelMode = document.querySelector('input[name="color-sel"]:checked').value;
        const method = document.getElementById('sep-method').value;
        const maxColors = parseInt(document.getElementById('color-slider').value);
        const useUnderbase = document.getElementById('chk-underbase').checked;
        const useHighlight = document.getElementById('chk-highlight').checked;
        const chokeSpread = parseFloat(document.getElementById('choke-spread').value);
        const minDot = parseInt(document.getElementById('min-dot').value);
        const softness = parseFloat(document.getElementById('softness').value);
        const matchPantone = colorSelMode === 'pantone';
        const customColors = colorSelMode === 'manual' ? state.manualColors : null;
        
        showLoader('Processing separations...');
        
        try {
            const result = await apiCall('/process', {
                image_base64: getRawBase64(state.currentBase64),
                separation_method: method,
                max_colors: maxColors,
                use_underbase: useUnderbase,
                use_highlight_white: useHighlight,
                softness: softness,
                choke_spread: chokeSpread,
                min_dot: minDot,
                match_pantone: matchPantone,
                custom_colors: customColors,
                color_adjustment: state.adjustments
            });
            
            if (result.channels) {
                state.channels = result.channels;
                state.selectedChannels = new Set([...Array(result.channels.length).keys()]);
                renderChannelsPanel();
                dom.channelsWindow.classList.remove('hidden');
                
                showMessage(
                    `Separation complete! ${result.channels.length} channels created. Quality score: ${result.separation_quality}/100`,
                    'success',
                    'Success'
                );
            }
        } catch (e) {
            showMessage('Separation failed: ' + e.message, 'error', 'Error');
        } finally {
            hideLoader();
        }
    };

    // Toolbar Actions
    document.getElementById('tool-fit').onclick = () => {
        if (!state.img) return;
        const parent = dom.canvas.parentElement;
        state.zoom = Math.min(
            parent.clientWidth / state.img.width, 
            parent.clientHeight / state.img.height
        ) * 0.85;
        state.pan = { x: 0, y: 0 };
        renderCanvas();
        updateZoomDisplay();
    };
    
    document.getElementById('tool-zoom-in').onclick = () => { 
        state.zoom *= 1.2; 
        state.zoom = Math.min(state.zoom, 10);
        renderCanvas(); 
        updateZoomDisplay();
    };
    
    document.getElementById('tool-zoom-out').onclick = () => { 
        state.zoom /= 1.2;
        state.zoom = Math.max(state.zoom, 0.1);
        renderCanvas(); 
        updateZoomDisplay();
    };

    document.getElementById('tool-grid').onclick = () => {
        dom.gridOverlay.classList.toggle('hidden');
    };

    document.getElementById('tool-color-picker').onclick = () => {
        if (!state.img) return;
        showMessage('Click on the canvas to pick a color', 'info', 'Color Picker');
        state.currentTool = 'color-picker';
        dom.canvas.style.cursor = 'crosshair';
    };

    document.getElementById('btn-toggle-channels').onclick = () => {
        dom.channelsWindow.classList.toggle('hidden');
    };

    // Export Functions
    document.getElementById('btn-export-all').onclick = () => {
        if (state.channels.length === 0) {
            showMessage('No channels to export. Process an image first.', 'warning', 'No Channels');
            return;
        }
        
        state.channels.forEach((ch, i) => {
            const link = document.createElement('a');
            link.href = ch.image;
            link.download = `${state.fileName}_${ch.name.replace(/\s+/g, '_')}.png`;
            link.click();
        });
        
        showMessage(`Exported ${state.channels.length} channels successfully!`, 'success', 'Export Complete');
    };

    document.getElementById('btn-production-proof').onclick = () => {
        if (state.channels.length === 0) {
            showMessage('No channels to export. Process an image first.', 'warning', 'No Channels');
            return;
        }
        
        showMessage('Production proof export coming soon!', 'info', 'Coming Soon');
    };

    // View Toggles
    document.getElementById('chk-composite-view')?.addEventListener('change', () => {
        renderCanvas();
    });

    document.getElementById('chk-solo-mode')?.addEventListener('change', (e) => {
        if (e.target.checked && state.selectedChannels.size > 0) {
            const firstSelected = Array.from(state.selectedChannels)[0];
            state.selectedChannels.clear();
            state.selectedChannels.add(firstSelected);
            updateChannelsDisplay();
            renderCanvas();
        }
    });

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
            e.preventDefault();
            document.getElementById('btn-reset-adjustments').click();
        }
        
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            document.getElementById('btn-export-all').click();
        }
        
        if (e.key === ' ' && state.img) {
            e.preventDefault();
            document.getElementById('tool-fit').click();
        }
        
        if (e.key === '+' || e.key === '=') {
            e.preventDefault();
            document.getElementById('tool-zoom-in').click();
        }
        if (e.key === '-') {
            e.preventDefault();
            document.getElementById('tool-zoom-out').click();
        }
        
        if (e.key === 'g') {
            e.preventDefault();
            document.getElementById('tool-grid').click();
        }
        
        if (e.key === 'Escape') {
            closeModal();
            closeColorPicker();
        }
    });

    // Window Resize
    window.addEventListener('resize', () => {
        if (state.img) {
            renderCanvas();
        }
    });
}

// ============ INITIALIZATION ============

function initialize() {
    console.log('%c Pro Separation Lab v3.0 ', 'background: #8b5cf6; color: white; font-size: 16px; padding: 8px; border-radius: 4px;');
    console.log('🎨 Features: Color Adjustments, Pantone Matching, Manual Selection, Simulated Process');
    console.log('⌨️  Shortcuts: Ctrl+Z (Reset), Ctrl+S (Export), Space (Fit), +/- (Zoom), G (Grid), Esc (Close)');
    
    initializeEventListeners();
    checkHealth();
    setInterval(checkHealth, 30000);
}

// Make functions globally accessible
window.selectAllChannels = selectAllChannels;
window.deselectAllChannels = deselectAllChannels;
window.toggleChannelVisibility = toggleChannelVisibility;
window.viewChannelSolo = viewChannelSolo;
window.closeModal = closeModal;
window.closeColorPicker = closeColorPicker;
window.addCustomColor = addCustomColor;
window.removeManualColor = removeManualColor;

// Start the app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}