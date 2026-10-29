/**
 * Animate UI + GreenSock (GSAP 3) Animation Engine
 * Standardized High-Craft Web Animations for CTUT Blockchain Degree System
 * Hardware-Accelerated 60-120FPS - Apple Motion & GSAP Physics
 */

(function () {
    'use strict';

    const hasGSAP = typeof gsap !== 'undefined';

    // -------------------------------------------------------------------------
    // 1. GSAP STICKY TOP ACTION BAR (Interruptible Physics, Zero Jitter)
    // -------------------------------------------------------------------------
    function initAdminActionBar() {
        const form = document.querySelector('#changelist-form');
        const container = document.querySelector('.apple-action-bar-container');
        if (!form || !container) return;

        let isBarOpen = false;

        function updateActionBarState() {
            const checkedBoxes = form.querySelectorAll('input.action-select:checked');
            const count = checkedBoxes.length;

            if (count > 0) {
                if (!isBarOpen) {
                    isBarOpen = true;
                    container.classList.add('is-visible');

                    if (hasGSAP) {
                        gsap.killTweensOf(container);
                        gsap.fromTo(container, 
                            { opacity: 0, y: -10, scale: 0.985 },
                            { 
                                opacity: 1, 
                                y: 0, 
                                scale: 1, 
                                duration: 0.32, 
                                ease: 'power3.out',
                                onStart: () => { container.style.pointerEvents = 'auto'; }
                            }
                        );
                    }
                }

                // Micro-bounce on counter
                const counter = container.querySelector('.action-counter');
                if (counter) {
                    if (hasGSAP) {
                        gsap.killTweensOf(counter);
                        gsap.fromTo(counter,
                            { scale: 1.25, color: '#2563eb' },
                            { scale: 1, color: '', duration: 0.3, ease: 'back.out(2.5)' }
                        );
                    } else {
                        counter.classList.remove('apple-pop-animate');
                        void counter.offsetWidth;
                        counter.classList.add('apple-pop-animate');
                    }
                }

                // Checkmark badge pop
                const badge = container.querySelector('.apple-check-badge');
                if (badge && hasGSAP) {
                    gsap.killTweensOf(badge);
                    gsap.fromTo(badge,
                        { scale: 0.7, rotation: -12 },
                        { scale: 1, rotation: 0, duration: 0.35, ease: 'back.out(2)' }
                    );
                }
            } else {
                if (isBarOpen) {
                    isBarOpen = false;

                    if (hasGSAP) {
                        gsap.killTweensOf(container);
                        gsap.to(container, {
                            opacity: 0,
                            y: -8,
                            scale: 0.985,
                            duration: 0.22,
                            ease: 'power2.in',
                            onComplete: () => {
                                container.classList.remove('is-visible');
                                container.style.pointerEvents = 'none';
                            }
                        });
                    } else {
                        container.classList.remove('is-visible');
                    }
                }
            }

            // Sync Row highlighting with GSAP
            syncTableRows(form);
        }

        form.addEventListener('change', function (e) {
            if (e.target.matches('input.action-select, #action-toggle')) {
                updateActionBarState();
            }
        });

        // Initialize state on page load
        updateActionBarState();
    }

    // Đồng bộ màu sắc các hàng được tick chọn
    function syncTableRows(form) {
        if (!hasGSAP) return;
        const isDark = document.documentElement.classList.contains('dark') || document.body.classList.contains('dark');
        const rows = form.querySelectorAll('tbody tr');

        rows.forEach((row) => {
            const checkbox = row.querySelector('input.action-select');
            if (!checkbox) return;

            if (checkbox.checked) {
                gsap.to(row, {
                    backgroundColor: isDark ? 'rgba(59, 130, 246, 0.14)' : 'rgba(59, 130, 246, 0.07)',
                    duration: 0.2,
                    ease: 'power1.out'
                });
            } else {
                gsap.to(row, {
                    backgroundColor: '',
                    duration: 0.2,
                    ease: 'power1.out',
                    clearProps: 'backgroundColor'
                });
            }
        });
    }

    // -------------------------------------------------------------------------
    // 2. GSAP STAGGER ENTRANCES (Bảng dữ liệu & Thẻ Dashboard trượt vào êm ái)
    // -------------------------------------------------------------------------
    function initStaggerEntrances() {
        if (!hasGSAP) return;

        // Stagger cho các hàng trong bảng dữ liệu
        const tableRows = document.querySelectorAll('tbody tr');
        if (tableRows.length > 0 && tableRows.length <= 100) {
            gsap.from(tableRows, {
                opacity: 0,
                y: 10,
                duration: 0.35,
                ease: 'power2.out',
                stagger: {
                    each: 0.02,
                    from: 'start'
                },
                clearProps: 'transform,opacity'
            });
        }

        // Stagger cho 4 bước trong Workflow Hub
        const steps = document.querySelectorAll('.apple-step-item');
        if (steps.length > 0) {
            gsap.from(steps, {
                opacity: 0,
                y: 16,
                duration: 0.45,
                ease: 'power3.out',
                stagger: 0.06,
                clearProps: 'transform,opacity'
            });
        }

        // Stagger cho các thẻ KPI Cards
        const kpis = document.querySelectorAll('.apple-kpi-item');
        if (kpis.length > 0) {
            gsap.from(kpis, {
                opacity: 0,
                y: 18,
                duration: 0.5,
                ease: 'power3.out',
                stagger: 0.07,
                clearProps: 'transform,opacity'
            });
        }
    }

    // -------------------------------------------------------------------------
    // 3. GSAP FLUID NUMBER ROLL-UP FOR KPI CARDS
    // -------------------------------------------------------------------------
    function initKpiCounterRollup() {
        const metricEls = document.querySelectorAll('.apple-kpi-item h3');
        if (!metricEls.length) return;

        metricEls.forEach((el) => {
            const rawText = el.textContent.trim();
            const match = rawText.match(/^([^\d]*)(\d+)([^\d]*)$/);
            if (!match) return;

            const prefix = match[1] || '';
            const target = parseInt(match[2], 10);
            const suffix = match[3] || '';
            
            if (isNaN(target) || target <= 0) return;

            if (hasGSAP) {
                const counter = { val: 0 };
                gsap.to(counter, {
                    val: target,
                    duration: 0.95,
                    ease: 'power3.out',
                    onUpdate: () => {
                        el.textContent = `${prefix}${Math.floor(counter.val).toLocaleString()}${suffix}`;
                    },
                    onComplete: () => {
                        el.textContent = rawText;
                    }
                });
            } else {
                // Fallback nếu không có GSAP
                let startTime = performance.now();
                const duration = 650;
                function easeOutExpo(x) { return x === 1 ? 1 : 1 - Math.pow(2, -10 * x); }
                function update(now) {
                    const progress = Math.min((now - startTime) / duration, 1);
                    el.textContent = `${prefix}${Math.floor(easeOutExpo(progress) * target).toLocaleString()}${suffix}`;
                    if (progress < 1) requestAnimationFrame(update);
                    else el.textContent = rawText;
                }
                requestAnimationFrame(update);
            }
        });
    }

    // -------------------------------------------------------------------------
    // 4. GSAP 3D PERSPECTIVE TILT WITH SPRING RETURN
    // -------------------------------------------------------------------------
    function initTiltCards() {
        const cards = document.querySelectorAll('.animate-tilt, .animate-tilt-demo');

        cards.forEach((card) => {
            let glare = card.querySelector('.animate-tilt-glare');
            if (!glare) {
                glare = document.createElement('div');
                glare.className = 'animate-tilt-glare';
                card.appendChild(glare);
            }

            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const normX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
                const normY = ((e.clientY - rect.top) / rect.height) * 2 - 1;

                if (hasGSAP) {
                    gsap.to(card, {
                        rotationY: normX * 4.5,
                        rotationX: -normY * 4.5,
                        scale: 1.018,
                        duration: 0.28,
                        ease: 'power1.out',
                        transformPerspective: 1000,
                        transformOrigin: 'center center'
                    });

                    const glareX = ((e.clientX - rect.left) / rect.width) * 100;
                    const glareY = ((e.clientY - rect.top) / rect.height) * 100;
                    gsap.to(glare, {
                        opacity: 1,
                        background: `radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255, 255, 255, 0.22) 0%, rgba(255, 255, 255, 0) 70%)`,
                        duration: 0.2,
                        ease: 'power1.out'
                    });
                }
            });

            card.addEventListener('mouseleave', () => {
                if (hasGSAP) {
                    gsap.to(card, {
                        rotationX: 0,
                        rotationY: 0,
                        scale: 1,
                        duration: 0.55,
                        ease: 'elastic.out(1, 0.6)'
                    });
                    gsap.to(glare, {
                        opacity: 0,
                        duration: 0.35,
                        ease: 'power1.out'
                    });
                }
            });
        });
    }

    // -------------------------------------------------------------------------
    // 5. GSAP TACTILE BUTTON INTERACTIONS
    // -------------------------------------------------------------------------
    function initTactileButtons() {
        const selector = '.animate-btn, .tab-btn, button, .button, .btn-action, .apple-action-btn, .apple-step-item, .apple-kpi-item';

        document.addEventListener('pointerdown', function (e) {
            const target = e.target.closest(selector);
            if (!target) return;

            if (hasGSAP) {
                gsap.to(target, { scale: 0.965, duration: 0.08, ease: 'power2.out' });
                const cleanup = () => {
                    gsap.to(target, { scale: 1, duration: 0.28, ease: 'back.out(2)' });
                    window.removeEventListener('pointerup', cleanup);
                    window.removeEventListener('pointercancel', cleanup);
                };
                window.addEventListener('pointerup', cleanup, { once: true });
                window.addEventListener('pointercancel', cleanup, { once: true });
            } else {
                target.style.transition = 'transform 70ms cubic-bezier(0.2, 0, 0, 1)';
                target.style.transform = 'scale(0.965)';
                const cleanup = () => {
                    target.style.transition = 'transform 220ms cubic-bezier(0.16, 1, 0.3, 1)';
                    target.style.transform = '';
                    window.removeEventListener('pointerup', cleanup);
                    window.removeEventListener('pointercancel', cleanup);
                };
                window.addEventListener('pointerup', cleanup, { once: true });
                window.addEventListener('pointercancel', cleanup, { once: true });
            }
        }, { passive: true });
    }

    // -------------------------------------------------------------------------
    // 6. ANIMATED COPY BUTTONS WITH GSAP
    // -------------------------------------------------------------------------
    function initCopyButtons() {
        document.querySelectorAll('[data-copy-text]').forEach((btn) => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const text = btn.getAttribute('data-copy-text');
                if (!text) return;

                try {
                    await navigator.clipboard.writeText(text);
                    const originalHtml = btn.innerHTML;
                    btn.classList.add('copied');
                    btn.innerHTML = `<span class="material-symbols-outlined text-sm">check</span> Đã chép!`;

                    if (hasGSAP) {
                        gsap.fromTo(btn,
                            { scale: 0.92 },
                            { scale: 1.08, duration: 0.22, ease: 'back.out(3)', yoyo: true, repeat: 1 }
                        );
                    }

                    setTimeout(() => {
                        btn.classList.remove('copied');
                        btn.innerHTML = originalHtml;
                        if (hasGSAP) gsap.to(btn, { scale: 1, duration: 0.2 });
                    }, 1800);
                } catch (err) {
                    console.error('Không thể chép vào bộ nhớ tạm:', err);
                }
            });
        });
    }

    // -------------------------------------------------------------------------
    // 7. RIPPLE EFFECT FOR BUTTONS
    // -------------------------------------------------------------------------
    function initRipple() {
        document.addEventListener('click', function (e) {
            const btn = e.target.closest('.animate-btn, .tab-btn, button[type="submit"], .btn-action, .animate-ripple');
            if (!btn) return;

            const rect = btn.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height) * 1.5;
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            const ripple = document.createElement('span');
            ripple.style.width = ripple.style.height = `${size}px`;
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;

            const bgColor = window.getComputedStyle(btn).backgroundColor;
            const isLightBg = isColorLight(bgColor);
            ripple.className = isLightBg ? 'ripple-wave ripple-wave-dark' : 'ripple-wave';

            btn.appendChild(ripple);

            if (hasGSAP) {
                gsap.fromTo(ripple,
                    { scale: 0, opacity: 0.7 },
                    { 
                        scale: 3.5, 
                        opacity: 0, 
                        duration: 0.55, 
                        ease: 'power2.out',
                        onComplete: () => ripple.remove() 
                    }
                );
            } else {
                setTimeout(() => ripple.remove(), 550);
            }
        });
    }

    function isColorLight(rgbStr) {
        if (!rgbStr || rgbStr === 'transparent') return true;
        const rgb = rgbStr.match(/\d+/g);
        if (!rgb || rgb.length < 3) return false;
        const yiq = ((rgb[0] * 299) + (rgb[1] * 587) + (rgb[2] * 114)) / 1000;
        return yiq >= 170;
    }

    // -------------------------------------------------------------------------
    // 8. ANIMATED DRAG & DROP ZONE
    // -------------------------------------------------------------------------
    function initDropzone() {
        const dropzone = document.querySelector('#pdf-dropzone, #search-form input[type="file"]')?.parentElement;
        if (!dropzone) return;

        ['dragenter', 'dragover'].forEach((eventName) => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('border-ntt-light', 'bg-blue-50/50');
                if (hasGSAP) {
                    gsap.to(dropzone, { scale: 1.015, duration: 0.2, ease: 'power2.out' });
                }
            });
        });

        ['dragleave', 'drop'].forEach((eventName) => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('border-ntt-light', 'bg-blue-50/50');
                if (hasGSAP) {
                    gsap.to(dropzone, { scale: 1, duration: 0.2, ease: 'power2.out' });
                }
            });
        });
    }

    // Khởi chạy toàn bộ hệ thống
    function init() {
        initTactileButtons();
        initAdminActionBar();
        initStaggerEntrances();
        initKpiCounterRollup();
        initRipple();
        initTiltCards();
        initCopyButtons();
        initDropzone();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.AnimateUI = {
        init,
        initAdminActionBar,
        initKpiCounterRollup,
        initStaggerEntrances,
        initTiltCards,
        initRipple,
        initCopyButtons
    };
})();
