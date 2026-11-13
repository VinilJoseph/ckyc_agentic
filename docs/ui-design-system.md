# UI Design System & Visual Guidelines: CKYC Marketplace

> Visual design guidelines, theme specifications, and component tokens based on visual design references (`design1`, `design2`, `design3` for Normal/Light mode and `design4` for Dark mode).

---

## 1. Visual References Overview

| Mode | Reference Images | Visual Language & Identity |
|---|---|---|
| **Normal Mode (Light)** | `design1.webp`, `design2.webp`, `design3.webp` | Clean, crisp, high-trust fintech aesthetic. Airy light surfaces, iridescent holographic accents (cyan, mint, magenta sheens), rich navy/slate contrasting panels, rounded pill buttons, subtle borders, high-density metric cards. |
| **Dark Mode** | `design4.webp` | Precision isometric engineering, obsidian/charcoal surfaces (`#0f0f11`, `#18181b`), subtle wireframe grid backgrounds, high-contrast crisp typography, minimal monochrome badge pills, and stark white contrast primary action triggers. |

---

## 2. Color Palette & Theming Tokens

### A. Normal Mode (Light / Modern Fintech)
Inspired by `design1.webp` & `design3.webp`:
- **Canvas / Background**: `#F8FAFC` (slate-50) / `#FFFFFF` (pure white card background)
- **Primary Text**: `#0F172A` (slate-900)
- **Muted Text / Secondary**: `#64748B` (slate-500)
- **Borders & Dividers**: `#E2E8F0` (slate-200) / `#F1F5F9` (slate-100)
- **Accent & Brand Primary**:
  - Vibrant Cyan: `#00B4D8` / `#00C2CB`
  - Emerald / Mint: `#10B981` (Approved / Verified)
  - Holographic Gradient Accents: `linear-gradient(135deg, #a7f3d0 0%, #bae6fd 50%, #fbcfe8 100%)` (for KYC credentials card preview, similar to Onpoint card in `design1`)
- **Deep Contrast Panels**: `#0F172A` / `#0A0F1D` (Hero banners, stat highlights, or elevated modal drawer headers)

### B. Dark Mode (Precision Sleek Obsidian)
Inspired directly by `design4.webp` ("Hill" aesthetic):
- **Canvas / Background**: `#0D0D10` (true deep charcoal/black)
- **Elevated Card Surface**: `#16161A` with `1px solid rgba(255, 255, 255, 0.08)` border
- **Sub-card / Hover Surface**: `#202026`
- **Primary Text**: `#F4F4F6` (crisp white)
- **Secondary / Subdued Text**: `#8E8E93` (mid grey)
- **Wireframe & Grid Lines**: `rgba(255, 255, 255, 0.05)` subtle dot grid or isometric lines
- **Primary Action Accent**: `#FFFFFF` with `#000000` text (high-visibility stark white pill buttons like `Next` in `design4`)
- **Secondary Action Accent**: `#27272A` with `#FFFFFF` text (e.g. `Skip` button)
- **Status Indicators (Dark)**:
  - OCR Draft: `#38BDF8` (Sky blue border + subtle glowing dot)
  - Approved / Confirmed: `#34D399` (Emerald badge)
  - Needs Correction / Rejected: `#F87171` (Rose red)

---

## 3. Typography & Hierarchy

- **Font Family**: Modern clean sans-serif (`Inter`, `Plus Jakarta Sans`, or `Geist Sans`)
- **Monospace Details**: `JetBrains Mono` or `Fira Code` for Case IDs (`CASE-2026-0042`), SHA-256 hashes, and raw document keys.
- **Scale**:
  - Display / Hero Headings: `text-3xl` to `text-4xl` (font-extrabold, tight tracking `-0.02em`)
  - Section Headings: `text-xl` to `text-2xl` (font-semibold)
  - Card & Table Headers: `text-sm` (font-medium, uppercase tracking-wide in dark mode)
  - Body Text: `text-sm` (leading-relaxed)
  - Badges & Micro-copy: `text-xs` (font-medium, rounded-full)

---

## 4. Layout Patterns by Core Experience

### A. Navigation & Shell (`design1` & `design3`)
- **Header**: Floating pill header with blurred backdrop (`backdrop-blur-md bg-white/80` or `bg-[#0D0D10]/80` in dark mode).
- **Tenant Switcher**: Elegant dropdown displaying current tenant logo + status badge.
- **Quick Theme Toggle**: Light / Dark mode toggle switch with sun/moon icon.

### B. Tenant Dashboard & Case Queue (`design3` pattern)
- **Top Metrics Row**: 4 KPI cards (Open Cases, Pending OCR Review, Expiring Shares, Completed Onboardings) with mini trend sparklines and clean numeric callouts.
- **Filter Toolbar**: Segmented search input, status filter pills (`All`, `In Review`, `Awaiting Docs`, `Approved`), date range picker.
- **Data Grid / Master List**: Clean rows with hovering effects, badge indicators, reviewer avatar, and direct drawer trigger.

### C. Case Investigation & Split Workspace (`design4` card elegance)
- **Left Panel (55%) — Document Inspection**:
  - Embedded PDF/Image viewer with zoom, rotation, and page toggle.
  - Overlay highlights on OCR-detected bounding areas.
- **Right Panel (45%) — Field Verification & Decision Deck**:
  - Grouped fields (Entity Information, Representative Details, Registration Data).
  - Each field displays:
    1. Label & Extracted OCR value.
    2. Confidence pill badge (`98% High`).
    3. Quick action buttons: `[Confirm]`, `[Edit / Correct]`, `[Reject]`.
  - Bottom Sticky Decision Bar: Mandatory decision rationale textarea + `Approve Case`, `Request Resubmission`, `Reject Case` buttons.

### D. Applicant Portal (Self-Service Onboarding)
- **Context Card**: Displays the requesting marketplace business name, transaction purpose, and strict data privacy guarantee.
- **Stepped Progress**: Step 1: Business details $\rightarrow$ Step 2: Document upload $\rightarrow$ Step 3: Review OCR draft fields $\rightarrow$ Step 4: Consent & share approval.
- **Dropzone**: Modern animated drag-and-drop zone with immediate magic-byte validation and upload progress bar.

### E. Controlled Share View (Recipient Tenant Experience)
- **Credential Summary Card**: Emulating the holographic credential card from `design1` and `design2`.
- Displays *only* the specific granted fields (e.g., Business Registration Verified, Tax ID confirmed).
- Clear expiration countdown tag (`Valid for 28 more days`) and source tenant cryptographic signature badge.

---

## 5. Tailwind Configuration Guide & Theme Setup

```javascript
// tailwind.config.js snippet
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: {
          light: '#F8FAFC',
          dark: '#0D0D10',
        },
        surface: {
          light: '#FFFFFF',
          dark: '#16161A',
          subtleDark: '#202026',
        },
        brand: {
          cyan: '#00C2CB',
          mint: '#10B981',
          slate: '#0F172A',
        }
      },
      borderRadius: {
        'card': '16px',
        'pill': '9999px',
      }
    }
  }
}
```

---

## 6. Implementation Consistency Rules

1. **State Label Consistency**: Always use uniform status styling across views:
   - `OCR Draft`: Amber / Orange tag with pencil icon
   - `Applicant Confirmed`: Cyan / Blue tag with checkmark
   - `Reviewed / Verified`: Emerald / Green tag with shield icon
   - `Shared`: Purple / Indigo tag with link icon
2. **Accessible Contrast**: Ensure all text meets WCAG AA standards (4.5:1 ratio) in both light mode and dark mode.
3. **No Flashing During Theme Switch**: Store theme preference in `localStorage` and apply class `dark` to `document.documentElement` before hydration.
