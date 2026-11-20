// ZaloTask Assistant Frontend Logic - Pro Edition
let soundEnabled = true;
let audioCtx = null;
let currentPreviewCountdown = 0;
let previewTimer = null;
let activePreviewTaskId = null;

// Khởi tạo âm thanh bằng Web Audio API Synthesizer (chuông ngân trong trẻo)
function playChimeSound() {
    if (!soundEnabled) return;
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        
        const now = audioCtx.currentTime;
        // Nốt 1: E5 (659.25Hz)
        const osc1 = audioCtx.createOscillator();
        const gain1 = audioCtx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(659.25, now);
        gain1.gain.setValueAtTime(0.25, now);
        gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
        osc1.connect(gain1);
        gain1.connect(audioCtx.destination);
        osc1.start(now);
        osc1.stop(now + 0.6);

        // Nốt 2: G#5 (830.61Hz)
        const osc2 = audioCtx.createOscillator();
        const gain2 = audioCtx.createGain();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(830.61, now + 0.15);
        gain2.gain.setValueAtTime(0.3, now + 0.15);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.9);
        osc2.connect(gain2);
        gain2.connect(audioCtx.destination);
        osc2.start(now + 0.15);
        osc2.stop(now + 0.9);

        // Nốt 3: B5 (987.77Hz)
        const osc3 = audioCtx.createOscillator();
        const gain3 = audioCtx.createGain();
        osc3.type = 'sine';
        osc3.frequency.setValueAtTime(987.77, now + 0.3);
        gain3.gain.setValueAtTime(0.35, now + 0.3);
        gain3.gain.exponentialRampToValueAtTime(0.001, now + 1.2);
        osc3.connect(gain3);
        gain3.connect(audioCtx.destination);
        osc3.start(now + 0.3);
        osc3.stop(now + 1.2);
    } catch (e) {
        console.warn("Không thể phát chuông âm thanh:", e);
    }
}

// Yêu cầu quyền thông báo của trình duyệt
if ("Notification" in window && Notification.permission !== "granted") {
    Notification.requestPermission();
}

function showBrowserNotification(title, body) {
    if ("Notification" in window && Notification.permission === "granted") {
        new Notification(title, {
            body: body,
            icon: "/static/icon.png"
        });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Clock
    setInterval(updateClock, 1000);
    updateClock();

    // Sound toggle
    const soundBtn = document.getElementById("sound-toggle-btn");
    soundBtn.addEventListener("click", () => {
        soundEnabled = !soundEnabled;
        document.getElementById("sound-status-text").textContent = soundEnabled ? "Bật" : "Tắt";
        document.getElementById("sound-icon").textContent = soundEnabled ? "🔊" : "🔇";
        if (soundEnabled) playChimeSound();
    });

    // Unified Tabs & Mobile Bottom Navigation
    window.switchTab = function(target) {
        document.querySelectorAll(".tab-btn").forEach(b => {
            b.classList.toggle("active", b.dataset.tab === target);
        });
        document.querySelectorAll(".bottom-nav-item").forEach(b => {
            b.classList.toggle("active", b.dataset.tab === target);
        });
        document.querySelectorAll(".tab-content").forEach(c => {
            c.classList.toggle("active", c.id === target);
        });

        if (target === "tab-logs") loadLogs();
        if (target === "tab-settings") loadSettings();
        if (target === "tab-ai-chat") {
            const input = document.getElementById("chat-input-text");
            if (input) input.focus();
        }
    };

    document.querySelectorAll(".tab-btn, .bottom-nav-item").forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.tab;
            if (target) switchTab(target);
        });
    });

    // Form conditional logic
    const scheduleTypeSelect = document.getElementById("form-schedule-type");
    scheduleTypeSelect.addEventListener("change", handleScheduleTypeChange);

    const actionTypeSelect = document.getElementById("form-action-type");
    actionTypeSelect.addEventListener("change", () => {
        const val = actionTypeSelect.value;
        const zaloBlock = document.getElementById("zalo-options-block");
        zaloBlock.style.opacity = (val === "alert_only") ? "0.5" : "1";
    });

    // File source mode radio (Modal)
    document.querySelectorAll("input[name='form-file-mode']").forEach(radio => {
        radio.addEventListener("change", (e) => {
            const isDir = (e.target.value === "directory");
            document.getElementById("form-file-fixed-block").style.display = isDir ? "none" : "block";
            document.getElementById("form-file-dir-block").style.display = isDir ? "block" : "none";
        });
    });

    // File source mode radio (Quick Test)
    document.querySelectorAll("input[name='test-file-mode']").forEach(radio => {
        radio.addEventListener("change", (e) => {
            const isDir = (e.target.value === "directory");
            document.getElementById("test-file-upload-block").style.display = isDir ? "none" : "block";
            document.getElementById("test-file-dir-block").style.display = isDir ? "block" : "none";
        });
    });

    // Browse Directory Buttons
    document.getElementById("btn-browse-form-dir").addEventListener("click", () => {
        checkDirectory(
            document.getElementById("form-watch-dir").value,
            document.getElementById("form-file-pattern").value,
            "form-dir-preview"
        );
    });

    document.getElementById("btn-browse-test-dir").addEventListener("click", () => {
        checkDirectory(
            document.getElementById("test-dir-path").value,
            "*.*",
            "test-dir-preview"
        );
    });

    // Modal events
    document.getElementById("open-create-modal-btn").addEventListener("click", () => openModal());
    document.getElementById("modal-close-btn").addEventListener("click", () => closeModal());
    document.getElementById("modal-cancel-btn").addEventListener("click", () => closeModal());

    // Submit forms
    document.getElementById("task-form").addEventListener("submit", handleSaveTask);
    document.getElementById("quick-test-form").addEventListener("submit", handleQuickTest);

    // Refresh logs btn
    document.getElementById("btn-refresh-logs").addEventListener("click", loadLogs);

    // Dismiss alert banner
    document.getElementById("btn-dismiss-alert").addEventListener("click", () => {
        document.getElementById("due-alert-banner").style.display = "none";
    });

    // Settings & Telegram
    document.getElementById("btn-save-settings").addEventListener("click", saveSettings);
    document.getElementById("btn-test-telegram").addEventListener("click", testTelegram);

    // Smart Preview Modal Buttons
    document.getElementById("btn-preview-send-now").addEventListener("click", confirmPreviewNow);
    document.getElementById("btn-preview-postpone").addEventListener("click", postponePreview);

    // Polling
    loadSystemStatus();
    loadTasks();
    loadLogs();
    loadSettings();
    initAIChat();

    setInterval(checkAlerts, 3000);
    setInterval(loadSystemStatus, 10000);
});

function updateClock() {
    const now = new Date();
    const str = now.toLocaleTimeString('vi-VN', { hour12: false });
    document.getElementById("clock-display").textContent = str;
}

async function loadSystemStatus() {
    try {
        const res = await fetch("/api/system-status");
        const data = await res.json();
        
        const zaloDot = document.getElementById("zalo-dot");
        const zaloText = document.getElementById("zalo-status-text");
        if (data.zalo_desktop_running) {
            zaloDot.className = "dot green";
            zaloText.textContent = "Đã sẵn sàng";
        } else {
            zaloDot.className = "dot red";
            zaloText.textContent = "Chưa mở";
        }
    } catch (e) {
        console.error("Lỗi lấy trạng thái hệ thống:", e);
    }
}

async function loadTasks() {
    try {
        const res = await fetch("/api/tasks");
        const data = await res.json();
        renderTasks(data.tasks || []);
        updateStats(data.tasks || []);
    } catch (e) {
        console.error("Lỗi tải danh sách tác vụ:", e);
    }
}

function updateStats(tasks) {
    document.getElementById("stat-total").textContent = tasks.length;
    const active = tasks.filter(t => t.is_active).length;
    document.getElementById("stat-active").textContent = active;

    const nextTasks = tasks
        .filter(t => t.is_active && t.next_run)
        .sort((a, b) => new Date(a.next_run) - new Date(b.next_run));

    if (nextTasks.length > 0) {
        const nextDate = new Date(nextTasks[0].next_run);
        const timeStr = nextDate.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
        const dateStr = nextDate.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
        document.getElementById("stat-next-run").textContent = `${timeStr} (${dateStr})`;
    } else {
        document.getElementById("stat-next-run").textContent = "--:--";
    }
}

function renderTasks(tasks) {
    const container = document.getElementById("tasks-container");
    if (!tasks || tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state card">
                <div style="font-size: 40px; margin-bottom: 12px;">📭</div>
                <h3>Chưa có tác vụ nào được tạo</h3>
                <p>Hãy bấm nút <b>"➕ Thêm Tác Vụ Mới"</b> phía trên để bắt đầu cài đặt lịch nhắc việc hoặc gửi file Zalo tự động!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = tasks.map(task => {
        let scheduleBadge = "";
        if (task.schedule_type === 'daily') {
            scheduleBadge = `Hàng ngày ${task.schedule_time || '08:00'}`;
        } else if (task.schedule_type === 'weekly') {
            const daysMap = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
            const daysArr = (task.schedule_days || '').split(',').map(d => daysMap[parseInt(d)]).filter(Boolean).join(', ');
            scheduleBadge = `Hàng tuần (${daysArr || 'T2'}) lúc ${task.schedule_time}`;
        } else if (task.schedule_type === 'interval') {
            scheduleBadge = `Mỗi ${task.interval_minutes} phút`;
        } else {
            scheduleBadge = `1 lần: ${task.schedule_time || 'Chưa định'}`;
        }

        let actionBadge = "";
        if (task.action_type === 'zalo_all') actionBadge = "Gửi Tin & File Zalo";
        else if (task.action_type === 'zalo_file') actionBadge = "Gửi File Zalo";
        else if (task.action_type === 'zalo_msg') actionBadge = "Gửi Tin Nhắn Zalo";
        else actionBadge = "Chỉ Bật Chuông Nhắc";

        let fileBadge = "";
        if (task.file_source_mode === 'directory') {
            fileBadge = `<span class="badge badge-file" title="Tự bốc file mới nhất trong: ${task.watch_directory}">🔄 Bốc file mới (${task.file_pattern || '*.*'})</span>`;
        } else if (task.attachment_name) {
            fileBadge = `<span class="badge badge-file">📎 ${escapeHtml(task.attachment_name)}</span>`;
        }

        const teleBadge = task.notify_telegram ? `<span class="badge badge-tele">📱 Báo Telegram</span>` : '';
        const countdownBadge = (task.safe_countdown_seconds > 0) ? `<span class="badge badge-action">🛡 Đếm lùi ${task.safe_countdown_seconds}s</span>` : '';

        const nextRunStr = task.next_run ? new Date(task.next_run).toLocaleString('vi-VN') : 'Không có';

        return `
            <div class="task-card ${task.is_active ? '' : 'inactive'}" id="task-card-${task.id}">
                <div>
                    <div class="task-card-header">
                        <h3 class="task-title">${escapeHtml(task.title)}</h3>
                    </div>
                    <div class="task-badges">
                        <span class="badge badge-schedule">⏰ ${scheduleBadge}</span>
                        <span class="badge badge-action">⚡ ${actionBadge}</span>
                        ${fileBadge}
                        ${teleBadge}
                        ${countdownBadge}
                    </div>

                    ${task.description ? `<p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">${escapeHtml(task.description)}</p>` : ''}

                    <div class="task-info-list">
                        ${task.zalo_recipient ? `<div class="task-info-item"><span>👤 Người nhận:</span> <b>${escapeHtml(task.zalo_recipient)}</b></div>` : ''}
                        <div class="task-info-item"><span>⏳ Lần chạy tới:</span> <b>${nextRunStr}</b></div>
                        ${task.last_run ? `<div class="task-info-item"><span>🕒 Lần chạy gần nhất:</span> <span>${new Date(task.last_run).toLocaleString('vi-VN')}</span></div>` : ''}
                    </div>
                </div>

                <div class="task-actions-row">
                    <button class="btn btn-sm ${task.is_active ? 'btn-secondary' : 'btn-success'}" onclick="toggleTaskStatus(${task.id})">
                        ${task.is_active ? '⏸ Tạm dừng' : '▶ Kích hoạt'}
                    </button>
                    <button class="btn btn-sm btn-outline" onclick="runTaskNow(${task.id})" title="Chạy thử nghiệm tác vụ này ngay lập tức">
                        🚀 Chạy ngay
                    </button>
                    <button class="btn btn-sm btn-outline" onclick="openEditModal(${task.id})">
                        ✏ Sửa
                    </button>
                    <button class="btn btn-sm btn-danger-outline" onclick="deleteTaskItem(${task.id})" style="margin-left: auto;">
                        🗑 Xóa
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function handleScheduleTypeChange() {
    const type = document.getElementById("form-schedule-type").value;
    const timeGroup = document.getElementById("group-schedule-time");
    const weeklyGroup = document.getElementById("group-weekly-days");
    const intervalGroup = document.getElementById("group-interval");
    const onceGroup = document.getElementById("group-once-datetime");

    timeGroup.style.display = (type === 'daily' || type === 'weekly') ? 'flex' : 'none';
    weeklyGroup.style.display = (type === 'weekly') ? 'block' : 'none';
    intervalGroup.style.display = (type === 'interval') ? 'block' : 'none';
    onceGroup.style.display = (type === 'once') ? 'block' : 'none';
}

function openModal(task = null) {
    const modal = document.getElementById("task-modal");
    const form = document.getElementById("task-form");
    form.reset();

    if (task) {
        document.getElementById("modal-title").textContent = "✏ Chỉnh Sửa Tác Vụ";
        document.getElementById("form-task-id").value = task.id;
        document.getElementById("form-title").value = task.title;
        document.getElementById("form-desc").value = task.description || '';
        document.getElementById("form-schedule-type").value = task.schedule_type;
        document.getElementById("form-schedule-time").value = task.schedule_time || '08:30';
        document.getElementById("form-interval-minutes").value = task.interval_minutes || 60;
        document.getElementById("form-action-type").value = task.action_type;
        document.getElementById("form-recipient").value = task.zalo_recipient || '';
        document.getElementById("form-message").value = task.zalo_message || '';
        document.getElementById("form-safe-countdown").value = task.safe_countdown_seconds || 0;
        document.getElementById("form-notify-tele").checked = Boolean(task.notify_telegram);

        // Days
        if (task.schedule_days) {
            const days = task.schedule_days.split(',');
            document.querySelectorAll("input[name='days']").forEach(cb => {
                cb.checked = days.includes(cb.value);
            });
        }

        // File source mode
        const isDir = (task.file_source_mode === 'directory');
        document.querySelector(`input[name='form-file-mode'][value='${isDir ? 'directory' : 'fixed'}']`).checked = true;
        document.getElementById("form-file-fixed-block").style.display = isDir ? "none" : "block";
        document.getElementById("form-file-dir-block").style.display = isDir ? "block" : "none";
        document.getElementById("form-watch-dir").value = task.watch_directory || '';
        document.getElementById("form-file-pattern").value = task.file_pattern || '*.xlsx';

        if (task.attachment_name) {
            document.getElementById("existing-file-info").style.display = "block";
            document.getElementById("existing-file-name").textContent = task.attachment_name;
        } else {
            document.getElementById("existing-file-info").style.display = "none";
        }
    } else {
        document.getElementById("modal-title").textContent = "➕ Tạo Tác Vụ Mới";
        document.getElementById("form-task-id").value = "";
        document.getElementById("existing-file-info").style.display = "none";
        document.querySelector("input[name='form-file-mode'][value='fixed']").checked = true;
        document.getElementById("form-file-fixed-block").style.display = "block";
        document.getElementById("form-file-dir-block").style.display = "none";
        document.getElementById("form-safe-countdown").value = "30"; // Khuyên dùng 30s
        document.getElementById("form-notify-tele").checked = true;

        document.querySelectorAll("input[name='days']").forEach(cb => {
            cb.checked = (cb.value === "0" || cb.value === "4");
        });
    }

    handleScheduleTypeChange();
    modal.classList.add("show");
}

function closeModal() {
    document.getElementById("task-modal").classList.remove("show");
}

async function checkDirectory(path, pattern, targetElementId) {
    const el = document.getElementById(targetElementId);
    if (!path.trim()) {
        el.className = "dir-preview-result error";
        el.textContent = "Vui lòng nhập đường dẫn thư mục!";
        return;
    }
    el.className = "dir-preview-result";
    el.style.display = "block";
    el.textContent = "Đang quét thư mục...";

    try {
        const res = await fetch(`/api/browse-directory?path=${encodeURIComponent(path)}&pattern=${encodeURIComponent(pattern || '*.*')}`);
        const data = await res.json();
        if (data.exists && data.latest_file) {
            el.className = "dir-preview-result success";
            el.innerHTML = `✅ Đã tìm thấy file mới nhất: <b>${escapeHtml(data.latest_file.name)}</b> (${(data.latest_file.size / 1024).toFixed(1)} KB)`;
        } else if (data.exists) {
            el.className = "dir-preview-result error";
            el.textContent = "Thư mục tồn tại nhưng không tìm thấy file nào khớp với định dạng lọc!";
        } else {
            el.className = "dir-preview-result error";
            el.textContent = "❌ Thư mục không tồn tại trên máy tính! Vui lòng kiểm tra lại.";
        }
    } catch (e) {
        el.className = "dir-preview-result error";
        el.textContent = "Lỗi khi kiểm tra thư mục: " + e;
    }
}

async function handleSaveTask(e) {
    e.preventDefault();
    const taskId = document.getElementById("form-task-id").value;
    const formData = new FormData();

    formData.append("title", document.getElementById("form-title").value);
    formData.append("description", document.getElementById("form-desc").value);
    formData.append("schedule_type", document.getElementById("form-schedule-type").value);
    formData.append("schedule_time", document.getElementById("form-schedule-time").value);
    formData.append("interval_minutes", document.getElementById("form-interval-minutes").value);
    formData.append("action_type", document.getElementById("form-action-type").value);
    formData.append("zalo_recipient", document.getElementById("form-recipient").value);
    formData.append("zalo_message", document.getElementById("form-message").value);

    // Days array
    const selectedDays = Array.from(document.querySelectorAll("input[name='days']:checked")).map(cb => cb.value);
    formData.append("schedule_days", selectedDays.join(','));

    // File source mode
    const fileMode = document.querySelector("input[name='form-file-mode']:checked").value;
    formData.append("file_source_mode", fileMode);
    formData.append("watch_directory", document.getElementById("form-watch-dir").value);
    formData.append("file_pattern", document.getElementById("form-file-pattern").value);

    // Safe Countdown & Telegram
    formData.append("safe_countdown_seconds", document.getElementById("form-safe-countdown").value);
    formData.append("notify_telegram", document.getElementById("form-notify-tele").checked);

    // File upload
    const fileInput = document.getElementById("form-file");
    if (fileMode === "fixed" && fileInput.files.length > 0) {
        formData.append("file", fileInput.files[0]);
    }

    const url = taskId ? `/api/tasks/${taskId}` : "/api/tasks";
    const method = taskId ? "PUT" : "POST";

    try {
        const res = await fetch(url, { method: method, body: formData });
        const data = await res.json();
        if (data.success) {
            closeModal();
            loadTasks();
        } else {
            alert("Lỗi khi lưu tác vụ: " + (data.detail || "Không rõ"));
        }
    } catch (err) {
        alert("Lỗi kết nối: " + err);
    }
}

async function openEditModal(taskId) {
    try {
        const res = await fetch(`/api/tasks`);
        const data = await res.json();
        const task = (data.tasks || []).find(t => t.id === taskId);
        if (task) openModal(task);
    } catch (e) {
        alert("Lỗi khi lấy thông tin tác vụ");
    }
}

async function toggleTaskStatus(taskId) {
    try {
        await fetch(`/api/tasks/${taskId}/toggle`, { method: "POST" });
        loadTasks();
    } catch (e) {
        console.error("Lỗi toggle status:", e);
    }
}

async function deleteTaskItem(taskId) {
    if (!confirm("Bạn có chắc chắn muốn xóa tác vụ này?")) return;
    try {
        await fetch(`/api/tasks/${taskId}`, { method: "DELETE" });
        loadTasks();
    } catch (e) {
        console.error("Lỗi xóa task:", e);
    }
}

async function runTaskNow(taskId) {
    if (!confirm("Thực thi tác vụ này ngay bây giờ?")) return;
    try {
        const res = await fetch(`/api/tasks/${taskId}/run-now`, { method: "POST" });
        const data = await res.json();
        playChimeSound();
        alert("Đã kích hoạt! Xem chi tiết tại tab 'Lịch Sử Thực Thi'.");
        loadTasks();
        loadLogs();
    } catch (e) {
        alert("Lỗi kích hoạt tác vụ: " + e);
    }
}

async function handleQuickTest(e) {
    e.preventDefault();
    const btn = document.getElementById("btn-run-quick-test");
    const resultBox = document.getElementById("test-result-box");
    const resultLogs = document.getElementById("test-result-logs");

    btn.disabled = true;
    btn.innerHTML = `<div class="spinner" style="width: 16px; height: 16px; border-width: 2px; margin: 0;"></div> Đang gửi...`;
    resultBox.style.display = "block";
    resultLogs.textContent = "Đang khởi tạo quy trình tự động hóa Zalo...";

    const formData = new FormData();
    formData.append("recipient", document.getElementById("test-recipient").value);
    formData.append("message", document.getElementById("test-message").value);
    formData.append("dry_run", document.getElementById("test-dry-run").checked);

    const fileMode = document.querySelector("input[name='test-file-mode']:checked").value;
    formData.append("file_source_mode", fileMode);
    formData.append("watch_directory", document.getElementById("test-dir-path").value);

    const fileInput = document.getElementById("test-file");
    if (fileMode === "fixed" && fileInput.files.length > 0) {
        formData.append("file", fileInput.files[0]);
    }

    try {
        const res = await fetch("/api/test-zalo", { method: "POST", body: formData });
        const data = await res.json();
        playChimeSound();
        if (data.result && data.result.logs) {
            resultLogs.textContent = data.result.logs.join("\n");
        } else {
            resultLogs.textContent = JSON.stringify(data, null, 2);
        }
    } catch (err) {
        resultLogs.textContent = "Lỗi khi chạy thử nghiệm: " + err;
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>📤</span> Bấm Gửi Thử Ngay Qua Zalo`;
    }
}

// SMART PREVIEW & COUNTDOWN
async function checkAlerts() {
    try {
        const res = await fetch("/api/alerts");
        const data = await res.json();
        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(alertItem => {
                if (alertItem.is_preview) {
                    showSmartPreview(alertItem);
                } else {
                    triggerAlertNotification(alertItem);
                }
            });
            loadTasks();
            loadLogs();
        }
    } catch (e) {
        // im lặng
    }
}

function showSmartPreview(item) {
    playChimeSound();
    activePreviewTaskId = item.id;
    currentPreviewCountdown = item.countdown || 30;

    const modal = document.getElementById("preview-modal");
    document.getElementById("preview-task-title").textContent = item.title;
    document.getElementById("preview-recipient").textContent = item.zalo_recipient || '--';
    document.getElementById("preview-file").textContent = item.attachment_name || 'Tự bốc file mới nhất';
    document.getElementById("preview-countdown-number").textContent = currentPreviewCountdown;
    modal.style.display = "flex";

    if (previewTimer) clearInterval(previewTimer);
    previewTimer = setInterval(() => {
        currentPreviewCountdown--;
        document.getElementById("preview-countdown-number").textContent = Math.max(0, currentPreviewCountdown);
        if (currentPreviewCountdown <= 0) {
            clearInterval(previewTimer);
            modal.style.display = "none";
        }
    }, 1000);
}

async function confirmPreviewNow() {
    if (!activePreviewTaskId) return;
    if (previewTimer) clearInterval(previewTimer);
    document.getElementById("preview-modal").style.display = "none";

    try {
        await fetch(`/api/tasks/${activePreviewTaskId}/confirm-preview`, { method: "POST" });
        loadTasks();
        loadLogs();
    } catch (e) {
        console.error("Lỗi confirm preview:", e);
    }
}

async function postponePreview() {
    if (!activePreviewTaskId) return;
    if (previewTimer) clearInterval(previewTimer);
    document.getElementById("preview-modal").style.display = "none";

    try {
        await fetch(`/api/tasks/${activePreviewTaskId}/postpone-preview`, { method: "POST" });
        alert("Đã hoãn tác vụ lại 15 phút!");
        loadTasks();
    } catch (e) {
        console.error("Lỗi postpone preview:", e);
    }
}

function triggerAlertNotification(item) {
    playChimeSound();
    showBrowserNotification(`🔔 Nhắc việc: ${item.title}`, item.description || "Đến giờ thực hiện tác vụ đã lập lịch!");

    const banner = document.getElementById("due-alert-banner");
    document.getElementById("alert-task-title").textContent = `🔔 Đến giờ: ${item.title}`;
    document.getElementById("alert-task-desc").textContent = item.zalo_recipient ? `Gửi tới: ${item.zalo_recipient}` : (item.description || "Tác vụ nhắc nhở");
    banner.style.display = "flex";

    setTimeout(() => {
        banner.style.display = "none";
    }, 10000);
}

// LOGS
async function loadLogs() {
    try {
        const res = await fetch("/api/logs");
        const data = await res.json();
        const logs = data.logs || [];
        const tbody = document.getElementById("logs-tbody");

        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center">Chưa có lịch sử thực thi nào.</td></tr>`;
            return;
        }

        const successCount = logs.filter(l => l.status === 'SUCCESS').length;
        document.getElementById("stat-success-runs").textContent = successCount;

        tbody.innerHTML = logs.map(l => {
            const timeStr = new Date(l.executed_at).toLocaleString('vi-VN');
            const statusBadge = l.status === 'SUCCESS' 
                ? `<span class="badge-status status-success">Thành công</span>`
                : `<span class="badge-status status-failed">Lỗi / Hủy</span>`;

            return `
                <tr>
                    <td><b>${timeStr}</b></td>
                    <td><b>${escapeHtml(l.task_title || '')}</b></td>
                    <td>${escapeHtml(l.recipient || '--')}</td>
                    <td>${statusBadge}</td>
                    <td>${l.attachment_name ? `📎 ${escapeHtml(l.attachment_name)}` : '--'}</td>
                    <td><small style="font-family: monospace; color: #475569;">${escapeHtml((l.details || '').slice(0, 120))}</small></td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error("Lỗi tải lịch sử:", e);
    }
}

// SETTINGS & TELEGRAM
async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        const settings = await res.json();
        document.getElementById("setting-tele-token").value = settings.telegram_bot_token || "";
        document.getElementById("setting-tele-chat").value = settings.telegram_chat_id || "";
    } catch (e) {
        console.error("Lỗi load settings:", e);
    }
}

async function saveSettings() {
    const payload = {
        telegram_bot_token: document.getElementById("setting-tele-token").value.trim(),
        telegram_chat_id: document.getElementById("setting-tele-chat").value.trim()
    };
    try {
        await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        alert("Đã lưu cài đặt thành công!");
    } catch (e) {
        alert("Lỗi lưu cài đặt: " + e);
    }
}

async function testTelegram() {
    const token = document.getElementById("setting-tele-token").value.trim();
    const chat = document.getElementById("setting-tele-chat").value.trim();
    if (!token || !chat) {
        alert("Vui lòng nhập đầy đủ Telegram Bot Token và Chat ID trước khi test!");
        return;
    }

    const formData = new FormData();
    formData.append("bot_token", token);
    formData.append("chat_id", chat);

    try {
        const res = await fetch("/api/test-telegram", { method: "POST", body: formData });
        const data = await res.json();
        alert(data.message);
    } catch (e) {
        alert("Lỗi khi kết nối Telegram: " + e);
    }
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ============================================================
// AI CHAT 2 CHIỀU LOGIC
// ============================================================
function initAIChat() {
    const chatForm = document.getElementById("chat-input-form");
    const chatInput = document.getElementById("chat-input-text");
    const chatMessages = document.getElementById("chat-messages");
    const clearBtn = document.getElementById("btn-clear-chat");
    const suggestionChips = document.querySelectorAll(".suggestion-chip");

    if (!chatForm || !chatInput || !chatMessages) return;

    async function sendChatMessage(userText) {
        const text = userText || chatInput.value.trim();
        if (!text) return;

        appendMessageBubble("user", escapeHtml(text));
        chatInput.value = "";

        const thinkingId = "thinking-" + Date.now();
        const thinkingBubble = document.createElement("div");
        thinkingBubble.className = "chat-message ai-message";
        thinkingBubble.id = thinkingId;
        thinkingBubble.innerHTML = `
            <div class="msg-avatar">🤖</div>
            <div class="msg-bubble"><i>Trợ lý đang xử lý câu lệnh...</i></div>
        `;
        chatMessages.appendChild(thinkingBubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const res = await fetch("/api/ai-chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();

            const thinkingEl = document.getElementById(thinkingId);
            if (thinkingEl) thinkingEl.remove();

            appendMessageBubble("ai", data.reply);

            if (data.action === "task_created") {
                playChimeSound();
                loadTasks();
            }
        } catch (err) {
            const thinkingEl = document.getElementById(thinkingId);
            if (thinkingEl) thinkingEl.remove();
            appendMessageBubble("ai", "Xin lỗi, đã xảy ra lỗi kết nối: " + err);
        }
    }

    function appendMessageBubble(sender, htmlContent) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-message ${sender}-message`;
        msgDiv.innerHTML = `
            <div class="msg-avatar">${sender === 'ai' ? '🤖' : '👤'}</div>
            <div class="msg-bubble">${htmlContent}</div>
        `;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        sendChatMessage();
    });

    suggestionChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const text = chip.dataset.text || chip.innerText.trim();
            sendChatMessage(text);
        });
    });

    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            chatMessages.innerHTML = `
                <div class="chat-message ai-message">
                    <div class="msg-avatar">🤖</div>
                    <div class="msg-bubble">
                        <p>Đoạn chat đã được làm mới! Bạn cần tôi giúp gì?</p>
                    </div>
                </div>
            `;
        });
    }
}
