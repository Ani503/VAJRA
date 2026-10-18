---
name: VAJRA Operations Fleet Maintenance
colors:
  surface: '#101418'
  surface-dim: '#101418'
  surface-bright: '#363a3e'
  surface-container-lowest: '#0b0f12'
  surface-container-low: '#181c20'
  surface-container: '#1c2024'
  surface-container-high: '#262a2f'
  surface-container-highest: '#31353a'
  on-surface: '#e0e3e8'
  on-surface-variant: '#c5c8ba'
  inverse-surface: '#e0e3e8'
  inverse-on-surface: '#2d3135'
  outline: '#8f9285'
  outline-variant: '#45483e'
  surface-tint: '#b8ce96'
  primary: '#b8ce96'
  on-primary: '#25350c'
  primary-container: '#839864'
  on-primary-container: '#1e2e06'
  inverse-primary: '#516536'
  secondary: '#8ecdfc'
  on-secondary: '#00344d'
  secondary-container: '#025a83'
  on-secondary-container: '#92d1ff'
  tertiary: '#ebb7dc'
  on-tertiary: '#482441'
  tertiary-container: '#b282a4'
  on-tertiary-container: '#401d39'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d4ebb0'
  primary-fixed-dim: '#b8ce96'
  on-primary-fixed: '#111f00'
  on-primary-fixed-variant: '#3a4c21'
  secondary-fixed: '#c9e6ff'
  secondary-fixed-dim: '#8ecdfc'
  on-secondary-fixed: '#001e2f'
  on-secondary-fixed-variant: '#004c6e'
  tertiary-fixed: '#ffd7f1'
  tertiary-fixed-dim: '#ebb7dc'
  on-tertiary-fixed: '#300e2b'
  on-tertiary-fixed-variant: '#613a58'
  background: '#101418'
  on-background: '#e0e3e8'
  surface-variant: '#31353a'
typography:
  headline-xl:
    fontFamily: IBM Plex Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: IBM Plex Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.005em
  headline-md:
    fontFamily: IBM Plex Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-default:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-strong:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  label-default:
    fontFamily: IBM Plex Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-muted:
    fontFamily: IBM Plex Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  mono-metric:
    fontFamily: IBM Plex Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  mono-code:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

This design system is engineered for mission-critical defense fleet maintenance and operations tracking. Its aesthetic draws deliberate inspiration from high-density, professional developer and analyst tools such as Grafana, Linear, and Palantir Blueprint. The software rejects popular military sci-fi tropes—strictly prohibiting neon glows, decorative HUD brackets, synthetic lens flares, and artificial classification watermarks.

Instead, the UI communicates calm, authoritative clarity under high-cognitive-load conditions. The emotional response is one of dependable precision, situational awareness, and operational readiness. Visual rhythm is derived entirely from structural alignment, rigorous tabular densities, purposeful contrast tiers, and utilitarian ergonomics.

## Colors

The system uses a focused, low-fatigue dark palette designed for extended viewing across variable field and operations-center lighting conditions.

- **Background Canvas (`#14181C`)**: Muted charcoal-slate base canvas.
- **Surface & Panels (`#1C2127`)**: Elevated functional panels, sidebars, tables, and inspection panes.
- **Structural Borders (`#2B323A`)**: Crisp, 1px solid dividers defining every region and modular boundary.
- **Primary Text (`#E6E9EC`)**: High-legibility neutral text for titles, body rows, and metrics.
- **Secondary / Muted Text (`#9AA4AE`)**: De-emphasized metadata, units, and structural keys.
- **Brand Olive (`#6B7F4E`)**: Strictly reserved for the primary system mark and active top-level navigation indicators. It must not be used for generic interactions or decorative fills.
- **Steel Blue Accent (`#4C8DB8`)**: Interactive focus points, including active tab indicators, hyperlinked serials, row selection rings, and multi-select filters.

### Semantic Status Tokens
Semantic colors are strictly communicative and must never appear as decorative accents:
- **Healthy (`#3FA34D`)**: Nominal operational readiness, cleared components.
- **Watch (`#D9A21B`)**: Cautionary maintenance intervals, degraded sensor telemetry.
- **Critical (`#D64545`)**: Hard faults, grounded craft, mission-critical failure states.

## Typography

Typography relies on a dual-font structure built around sentence-case semantics and high-density technical readouts.

- **Primary Interface (IBM Plex Sans)**: Applied to all general navigation, headers, button labels, descriptions, and table headers. Avoid uppercase styling on UI labels; sentence-case is mandatory for rapid cognitive parsing. The baseline body size is 14px, with absolute minimum text anchored at 12px.
- **Technical Readouts (IBM Plex Mono)**: Reserved exclusively for serial numbers, tail codes, engine IDs, timestamps (UTC/IST), coordinate points, and numeric sensor feeds. This guarantees uniform tabular alignment and eliminates visual jitter during live telemetry polling.

## Layout & Spacing

The layout is built upon an uncompromising 12-column fluid grid system with uniform 24px (`1.5rem`) gutters and exterior view margins. 

The screen architecture is divided into three fixed horizontal areas:
1. **Utility Navigation Header**: 48px height, containing operational sector identification, network state, and global telemetry search.
2. **Modular Workspace**: Split-pane or multi-column data views accommodating master-detail lists, fleet inventory grids, and live telemetry graphs.
3. **Operational Status Bar**: Minimal 28px bottom shelf displaying connectivity, sync state, and clock (e.g., `Offline mode · Last sync 14:12 IST`).

Adaptive responsiveness follows clean reflow mechanics:
- **Desktop (1440px+)**: Full 12-column multi-panel inspection with simultaneous fleet lists and diagnostics.
- **Compact Desktop / Tablet Landscape (1024px–1439px)**: 12 columns collapse to 8 active units; inspection panels fold into drawer overlays.
- **Tactical / Tablet Portrait (<1024px)**: Single-column linear stack; tabular data converts to horizontally scrollable sheets with pinned identifier columns.

## Elevation & Depth

This design system is entirely shadow-free (`box-shadow: none`). Elevation and structural hierarchy are articulated exclusively through surface brightness variations and low-contrast perimeter rules:

- **Base Layer (`#14181C`)**: Canvas background.
- **Container Layer (`#1C2127`)**: Structural modules, cards, data grids, toolbars, and inspection drawers.
- **Interactive Layer (`#242B33`)**: Hover, press, and focused container states.
- **Divider Lines (`#2B323A`)**: Crisp 1px solid boundaries separating all columns, row borders, panel edges, and navigation tiers.

No blurred backdrops, glassmorphism, or skeuomorphic bevels are permitted. Z-index stacking (modals, tooltips, flyout menus) utilizes the surface color `#1C2127` bounded by a 1px solid `#4C8DB8` accent border on focus or a 1px solid `#2B323A` border on neutral display.

## Shapes

The design system maintains an intentional, engineered shape language. All interactive components, panels, data tables, status badges, and input elements use a fixed 4px (`0.25rem`) corner radius. 

Circular components are used only for status indicator dots (e.g., a 6px healthy/watch/critical dot). Pill shapes, exaggerated curves, and organic corner smoothing are explicitly disallowed to maintain structural rigidity and dense component tessellation.

## Components

### Buttons
- **Primary**: Solid background `#2B323A`, border 1px solid `#4C8DB8`, text `#E6E9EC`. Focus indicator is a 1px offset ring using `#4C8DB8`.
- **Secondary / Ghost**: Background transparent, border 1px solid `#2B323A`, text `#9AA4AE`. On hover, background shifts to `#1C2127` and text to `#E6E9EC`.
- **Destructive**: Background transparent, border 1px solid `#D64545`, text `#D64545`.

### Chips & Status Badges
- Compact rectangular tags (20px height) with 4px border radius.
- Background uses a 10% opacity wash of the respective semantic color, accompanied by a 1px solid border of the exact semantic token (`#3FA34D`, `#D9A21B`, or `#D64545`). Text is rendered in IBM Plex Mono at 12px using the solid status hue.

### Data Tables
- The core of the design system. Tables feature a fixed header with 1px solid `#2B323A` bottom border and `#14181C` background.
- Cell height is compact (36px). Alternating row fills are disabled; rows are separated by 1px solid `#2B323A` horizontal lines.
- Hovered rows highlight to `#242B33`. Selected rows display a 2px vertical border on the leading cell edge rendered in `#4C8DB8`.
- Identifiers (tail numbers, maintenance codes, timestamps) are strictly rendered in IBM Plex Mono.

### Inputs & Search
- Inputs feature background `#14181C`, border 1px solid `#2B323A`, text `#E6E9EC`, and placeholder `#9AA4AE`.
- On active focus, the border transitions cleanly to `#4C8DB8` with no glow or box-shadow.

### Checkboxes & Radios
- Size 14px by 14px with 2px corner radius for checkboxes, circular for radios.
- Unchecked: 1px solid `#2B323A` border, background `#14181C`.
- Checked: Background `#4C8DB8`, border `#4C8DB8`, interior checkmark `#14181C`.

### Diagnostic Panels & Cards
- Outer border 1px solid `#2B323A`, background `#1C2127`, padding 16px.
- Panel headers contain title in IBM Plex Sans (14px, semi-bold) and supplementary metrics in IBM Plex Mono (12px, `#9AA4AE`), divided by a 1px solid `#2B323A` baseline rule.