# Wizard avatar

The wizard mascot is the face of Memosphere's AI quiz-creation flow
(`/app/quiz/new/wizard`). Direct user feedback, in order:

1. A generic lucide "wand" icon read as too small/abstract — replaced with a 🧙 emoji.
2. A giant standalone portrait (Warcraft-dialogue style) outside the chat was too huge — replaced with a smaller avatar inline next to each speech bubble.
3. A hand-drawn SVG replacement for the emoji (per the request that the icon be
   a real `.svg` file, not inline markup) was tried and rejected as ugly — the
   🧙 emoji look was preferred. Resolution: the SVG file now wraps the same 🧙
   glyph in an `<svg><text>` element, so it's a real `.svg` asset on disk that
   renders identically to the emoji everyone liked.

**Current source of truth:** `/public/assets/svg/wizard.svg` (a real SVG file,
served as a static asset), rendered via the `WizardAvatar` component
(`wizard-avatar.tsx`) in this folder — every usage goes through that component.
If this ever needs a real illustration instead of the emoji-in-SVG approach,
that's a deliberate design upgrade, not a casual icon swap.

**Do not replace or remove the wizard mascot without checking with the user
first.** If it changes, change the SVG file and/or the component, and update
this note with the reasoning so the history isn't lost again.
