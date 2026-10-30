/**
 * main.js - ResourceBridge Client Interactivity
 * =============================================
 * Handles mobile navbar toggling, password visibility toggle,
 * and 1-click hackathon demo credential auto-fill.
 */

document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------------------
    // 1. Mobile Navigation Menu Toggle
    // -------------------------------------------------------------------------
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('open');
            const isOpen = navMenu.classList.contains('open');
            navToggle.setAttribute('aria-expanded', isOpen);
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!navToggle.contains(e.target) && !navMenu.contains(e.target) && navMenu.classList.contains('open')) {
                navMenu.classList.remove('open');
                navToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // -------------------------------------------------------------------------
    // 2. Password Visibility Toggle
    // -------------------------------------------------------------------------
    const togglePasswordBtn = document.getElementById('toggle-password');
    const passwordInput = document.getElementById('password');

    if (togglePasswordBtn && passwordInput) {
        togglePasswordBtn.addEventListener('click', () => {
            const isPassword = passwordInput.getAttribute('type') === 'password';
            passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
            
            // Toggle icon SVG
            togglePasswordBtn.innerHTML = isPassword
                ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`
                : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
        });
    }

    // -------------------------------------------------------------------------
    // 3. Hackathon 1-Click Demo Profiles Auto-Fill
    // -------------------------------------------------------------------------
    const demoButtons = document.querySelectorAll('.btn-demo-fill');
    const emailInput = document.getElementById('email');

    if (demoButtons.length > 0 && emailInput && passwordInput) {
        demoButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const demoEmail = btn.getAttribute('data-email');
                const demoPass = btn.getAttribute('data-password');
                const demoRole = btn.getAttribute('data-role');

                // Fill inputs
                emailInput.value = demoEmail;
                passwordInput.value = demoPass;

                // Visual flash effect on inputs
                [emailInput, passwordInput].forEach(input => {
                    input.style.borderColor = '#10b981';
                    input.style.backgroundColor = '#ecfdf5';
                    setTimeout(() => {
                        input.style.borderColor = '';
                        input.style.backgroundColor = '';
                    }, 500);
                });

                // Set focus to the submit button for 1-step completion
                const submitBtn = document.getElementById('submit-login-btn');
                if (submitBtn) {
                    submitBtn.focus();
                }

                // Temporary button state
                demoButtons.forEach(b => b.style.outline = 'none');
                btn.style.outline = '2px solid #2563eb';
            });
        });
    }

    // -------------------------------------------------------------------------
    // 4. Form Submission Guard (Prevent accidental double-clicks)
    // -------------------------------------------------------------------------
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', () => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                // Keep the button readable during fast processing
                submitBtn.dataset.originalText = submitBtn.innerHTML;
                setTimeout(() => {
                    if (submitBtn) {
                        submitBtn.disabled = true;
                        submitBtn.style.opacity = '0.75';
                    }
                }, 50);
            }
        });
    });

    // -------------------------------------------------------------------------
    // 5. Flash Alert Auto-Fade (Optional after 8 seconds)
    // -------------------------------------------------------------------------
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 8000);
    });

    // -------------------------------------------------------------------------
    // 6. Resource Form Prerequisite Toggles
    // -------------------------------------------------------------------------
    const trainingCheckbox = document.getElementById('training_required');
    const trainingWrapper = document.getElementById('training-details-wrapper');
    const supervisionCheckbox = document.getElementById('supervision_required');
    const supervisionWrapper = document.getElementById('supervision-details-wrapper');

    function syncPrereqToggles() {
        if (trainingCheckbox && trainingWrapper) {
            trainingWrapper.style.display = trainingCheckbox.checked ? 'block' : 'none';
        }
        if (supervisionCheckbox && supervisionWrapper) {
            supervisionWrapper.style.display = supervisionCheckbox.checked ? 'block' : 'none';
        }
    }

    if (trainingCheckbox) {
        trainingCheckbox.addEventListener('change', syncPrereqToggles);
    }
    if (supervisionCheckbox) {
        supervisionCheckbox.addEventListener('change', syncPrereqToggles);
    }
    syncPrereqToggles();
});

