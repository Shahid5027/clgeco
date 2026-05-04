// Countdown timer functionality for QR Attendance System
function startCountdown(expiryTime, elementId, onExpireCallback) {
    const countdownElement = document.getElementById(elementId);
    if (!countdownElement) {
        console.error('Countdown element not found:', elementId);
        return;
    }

    // Parse expiry time
    const expiryDate = new Date(expiryTime);

    // Create progress bar container if not exist
    let progressBar = countdownElement.nextElementSibling;
    if (!progressBar || !progressBar.classList.contains('progress')) {
        progressBar = document.createElement('div');
        progressBar.className = 'progress mt-1';
        progressBar.innerHTML = '<div class="progress-bar bg-success" role="progressbar" style="width: 100%"></div>';
        countdownElement.parentNode.insertBefore(progressBar, countdownElement.nextSibling);
    }
    const progressFill = progressBar.querySelector('.progress-bar');

    function updateCountdown() {
        const now = new Date();
        const timeLeft = expiryDate - now;

        if (timeLeft <= 0) {
            countdownElement.textContent = 'EXPIRED';
            countdownElement.className = 'badge bg-danger countdown-expired';
            progressFill.style.width = '0%';
            if (onExpireCallback && typeof onExpireCallback === 'function') {
                onExpireCallback();
            }
            return;
        }

        const totalSeconds = Math.max(Math.ceil((expiryDate - (expiryDate - timeLeft)) / 1000), 1);
        const secondsLeft = Math.ceil(timeLeft / 1000);

        // Update countdown text
        countdownElement.textContent = `${secondsLeft}s`;

        // Update badge color
        if (secondsLeft <= 2) {
            countdownElement.className = 'badge bg-danger transition-badge';
        } else if (secondsLeft <= 3) {
            countdownElement.className = 'badge bg-warning transition-badge';
        } else {
            countdownElement.className = 'badge bg-success transition-badge';
        }

        // Update progress bar
        const percent = (timeLeft / (totalSeconds * 1000)) * 100;
        progressFill.style.width = `${percent}%`;

        // Schedule next update
        requestAnimationFrame(updateCountdown);
    }

    updateCountdown();
}

// Utility: Auto-refresh QR
function autoRefreshQR(generateCallback, intervalSeconds = 30) {
    if (typeof generateCallback !== 'function') {
        console.error('Generate callback must be a function');
        return;
    }

    let refreshInterval;

    return {
        start: () => refreshInterval = setInterval(generateCallback, intervalSeconds * 1000),
        stop: () => { if (refreshInterval) clearInterval(refreshInterval); refreshInterval = null; }
    };
}

// Sync server time for QR
function syncTimeWithServer(callback) {
    const startTime = Date.now();
    fetch('/generate_qr')
        .then(res => res.json())
        .then(data => {
            const endTime = Date.now();
            const networkDelay = (endTime - startTime) / 2;
            if (data.expiry_time) {
                const adjustedExpiry = new Date(data.expiry_time).getTime() - networkDelay;
                data.expiry_time = new Date(adjustedExpiry).toISOString();
            }
            if (callback) callback(data);
        })
        .catch(err => { console.error('Time sync failed:', err); if (callback) callback(null); });
}

// Format time utility
function formatTime(seconds) {
    if (seconds < 60) return `${seconds}s`;
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s}s`;
}

// Initialize page features
document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Disable submit buttons on form submit
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function () {
            const btn = form.querySelector('button[type="submit"]');
            if (btn && !btn.disabled) {
                const text = btn.textContent;
                btn.disabled = true;
                btn.textContent = 'Please wait...';
                setTimeout(() => { btn.disabled = false; btn.textContent = text; }, 5000);
            }
        });
    });

    // Mobile spacing
    if (window.innerWidth <= 768) {
        document.querySelectorAll('.card').forEach(card => { card.style.margin = '0.5rem 0'; });
    }
});

// Expose globally
window.QRAttendance = { startCountdown, formatTime, autoRefreshQR, syncTimeWithServer };
