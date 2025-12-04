// ---------------- Habit Chart ----------------
window.renderHabitChart = function(labels, data) {
    const ctx = document.getElementById('habitChart').getContext('2d');
    if (window.habitChartInstance) {
        window.habitChartInstance.destroy();
    }
    window.habitChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Habits Completed',
                data: data,
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.2)',
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, stepSize: 1 }
            },
            plugins: {
                legend: { display: true },
                tooltip: { mode: 'index', intersect: false }
            }
        }
    });
};

// ---------------- Goal Chart ----------------
window.renderGoalChart = function(labels, data) {
    const ctx = document.getElementById('goalChart').getContext('2d');
    if (window.goalChartInstance) {
        window.goalChartInstance.destroy();
    }
    window.goalChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Goal Progress (%)',
                data: data,
                backgroundColor: '#2ecc71'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, max: 100 }
            },
            plugins: {
                legend: { display: true },
                tooltip: { mode: 'index', intersect: false }
            }
        }
    });
};

// ---------------- Habit Checkbox Toggle ----------------
document.addEventListener('DOMContentLoaded', function() {
    // For all habit checkboxes on dashboard/habits page
    const checkboxes = document.querySelectorAll('input[type="checkbox"][name="completed"]');

    checkboxes.forEach(box => {
        box.addEventListener('change', function() {
            // Submit the parent form to mark progress
            this.form.submit();
        });
    });

    // Tooltip for last completed date (hover over 💡)
    const tooltips = document.querySelectorAll('[title]');
    tooltips.forEach(el => {
        el.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('span');
            tooltip.className = 'tooltip';
            tooltip.textContent = el.getAttribute('title');
            el.appendChild(tooltip);
        });
        el.addEventListener('mouseleave', function() {
            const tooltip = el.querySelector('.tooltip');
            if (tooltip) el.removeChild(tooltip);
        });
    });
});

// ---------------- Optional: Animate streak bars ----------------
window.animateStreaks = function() {
    const bars = document.querySelectorAll('.streak-bar');
    bars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0';
        setTimeout(() => {
            bar.style.transition = 'width 0.8s ease-in-out';
            bar.style.width = width;
        }, 100);
    });
};

document.addEventListener('DOMContentLoaded', animateStreaks);

// ---------------- Form Validation ----------------
document.getElementById('registerForm').addEventListener('submit', function(e) {
    const password = document.getElementById('password').value;
    const confirm = document.getElementById('confirm_password').value;
    if (password !== confirm) {
        e.preventDefault();
        alert("Passwords do not match!");
    }
});

// ---------------- Password Toggle ----------------

document.querySelectorAll('.toggle-password').forEach(el => {
    el.addEventListener('click', () => {
        const input = document.getElementById(el.dataset.target);
        if (input.type === "password") {
            input.type = "text";
        } else {
            input.type = "password";
        }
    });
});


console.log('main.js loaded');
