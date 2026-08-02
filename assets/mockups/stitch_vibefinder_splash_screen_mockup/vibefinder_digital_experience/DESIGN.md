---
name: VibeFinder Digital Experience
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#bccbb9'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#869585'
  outline-variant: '#3d4a3d'
  surface-tint: '#53e076'
  primary: '#53e076'
  on-primary: '#003914'
  primary-container: '#1db954'
  on-primary-container: '#004118'
  inverse-primary: '#006e2d'
  secondary: '#62dac0'
  on-secondary: '#00382e'
  secondary-container: '#13a38b'
  on-secondary-container: '#003028'
  tertiary: '#ffb3b3'
  on-tertiary: '#680114'
  tertiary-container: '#ff767b'
  on-tertiary-container: '#730a1b'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#72fe8f'
  primary-fixed-dim: '#53e076'
  on-primary-fixed: '#002108'
  on-primary-fixed-variant: '#005320'
  secondary-fixed: '#80f7dc'
  secondary-fixed-dim: '#62dac0'
  on-secondary-fixed: '#00201a'
  on-secondary-fixed-variant: '#005144'
  tertiary-fixed: '#ffdad9'
  tertiary-fixed-dim: '#ffb3b3'
  on-tertiary-fixed: '#400009'
  on-tertiary-fixed-variant: '#881d28'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 30px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 32px
  xl: 48px
  margin-mobile: 20px
  gutter-mobile: 12px
---

## Brand & Style

The design system is centered on a **Premium Minimalist** aesthetic, specifically tailored for a high-energy, dark-mode mobile environment. It draws inspiration from modern entertainment platforms, prioritizing high-contrast legibility and a sense of "active darkness."

The brand personality is energetic yet sophisticated. By utilizing a deep charcoal base with vibrant neon accents, the UI creates a focused atmosphere where content is the protagonist. The style is strictly **Flat**, eschewing gradients or skeuomorphism in favor of pure color blocks and strategic depth through colored ambient shadows. The emotional response should be one of confidence, speed, and nocturnal discovery.

## Colors

This design system utilizes a high-contrast dark palette to reduce eye strain and make the primary "Vibe" color pop. 

- **Primary (#1DB954):** Reserved for high-priority actions, active states, and critical brand moments. It should be used sparingly to maintain its impact.
- **Teal Accent (#14a38b):** Used for secondary interactive elements, categories, or success states to provide a sophisticated visual counterpoint to the primary green.
- **Background (#121212):** A solid, deep surface that provides a unified canvas. Avoid using lighter grays for large surfaces; use elevation layers instead.
- **Text:** Primary white is used for headings and critical data. Secondary gray is used for metadata, hints, and disabled states to establish a clear information hierarchy.

## Typography

The system relies exclusively on **Inter** to maintain a systematic, utilitarian, and modern feel. 

- **Headings:** Must always be Bold (700). Use tighter letter spacing for larger display sizes to create a "locked-in" editorial look.
- **Body:** Uses Regular (400) weight for maximum readability against the dark background. 
- **Labels:** Use Medium (500) or Semi-Bold (600) to ensure small text remains legible and distinguishable from body paragraphs.
- **Scaling:** For mobile, headlines should aggressively downscale while maintaining their bold weight to prevent awkward text wrapping on smaller devices.

## Layout & Spacing

This design system uses a **Fluid Grid** model optimized for mobile-first interaction. 

- **Grid:** A 4-column grid for mobile devices with 20px outer margins.
- **Rhythm:** All spacing must be a multiple of the 4px base unit. 
- **Hierarchy:** Use `md` (24px) for vertical padding between distinct content sections and `sm` (16px) for internal component padding.
- **Safe Areas:** Ensure all critical CTAs are placed within the thumb-zone (bottom 1/3rd of the screen) using fixed-bottom containers with 32px of bottom padding to clear system indicators.

## Elevation & Depth

While the design is "Flat," depth is communicated through **Tonal Layering** and **Luminous Shadows**.

1.  **Level 0 (Base):** #121212.
2.  **Level 1 (Cards/Surface):** Use a slightly lighter tint or a 1px subtle stroke (#FFFFFF at 10% opacity) to define boundaries.
3.  **Luminous Shadows:** Primary interactive elements (like the main CTA) use an ambient glow rather than a traditional black shadow. The shadow should be `rgba(29, 185, 84, 0.3)` with a 12px blur and 4px vertical offset.
4.  **Overlays:** Full-screen modals should use a 60% black wash to dim the background, keeping focus entirely on the foreground element.

## Shapes

The shape language is characterized by exaggerated roundness to soften the "hard" dark-mode aesthetic.

- **Primary Containers:** Cards, images, and modules must use a **24px (1.5rem)** corner radius.
- **Interactive Elements:** Buttons, chips, and input fields use a **Pill-shaped** (fully rounded) radius to signal touch-friendliness.
- **Icons:** Should follow a rounded cap and join style to match the container's softness.
- **Consistency:** Never mix sharp corners with rounded corners in the same view. Even small elements like checkboxes should have a minimum of 4px radius.

## Components

- **Buttons:**
    - **Primary:** Pill-shaped, Primary Green background, white text. Must include the green luminous shadow.
    - **Secondary:** Pill-shaped, 1px white border, no fill.
- **Cards:**
    - Background is #121212 with a 24px radius. Use a 1px border of `rgba(255,255,255,0.1)` for definition.
- **Inputs:**
    - Pill-shaped with a background of `rgba(255,255,255,0.05)`. Text is primary white, placeholder is secondary gray. On focus, the border changes to Teal Accent.
- **Chips/Badges:**
    - Small pill-shaped containers. Use Teal Accent for categories and Primary Green for "Active" or "Live" status indicators.
- **Lists:**
    - Standardized 72px row height for list items. Use 16px horizontal padding. Separators should be a 1px line of `rgba(255,255,255,0.05)`.
- **Haptic Feedback:**
    - All primary buttons and toggle components should be mapped to "Light" haptic feedback to reinforce the premium feel.