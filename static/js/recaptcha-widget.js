/**
 * Interactive reCAPTCHA Challenge Widget (3x3 Visual Puzzle)
 * Offline-ready, zero external dependencies, SVG-based verification.
 */
(function() {
    'use strict';

    // --- 1. SVG ARTWORK REPOSITORY (8 Categories x 4 Variants = 32 SVGs) ---
    const ASSETS = {
        traffic_light: [
            // Variant 1: Red light active
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <defs>
                    <radialGradient id="tl_red" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="#ff6b6b"/>
                        <stop offset="60%" stop-color="#ef4444"/>
                        <stop offset="100%" stop-color="#991b1b"/>
                    </radialGradient>
                    <filter id="tl_glow1" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="3" result="blur"/>
                        <feComposite in="SourceGraphic" in2="blur" operator="over"/>
                    </filter>
                </defs>
                <rect width="100" height="100" rx="12" fill="#e2e8f0"/>
                <rect x="47" y="65" width="6" height="35" fill="#475569" rx="2"/>
                <rect x="34" y="10" width="32" height="60" rx="8" fill="#1e293b" stroke="#0f172a" stroke-width="2"/>
                <!-- Visors -->
                <path d="M36 22 Q50 16 64 22" fill="none" stroke="#334155" stroke-width="2.5"/>
                <path d="M36 40 Q50 34 64 40" fill="none" stroke="#334155" stroke-width="2.5"/>
                <path d="M36 58 Q50 52 64 58" fill="none" stroke="#334155" stroke-width="2.5"/>
                <!-- Lights -->
                <circle cx="50" cy="22" r="7" fill="url(#tl_red)" filter="url(#tl_glow1)"/>
                <circle cx="50" cy="40" r="6.5" fill="#713f12" opacity="0.6"/>
                <circle cx="50" cy="58" r="6.5" fill="#14532d" opacity="0.6"/>
            </svg>`,
            // Variant 2: Green light active
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <defs>
                    <radialGradient id="tl_green" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="#86efac"/>
                        <stop offset="60%" stop-color="#22c55e"/>
                        <stop offset="100%" stop-color="#15803d"/>
                    </radialGradient>
                </defs>
                <rect width="100" height="100" rx="12" fill="#cbd5e1"/>
                <rect x="47" y="65" width="6" height="35" fill="#475569" rx="2"/>
                <rect x="34" y="10" width="32" height="60" rx="8" fill="#1e293b"/>
                <circle cx="50" cy="22" r="6.5" fill="#7f1d1d" opacity="0.6"/>
                <circle cx="50" cy="40" r="6.5" fill="#713f12" opacity="0.6"/>
                <circle cx="50" cy="58" r="7" fill="url(#tl_green)"/>
                <circle cx="50" cy="58" r="9" fill="#22c55e" opacity="0.3"/>
            </svg>`,
            // Variant 3: Yellow light active
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <defs>
                    <radialGradient id="tl_yellow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="#fef08a"/>
                        <stop offset="60%" stop-color="#eab308"/>
                        <stop offset="100%" stop-color="#a16207"/>
                    </radialGradient>
                </defs>
                <rect width="100" height="100" rx="12" fill="#e2e8f0"/>
                <rect x="47" y="65" width="6" height="35" fill="#334155" rx="2"/>
                <rect x="34" y="10" width="32" height="60" rx="8" fill="#0f172a"/>
                <circle cx="50" cy="22" r="6.5" fill="#7f1d1d" opacity="0.6"/>
                <circle cx="50" cy="40" r="7" fill="url(#tl_yellow)"/>
                <circle cx="50" cy="58" r="6.5" fill="#14532d" opacity="0.6"/>
            </svg>`,
            // Variant 4: Dual pedestrian / intersection light
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f1f5f9"/>
                <rect x="46" y="60" width="8" height="40" fill="#64748b"/>
                <rect x="32" y="14" width="36" height="50" rx="6" fill="#1e293b"/>
                <!-- Upper red hand -->
                <circle cx="50" cy="27" r="8" fill="#ef4444"/>
                <path d="M48 24 L52 24 L52 30 L48 30 Z" fill="#ffffff"/>
                <!-- Lower walking man green -->
                <circle cx="50" cy="48" r="8" fill="#10b981"/>
                <circle cx="50" cy="45" r="2.5" fill="#ffffff"/>
                <path d="M48 48 L52 48 L53 53 L47 53 Z" fill="#ffffff"/>
            </svg>`
        ],

        car: [
            // Variant 1: Red sporty sedan
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#e0f2fe"/>
                <path d="M0 72 L100 72" stroke="#94a3b8" stroke-width="4"/>
                <!-- Car body -->
                <path d="M12 58 Q15 50 25 48 L36 34 Q40 30 52 30 L66 30 Q74 30 78 38 L88 48 Q94 52 94 58 L92 65 L12 65 Z" fill="#dc2626"/>
                <!-- Windows -->
                <path d="M38 46 L39 36 Q42 34 50 34 L50 46 Z" fill="#bae6fd"/>
                <path d="M54 46 L54 34 L65 34 Q70 34 74 41 L76 46 Z" fill="#bae6fd"/>
                <!-- Headlight & taillight -->
                <path d="M88 52 L93 54 L92 58 L86 56 Z" fill="#fef08a"/>
                <path d="M12 54 L14 54 L14 59 L12 59 Z" fill="#f87171"/>
                <!-- Wheels -->
                <circle cx="28" cy="65" r="8.5" fill="#1e293b"/>
                <circle cx="28" cy="65" r="4" fill="#94a3b8"/>
                <circle cx="76" cy="65" r="8.5" fill="#1e293b"/>
                <circle cx="76" cy="65" r="4" fill="#94a3b8"/>
            </svg>`,
            // Variant 2: Blue modern SUV
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#eff6ff"/>
                <path d="M0 74 L100 74" stroke="#94a3b8" stroke-width="4"/>
                <!-- Roof rack -->
                <line x1="32" y1="28" x2="68" y2="28" stroke="#334155" stroke-width="2.5"/>
                <!-- Body -->
                <path d="M10 60 L14 42 Q16 38 24 36 L30 32 Q34 30 42 30 L72 30 Q78 30 84 38 L92 46 Q95 50 95 62 L90 67 L10 67 Z" fill="#2563eb"/>
                <!-- Glass -->
                <rect x="34" y="34" width="16" height="12" rx="2" fill="#bfdbfe"/>
                <rect x="54" y="34" width="20" height="12" rx="2" fill="#bfdbfe"/>
                <!-- Wheels -->
                <circle cx="26" cy="67" r="9.5" fill="#0f172a"/>
                <circle cx="26" cy="67" r="4.5" fill="#cbd5e1"/>
                <circle cx="76" cy="67" r="9.5" fill="#0f172a"/>
                <circle cx="76" cy="67" r="4.5" fill="#cbd5e1"/>
            </svg>`,
            // Variant 3: Silver compact car
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f8fafc"/>
                <path d="M0 72 L100 72" stroke="#cbd5e1" stroke-width="4"/>
                <path d="M14 62 Q16 52 26 50 L38 36 Q42 32 54 32 L66 32 Q72 32 78 40 L88 50 Q92 54 92 62 Z" fill="#64748b"/>
                <path d="M40 47 L42 37 Q46 36 53 36 L53 47 Z" fill="#e2e8f0"/>
                <path d="M57 47 L57 36 L66 36 Q70 36 74 42 L76 47 Z" fill="#e2e8f0"/>
                <circle cx="30" cy="64" r="8" fill="#1e293b"/>
                <circle cx="30" cy="64" r="3.5" fill="#f1f5f9"/>
                <circle cx="74" cy="64" r="8" fill="#1e293b"/>
                <circle cx="74" cy="64" r="3.5" fill="#f1f5f9"/>
            </svg>`,
            // Variant 4: Yellow taxi cab
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#fefce8"/>
                <path d="M0 73 L100 73" stroke="#94a3b8" stroke-width="4"/>
                <!-- Taxi sign -->
                <rect x="46" y="27" width="14" height="6" rx="2" fill="#ffffff" stroke="#1e293b" stroke-width="1.5"/>
                <path d="M12 60 Q15 50 26 48 L36 36 Q40 33 50 33 L68 33 Q76 33 80 40 L90 50 Q94 54 94 62 Z" fill="#eab308"/>
                <!-- Windows -->
                <path d="M38 46 L40 37 Q43 35 50 35 L50 46 Z" fill="#38bdf8"/>
                <path d="M54 46 L54 35 L66 35 Q71 35 75 42 L77 46 Z" fill="#38bdf8"/>
                <!-- Checker band -->
                <rect x="24" y="52" width="60" height="4" fill="#000000" stroke="#facc15" stroke-dasharray="4 4"/>
                <circle cx="28" cy="65" r="8" fill="#1e293b"/>
                <circle cx="76" cy="65" r="8" fill="#1e293b"/>
            </svg>`
        ],

        bus: [
            // Variant 1: Yellow school bus
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#fef9c3"/>
                <path d="M0 75 L100 75" stroke="#94a3b8" stroke-width="4"/>
                <rect x="12" y="26" width="76" height="38" rx="6" fill="#f59e0b"/>
                <!-- Windows -->
                <rect x="16" y="32" width="12" height="14" rx="2" fill="#bae6fd"/>
                <rect x="32" y="32" width="12" height="14" rx="2" fill="#bae6fd"/>
                <rect x="48" y="32" width="12" height="14" rx="2" fill="#bae6fd"/>
                <rect x="64" y="32" width="18" height="16" rx="2" fill="#bae6fd"/>
                <!-- Black stripe -->
                <rect x="12" y="52" width="76" height="4" fill="#1e293b"/>
                <!-- Wheels -->
                <circle cx="28" cy="66" r="9" fill="#0f172a"/>
                <circle cx="28" cy="66" r="4" fill="#94a3b8"/>
                <circle cx="72" cy="66" r="9" fill="#0f172a"/>
                <circle cx="72" cy="66" r="4" fill="#94a3b8"/>
            </svg>`,
            // Variant 2: Blue transit city bus
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f0f9ff"/>
                <path d="M0 75 L100 75" stroke="#cbd5e1" stroke-width="4"/>
                <rect x="10" y="24" width="80" height="40" rx="5" fill="#0284c7"/>
                <rect x="10" y="44" width="80" height="20" rx="2" fill="#ffffff"/>
                <!-- Windows band -->
                <rect x="14" y="28" width="14" height="14" rx="2" fill="#38bdf8"/>
                <rect x="32" y="28" width="14" height="14" rx="2" fill="#38bdf8"/>
                <rect x="50" y="28" width="14" height="14" rx="2" fill="#38bdf8"/>
                <rect x="68" y="28" width="18" height="16" rx="2" fill="#38bdf8"/>
                <circle cx="26" cy="66" r="8.5" fill="#1e293b"/>
                <circle cx="74" cy="66" r="8.5" fill="#1e293b"/>
            </svg>`,
            // Variant 3: Red double decker bus
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#fee2e2"/>
                <path d="M0 76 L100 76" stroke="#94a3b8" stroke-width="4"/>
                <rect x="14" y="16" width="72" height="50" rx="6" fill="#dc2626"/>
                <!-- Upper windows -->
                <rect x="18" y="21" width="14" height="10" rx="2" fill="#ffffff"/>
                <rect x="36" y="21" width="14" height="10" rx="2" fill="#ffffff"/>
                <rect x="54" y="21" width="14" height="10" rx="2" fill="#ffffff"/>
                <rect x="72" y="21" width="10" height="10" rx="2" fill="#ffffff"/>
                <!-- Lower windows -->
                <rect x="18" y="38" width="14" height="11" rx="2" fill="#ffffff"/>
                <rect x="36" y="38" width="14" height="11" rx="2" fill="#ffffff"/>
                <rect x="54" y="38" width="14" height="11" rx="2" fill="#ffffff"/>
                <circle cx="28" cy="68" r="8.5" fill="#1e293b"/>
                <circle cx="72" cy="68" r="8.5" fill="#1e293b"/>
            </svg>`,
            // Variant 4: Green eco shuttle
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#ecfdf5"/>
                <path d="M0 74 L100 74" stroke="#a7f3d0" stroke-width="4"/>
                <path d="M12 62 L12 34 Q12 28 20 28 L72 28 Q84 28 88 40 L88 62 Z" fill="#059669"/>
                <!-- Big panoramic window -->
                <path d="M20 34 L70 34 Q78 34 82 42 L82 48 L20 48 Z" fill="#a7f3d0"/>
                <circle cx="28" cy="65" r="8" fill="#064e3b"/>
                <circle cx="72" cy="65" r="8" fill="#064e3b"/>
            </svg>`
        ],

        bicycle: [
            // Variant 1: Orange Mountain bike
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#fff7ed"/>
                <path d="M0 78 L100 78" stroke="#cbd5e1" stroke-width="4"/>
                <!-- Wheels -->
                <circle cx="25" cy="58" r="16" fill="none" stroke="#1e293b" stroke-width="4.5"/>
                <circle cx="75" cy="58" r="16" fill="none" stroke="#1e293b" stroke-width="4.5"/>
                <circle cx="25" cy="58" r="2" fill="#ea580c"/>
                <circle cx="75" cy="58" r="2" fill="#ea580c"/>
                <!-- Frame -->
                <path d="M25 58 L46 58 L62 44 L38 44 Z" fill="none" stroke="#ea580c" stroke-width="4" stroke-linejoin="round"/>
                <path d="M46 58 L42 36" stroke="#ea580c" stroke-width="4"/>
                <!-- Seat -->
                <path d="M36 36 L48 36" stroke="#1e293b" stroke-width="4.5" stroke-linecap="round"/>
                <!-- Handlebar & front fork -->
                <path d="M75 58 L64 36 L58 36" fill="none" stroke="#1e293b" stroke-width="4" stroke-linecap="round"/>
            </svg>`,
            // Variant 2: Teal city bike with basket
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f0fdfa"/>
                <circle cx="24" cy="60" r="15" fill="none" stroke="#334155" stroke-width="3.5"/>
                <circle cx="76" cy="60" r="15" fill="none" stroke="#334155" stroke-width="3.5"/>
                <!-- Step through curved frame -->
                <path d="M24 60 L46 60 Q52 56 64 45 L76 60" fill="none" stroke="#0d9488" stroke-width="3.5"/>
                <path d="M46 60 L42 42" stroke="#0d9488" stroke-width="3.5"/>
                <!-- Seat -->
                <path d="M37 42 L47 42" stroke="#78350f" stroke-width="4" stroke-linecap="round"/>
                <!-- Front basket -->
                <rect x="68" y="36" width="14" height="10" rx="2" fill="#b45309" stroke="#78350f"/>
                <path d="M64 45 L68 36" stroke="#334155" stroke-width="3"/>
            </svg>`,
            // Variant 3: Blue road racing bicycle
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#eff6ff"/>
                <circle cx="24" cy="58" r="16" fill="none" stroke="#0f172a" stroke-width="3"/>
                <circle cx="76" cy="58" r="16" fill="none" stroke="#0f172a" stroke-width="3"/>
                <path d="M24 58 L46 58 L66 40 L38 40 Z" fill="none" stroke="#2563eb" stroke-width="3.5" stroke-linejoin="round"/>
                <path d="M46 58 L41 34" stroke="#2563eb" stroke-width="3.5"/>
                <path d="M35 34 L46 34" stroke="#0f172a" stroke-width="3.5" stroke-linecap="round"/>
                <!-- Drop bar -->
                <path d="M76 58 L66 38 Q64 34 68 32 Q74 32 72 38" fill="none" stroke="#0f172a" stroke-width="3.5"/>
            </svg>`,
            // Variant 4: Classic retro bicycle
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#faf5ff"/>
                <circle cx="25" cy="58" r="15" fill="none" stroke="#475569" stroke-width="4"/>
                <circle cx="75" cy="58" r="15" fill="none" stroke="#475569" stroke-width="4"/>
                <!-- Fenders -->
                <path d="M12 52 A 16 16 0 0 1 38 52" fill="none" stroke="#9333ea" stroke-width="3"/>
                <path d="M62 52 A 16 16 0 0 1 88 52" fill="none" stroke="#9333ea" stroke-width="3"/>
                <path d="M25 58 L48 58 L64 42 L38 42 Z" fill="none" stroke="#9333ea" stroke-width="3.5"/>
                <path d="M75 58 L64 36 L60 36" fill="none" stroke="#475569" stroke-width="3.5"/>
            </svg>`
        ],

        traffic_sign: [
            // Variant 1: Red octagonal STOP sign
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f1f5f9"/>
                <rect x="47" y="55" width="6" height="45" fill="#64748b"/>
                <!-- Octagon -->
                <polygon points="32,15 68,15 85,32 85,68 68,85 32,85 15,68 15,32" fill="#dc2626" stroke="#ffffff" stroke-width="3"/>
                <text x="50" y="57" font-size="19" font-weight="900" fill="#ffffff" text-anchor="middle" font-family="Arial, sans-serif">STOP</text>
            </svg>`,
            // Variant 2: Yellow triangular warning sign
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f8fafc"/>
                <rect x="47" y="55" width="6" height="45" fill="#64748b"/>
                <polygon points="50,14 88,78 12,78" fill="#facc15" stroke="#1e293b" stroke-width="4" stroke-linejoin="round"/>
                <!-- Exclamation mark -->
                <rect x="47" y="34" width="6" height="22" rx="3" fill="#1e293b"/>
                <circle cx="50" cy="66" r="3.5" fill="#1e293b"/>
            </svg>`,
            // Variant 3: Blue circular direction sign
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f1f5f9"/>
                <rect x="47" y="55" width="6" height="45" fill="#64748b"/>
                <circle cx="50" cy="46" r="32" fill="#2563eb" stroke="#ffffff" stroke-width="3"/>
                <!-- White arrow -->
                <path d="M50 26 L64 42 L54 42 L54 62 L46 62 L46 42 L36 42 Z" fill="#ffffff"/>
            </svg>`,
            // Variant 4: Red circular speed limit 50 sign
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f8fafc"/>
                <rect x="47" y="55" width="6" height="45" fill="#64748b"/>
                <circle cx="50" cy="46" r="32" fill="#ffffff" stroke="#dc2626" stroke-width="7"/>
                <text x="50" y="56" font-size="28" font-weight="900" fill="#0f172a" text-anchor="middle" font-family="Arial, sans-serif">50</text>
            </svg>`
        ],

        tree: [
            // Variant 1: Deciduous oak tree
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#ecfdf5"/>
                <!-- Ground -->
                <ellipse cx="50" cy="85" rx="36" ry="6" fill="#bbf7d0"/>
                <!-- Trunk -->
                <path d="M44 85 L46 54 L54 54 L56 85 Z" fill="#78350f"/>
                <!-- Foliage -->
                <circle cx="36" cy="44" r="18" fill="#16a34a"/>
                <circle cx="64" cy="44" r="18" fill="#16a34a"/>
                <circle cx="50" cy="30" r="20" fill="#22c55e"/>
            </svg>`,
            // Variant 2: Tropical palm tree
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#fefce8"/>
                <ellipse cx="50" cy="88" rx="34" ry="5" fill="#fef08a"/>
                <!-- Curved trunk -->
                <path d="M48 88 Q44 55 52 35 L56 36 Q48 55 52 88 Z" fill="#92400e"/>
                <!-- Fronds -->
                <path d="M54 35 Q30 25 18 36" stroke="#15803d" stroke-width="5" fill="none" stroke-linecap="round"/>
                <path d="M54 35 Q40 12 30 18" stroke="#16a34a" stroke-width="5" fill="none" stroke-linecap="round"/>
                <path d="M54 35 Q65 12 78 20" stroke="#16a34a" stroke-width="5" fill="none" stroke-linecap="round"/>
                <path d="M54 35 Q80 25 86 38" stroke="#15803d" stroke-width="5" fill="none" stroke-linecap="round"/>
                <!-- Coconuts -->
                <circle cx="51" cy="38" r="3.5" fill="#78350f"/>
                <circle cx="57" cy="38" r="3.5" fill="#78350f"/>
            </svg>`,
            // Variant 3: Evergreen pine tree
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f0fdf4"/>
                <rect x="46" y="70" width="8" height="18" fill="#713f12"/>
                <!-- Tiers -->
                <polygon points="50,14 74,38 26,38" fill="#15803d"/>
                <polygon points="50,30 78,54 22,54" fill="#166534"/>
                <polygon points="50,46 82,72 18,72" fill="#14532d"/>
            </svg>`,
            // Variant 4: Cherry blossom tree
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#fdf2f8"/>
                <ellipse cx="50" cy="85" rx="34" ry="5" fill="#fbcfe8"/>
                <path d="M45 85 L48 50 L52 50 L55 85 Z" fill="#581c87"/>
                <!-- Pink blossoms -->
                <circle cx="36" cy="44" r="17" fill="#f472b6"/>
                <circle cx="64" cy="44" r="17" fill="#f472b6"/>
                <circle cx="50" cy="30" r="19" fill="#fbcfe8"/>
            </svg>`
        ],

        house: [
            // Variant 1: Suburban house with red roof
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f8fafc"/>
                <!-- Chimney -->
                <rect x="64" y="22" width="7" height="16" fill="#b91c1c"/>
                <!-- Roof -->
                <polygon points="50,18 86,46 14,46" fill="#dc2626"/>
                <!-- Wall -->
                <rect x="22" y="46" width="56" height="38" fill="#fed7aa"/>
                <!-- Door -->
                <rect x="43" y="60" width="14" height="24" rx="2" fill="#78350f"/>
                <!-- Windows -->
                <rect x="27" y="52" width="10" height="10" rx="1" fill="#bae6fd" stroke="#475569" stroke-width="1.5"/>
                <rect x="63" y="52" width="10" height="10" rx="1" fill="#bae6fd" stroke="#475569" stroke-width="1.5"/>
            </svg>`,
            // Variant 2: Modern 2-story villa
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f1f5f9"/>
                <!-- Main cube -->
                <rect x="18" y="32" width="64" height="52" rx="3" fill="#ffffff" stroke="#94a3b8" stroke-width="2"/>
                <!-- Large balcony windows -->
                <rect x="24" y="38" width="24" height="16" fill="#38bdf8"/>
                <rect x="52" y="38" width="24" height="16" fill="#38bdf8"/>
                <rect x="24" y="62" width="18" height="22" fill="#0284c7"/>
                <rect x="52" y="62" width="14" height="22" fill="#334155"/>
            </svg>`,
            // Variant 3: Wooden rustic cabin
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#fef3c7"/>
                <polygon points="50,22 84,48 16,48" fill="#78350f"/>
                <rect x="22" y="48" width="56" height="36" fill="#b45309"/>
                <!-- Log lines -->
                <line x1="22" y1="56" x2="78" y2="56" stroke="#78350f" stroke-width="2"/>
                <line x1="22" y1="66" x2="78" y2="66" stroke="#78350f" stroke-width="2"/>
                <line x1="22" y1="76" x2="78" y2="76" stroke="#78350f" stroke-width="2"/>
                <rect x="44" y="60" width="12" height="24" fill="#451a03"/>
            </svg>`,
            // Variant 4: Townhouse
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f3e8ff"/>
                <polygon points="50,16 78,34 22,34" fill="#6b21a8"/>
                <rect x="26" y="34" width="48" height="50" fill="#e9d5ff"/>
                <rect x="32" y="40" width="10" height="10" fill="#9333ea"/>
                <rect x="58" y="40" width="10" height="10" fill="#9333ea"/>
                <rect x="32" y="56" width="10" height="10" fill="#9333ea"/>
                <rect x="58" y="56" width="10" height="10" fill="#9333ea"/>
                <rect x="44" y="68" width="12" height="16" fill="#581c87"/>
            </svg>`
        ],

        boat: [
            // Variant 1: White sailboat on blue waves
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f0f9ff"/>
                <!-- Mast -->
                <line x1="50" y1="16" x2="50" y2="64" stroke="#475569" stroke-width="3"/>
                <!-- Mainsail -->
                <path d="M50 20 L76 56 L50 56 Z" fill="#0284c7"/>
                <!-- Jib sail -->
                <path d="M47 24 L26 56 L47 56 Z" fill="#38bdf8"/>
                <!-- Hull -->
                <path d="M18 64 L82 64 Q74 76 50 76 Q26 76 18 64 Z" fill="#ffffff" stroke="#0f172a" stroke-width="2"/>
                <!-- Waves -->
                <path d="M4 76 Q16 72 28 76 Q40 80 52 76 Q64 72 76 76 Q88 80 96 76" stroke="#0ea5e9" stroke-width="3" fill="none"/>
            </svg>`,
            // Variant 2: Speedboat / Yacht
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#e0f2fe"/>
                <!-- Cabin -->
                <path d="M36 44 L58 44 L66 54 L30 54 Z" fill="#0369a1"/>
                <rect x="40" y="46" width="14" height="6" fill="#e0f2fe"/>
                <!-- Sleek hull -->
                <path d="M12 56 L88 56 Q82 72 45 72 L18 72 Z" fill="#ffffff" stroke="#0284c7" stroke-width="2"/>
                <path d="M0 72 Q25 66 50 72 Q75 78 100 72" stroke="#38bdf8" stroke-width="4" fill="none"/>
            </svg>`,
            // Variant 3: Wooden rowboat
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#ecfeff"/>
                <!-- Oars -->
                <line x1="28" y1="36" x2="68" y2="72" stroke="#78350f" stroke-width="3"/>
                <line x1="72" y1="36" x2="32" y2="72" stroke="#78350f" stroke-width="3"/>
                <!-- Hull -->
                <path d="M16 54 L84 54 Q72 72 50 72 Q28 72 16 54 Z" fill="#92400e" stroke="#451a03" stroke-width="2"/>
                <!-- Bench -->
                <rect x="44" y="56" width="12" height="4" fill="#d97706"/>
                <path d="M0 74 Q25 70 50 74 Q75 78 100 74" stroke="#06b6d4" stroke-width="3" fill="none"/>
            </svg>`,
            // Variant 4: Ferry ship
            `<svg viewBox="0 0 100 100" class="w-full h-full p-2 select-none pointer-events-none">
                <rect width="100" height="100" rx="12" fill="#f1f5f9"/>
                <!-- Funnel -->
                <rect x="52" y="28" width="8" height="12" fill="#dc2626"/>
                <!-- Decks -->
                <rect x="26" y="38" width="46" height="16" fill="#ffffff" stroke="#94a3b8"/>
                <circle cx="34" cy="46" r="2.5" fill="#0284c7"/>
                <circle cx="48" cy="46" r="2.5" fill="#0284c7"/>
                <circle cx="62" cy="46" r="2.5" fill="#0284c7"/>
                <!-- Hull -->
                <path d="M14 54 L86 54 L76 72 L22 72 Z" fill="#1e293b"/>
                <path d="M0 74 Q25 70 50 74 Q75 78 100 74" stroke="#0284c7" stroke-width="3" fill="none"/>
            </svg>`
        ]
    };

    // Category display names in Vietnamese
    const CATEGORY_NAMES = {
        traffic_light: 'Đèn giao thông',
        car: 'Xe hơi / Ô tô',
        bus: 'Xe buýt',
        bicycle: 'Xe đạp',
        traffic_sign: 'Biển báo giao thông',
        tree: 'Cây xanh',
        house: 'Ngôi nhà',
        boat: 'Thuyền / Tàu thủy'
    };

    const CATEGORY_KEYS = Object.keys(ASSETS);

    // --- 2. STATE MANAGER ---
    let currentChallenge = null;
    let selectedIndices = new Set();
    let isVerified = false;

    // --- 3. DOM INJECTION FOR CHALLENGE MODAL ---
    function ensureModalExists() {
        if (document.getElementById('captcha-modal')) return;

        const modalHtml = `
        <div id="captcha-modal" class="fixed inset-0 z-[9999] hidden items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 select-none">
            <div id="captcha-modal-box" class="bg-white w-full max-w-[390px] rounded-2xl shadow-2xl border border-slate-200 overflow-hidden transform transition-all duration-200 scale-95 opacity-0">
                <!-- Header -->
                <div class="bg-gradient-to-r from-blue-600 to-indigo-600 p-4 text-white relative">
                    <button type="button" id="captcha-close-btn" class="absolute top-3.5 right-3.5 text-white/70 hover:text-white transition-colors cursor-pointer" title="Đóng">
                        <span class="material-symbols-outlined text-[20px]">close</span>
                    </button>
                    <p class="text-[11px] uppercase tracking-wider text-blue-100 font-bold mb-0.5">Xác minh bảo mật</p>
                    <h4 class="text-sm font-medium leading-snug">
                        Chọn tất cả các hình ảnh có chứa:
                    </h4>
                    <div id="captcha-target-name" class="text-lg sm:text-xl font-black uppercase tracking-wide text-yellow-300 mt-0.5">
                        --
                    </div>
                    <p class="text-[11px] text-blue-100/90 mt-1">
                        Nếu không có hình nào phù hợp, nhấn Bỏ qua / Xác minh.
                    </p>
                </div>

                <!-- Alert Message -->
                <div id="captcha-alert" class="hidden px-4 py-2 bg-rose-50 border-b border-rose-200 text-rose-600 text-xs font-bold flex items-center gap-1.5">
                    <span class="material-symbols-outlined text-[16px]">error</span>
                    <span id="captcha-alert-text">Chưa chính xác. Vui lòng thử lại với câu đố mới.</span>
                </div>

                <!-- 3x3 Grid -->
                <div class="p-2.5 bg-slate-100">
                    <div id="captcha-grid" class="grid grid-cols-3 gap-2">
                        <!-- 9 tiles rendered dynamically -->
                    </div>
                </div>

                <!-- Footer -->
                <div class="px-4 py-3 bg-white border-t border-slate-200 flex items-center justify-between">
                    <div class="flex items-center gap-1 text-slate-500">
                        <button type="button" id="captcha-reload-btn" title="Đổi câu đố khác" class="w-8 h-8 rounded-lg hover:bg-slate-100 active:scale-95 flex items-center justify-center transition-all cursor-pointer">
                            <span class="material-symbols-outlined text-[20px]">refresh</span>
                        </button>
                        <button type="button" id="captcha-help-btn" title="Hướng dẫn" class="w-8 h-8 rounded-lg hover:bg-slate-100 active:scale-95 flex items-center justify-center transition-all cursor-pointer">
                            <span class="material-symbols-outlined text-[20px]">help_outline</span>
                        </button>
                    </div>
                    <button type="button" id="captcha-verify-btn" class="bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-extrabold px-6 py-2 rounded-xl text-xs uppercase tracking-wider shadow-sm hover:shadow transition-all cursor-pointer">
                        Xác minh
                    </button>
                </div>
            </div>
        </div>`;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Bind events
        document.getElementById('captcha-close-btn').addEventListener('click', closeModal);
        document.getElementById('captcha-reload-btn').addEventListener('click', () => generateNewChallenge());
        document.getElementById('captcha-help-btn').addEventListener('click', showHelpTip);
        document.getElementById('captcha-verify-btn').addEventListener('click', handleVerifyClick);

        // Close on background click
        document.getElementById('captcha-modal').addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });
    }

    // --- 4. GENERATE 3x3 CHALLENGE ---
    function generateNewChallenge(keepAlert = false) {
        if (!keepAlert) {
            hideAlert();
        }

        selectedIndices.clear();

        // 1. Pick a target category
        const targetCategory = CATEGORY_KEYS[Math.floor(Math.random() * CATEGORY_KEYS.length)];
        const targetLabel = CATEGORY_NAMES[targetCategory];

        // 2. Decide how many target tiles (between 3 and 4)
        const numTargets = Math.random() < 0.5 ? 3 : 4;
        const numDistractors = 9 - numTargets;

        // 3. Pick target variants
        const targetVariants = [...ASSETS[targetCategory]];
        shuffleArray(targetVariants);
        const chosenTargetVariants = targetVariants.slice(0, numTargets);

        // 4. Pick distractor variants from other categories
        const otherCategories = CATEGORY_KEYS.filter(c => c !== targetCategory);
        shuffleArray(otherCategories);

        const distractorPool = [];
        otherCategories.forEach(cat => {
            const vars = [...ASSETS[cat]];
            shuffleArray(vars);
            vars.forEach(v => distractorPool.push({ category: cat, svg: v }));
        });
        shuffleArray(distractorPool);
        const chosenDistractors = distractorPool.slice(0, numDistractors);

        // 5. Combine and shuffle into 9 tiles
        const tiles = [];
        chosenTargetVariants.forEach(svg => {
            tiles.push({ isTarget: true, category: targetCategory, svg });
        });
        chosenDistractors.forEach(d => {
            tiles.push({ isTarget: false, category: d.category, svg: d.svg });
        });
        shuffleArray(tiles);

        currentChallenge = {
            targetCategory,
            targetLabel,
            tiles,
            targetIndices: new Set(tiles.map((t, idx) => t.isTarget ? idx : null).filter(idx => idx !== null))
        };

        // Render UI
        document.getElementById('captcha-target-name').textContent = targetLabel;
        renderGrid(tiles);
    }

    function renderGrid(tiles) {
        const grid = document.getElementById('captcha-grid');
        grid.innerHTML = '';

        tiles.forEach((tile, index) => {
            const tileEl = document.createElement('div');
            tileEl.className = 'relative aspect-square bg-white rounded-xl border border-slate-200 cursor-pointer overflow-hidden transition-all duration-150 flex items-center justify-center hover:shadow-md active:scale-95 group';
            tileEl.dataset.index = index;

            tileEl.innerHTML = `
                ${tile.svg}
                <div class="captcha-badge hidden absolute top-1.5 right-1.5 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-md animate-pop">
                    <span class="material-symbols-outlined text-[16px] font-bold">check</span>
                </div>
            `;

            tileEl.addEventListener('click', () => toggleTileSelection(index, tileEl));
            grid.appendChild(tileEl);
        });
    }

    function toggleTileSelection(index, tileEl) {
        const badge = tileEl.querySelector('.captcha-badge');
        if (selectedIndices.has(index)) {
            selectedIndices.delete(index);
            tileEl.classList.remove('ring-4', 'ring-blue-500', 'ring-inset', 'scale-[0.96]', 'bg-blue-50/40');
            badge.classList.add('hidden');
        } else {
            selectedIndices.add(index);
            tileEl.classList.add('ring-4', 'ring-blue-500', 'ring-inset', 'scale-[0.96]', 'bg-blue-50/40');
            badge.classList.remove('hidden');
        }
    }

    // --- 5. VERIFICATION LOGIC ---
    function handleVerifyClick() {
        if (!currentChallenge) return;

        const targetIndices = currentChallenge.targetIndices;

        // Check exact match
        let isCorrect = (selectedIndices.size === targetIndices.size);
        if (isCorrect) {
            for (const idx of selectedIndices) {
                if (!targetIndices.has(idx)) {
                    isCorrect = false;
                    break;
                }
            }
        }

        if (isCorrect) {
            // SUCCESS
            markSuccess();
        } else {
            // FAILED - Shake and reset
            const modalBox = document.getElementById('captcha-modal-box');
            modalBox.classList.remove('shake-animate');
            void modalBox.offsetWidth; // trigger reflow
            modalBox.classList.add('shake-animate');

            showAlert('Chưa chính xác! Vui lòng chọn lại theo câu đố mới.');

            setTimeout(() => {
                modalBox.classList.remove('shake-animate');
                generateNewChallenge(true);
            }, 600);
        }
    }

    function markSuccess() {
        isVerified = true;
        closeModal();

        // Update Trigger Checkbox on Form
        const humanCheckbox = document.getElementById('human-checkbox');
        const checkboxVisual = document.getElementById('checkbox-visual');
        const captchaSpinner = document.getElementById('captcha-spinner');
        const captchaCheck = document.getElementById('captcha-check');
        const captchaLabel = document.getElementById('captcha-label');
        const captchaSubtext = document.getElementById('captcha-subtext');
        const humanVerified = document.getElementById('human_verified');
        const captchaContainer = document.getElementById('captcha-container');
        const captchaErrorMsg = document.getElementById('captcha-error-msg');

        if (humanCheckbox) humanCheckbox.checked = true;
        if (humanVerified) humanVerified.value = '1';

        if (checkboxVisual) {
            checkboxVisual.className = 'w-7 h-7 rounded-lg bg-emerald-500 border-2 border-emerald-500 flex items-center justify-center transition-all duration-200 shadow-xs shrink-0 captcha-pop';
        }
        if (captchaSpinner) captchaSpinner.classList.add('hidden');
        if (captchaCheck) captchaCheck.classList.remove('hidden');

        if (captchaLabel) {
            captchaLabel.textContent = 'Xác minh con người thành công';
            captchaLabel.className = 'text-sm font-extrabold text-emerald-700 transition-colors block';
        }
        if (captchaSubtext) {
            captchaSubtext.textContent = 'Đã hoàn tất kiểm tra an toàn hệ thống ✓';
            captchaSubtext.className = 'block text-[11px] text-emerald-600 font-medium';
        }

        if (captchaContainer) {
            captchaContainer.classList.remove('border-rose-400', 'bg-rose-50/50', 'border-slate-200', 'bg-slate-50/90');
            captchaContainer.classList.add('border-emerald-300', 'bg-emerald-50/40');
        }

        if (captchaErrorMsg) {
            captchaErrorMsg.classList.add('hidden');
        }
    }

    function openModal() {
        ensureModalExists();
        generateNewChallenge();

        const modal = document.getElementById('captcha-modal');
        const modalBox = document.getElementById('captcha-modal-box');

        modal.classList.remove('hidden');
        modal.classList.add('flex');

        requestAnimationFrame(() => {
            modalBox.classList.remove('scale-95', 'opacity-0');
            modalBox.classList.add('scale-100', 'opacity-100');
        });
    }

    function closeModal() {
        const modal = document.getElementById('captcha-modal');
        const modalBox = document.getElementById('captcha-modal-box');
        if (!modal) return;

        modalBox.classList.remove('scale-100', 'opacity-100');
        modalBox.classList.add('scale-95', 'opacity-0');

        setTimeout(() => {
            modal.classList.remove('flex');
            modal.classList.add('hidden');
        }, 150);
    }

    function showAlert(msg) {
        const alertEl = document.getElementById('captcha-alert');
        const alertText = document.getElementById('captcha-alert-text');
        if (alertEl && alertText) {
            alertText.textContent = msg;
            alertEl.classList.remove('hidden');
        }
    }

    function hideAlert() {
        const alertEl = document.getElementById('captcha-alert');
        if (alertEl) alertEl.classList.add('hidden');
    }

    function showHelpTip() {
        showAlert('Hãy bấm chọn tất cả hình vuông có chứa đồ vật được yêu cầu, sau đó bấm Xác minh.');
    }

    function shuffleArray(arr) {
        for (let i = arr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [arr[i], arr[j]] = [arr[j], arr[i]];
        }
        return arr;
    }

    // --- 6. ATTACH TO PAGE FORMS & TRIGGERS ---
    function initCaptchaWidget() {
        ensureModalExists();

        const trigger = document.getElementById('captcha-trigger');
        const humanCheckbox = document.getElementById('human-checkbox');
        const humanVerified = document.getElementById('human_verified');
        const captchaContainer = document.getElementById('captcha-container');
        const captchaErrorMsg = document.getElementById('captcha-error-msg');

        if (trigger) {
            trigger.addEventListener('click', function(e) {
                e.preventDefault();
                if (isVerified || (humanVerified && humanVerified.value === '1')) {
                    return;
                }
                openModal();
            });
        }

        // Handle Form Validation
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            if (form.contains(captchaContainer)) {
                form.addEventListener('submit', function(e) {
                    if (!humanVerified || humanVerified.value !== '1') {
                        e.preventDefault();
                        if (captchaErrorMsg) captchaErrorMsg.classList.remove('hidden');
                        if (captchaContainer) {
                            captchaContainer.classList.remove('border-slate-200', 'bg-slate-50/90');
                            captchaContainer.classList.add('border-rose-400', 'bg-rose-50/50', 'shake-animate');
                            setTimeout(() => {
                                captchaContainer.classList.remove('shake-animate');
                            }, 500);
                            captchaContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }
                });
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCaptchaWidget);
    } else {
        initCaptchaWidget();
    }
})();
