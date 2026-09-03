// Small facts about the project itself, kept out of the components so a copy
// change is a one-line edit. Corpus content never lives here.

// Prose says SG Ground Truth; sg-groundtruth is the slug, used for paths and the clone.
export const NAME = 'SG Ground Truth';

export const REPO = 'https://github.com/ksallee/sg-groundtruth';

// Two directory names, because two different questions are being answered and
// one constant used to answer both.
//
// OVERLAY_DIR is an instruction: it is what /how-it-works tells a reader to
// create for their own site. It never changes.
//
// OVERLAY_SOURCE_DIR is provenance: it is the directory this build actually
// read, and ScopeSection quotes it under every local section. A public deploy
// sets it to `corpus.example`, a committed copy reviewed by hand, so a section
// on that build names the directory its content came from rather than one it
// did not. See docs/example-overlay.md.
export const OVERLAY_DIR = 'corpus.local';

// Substituted by Vite. Declared in vite.config.js, which carries the default, so no .env
// file is needed and an absent variable cannot break a fresh clone.
export const OVERLAY_SOURCE_DIR = __OVERLAY_SOURCE__;
