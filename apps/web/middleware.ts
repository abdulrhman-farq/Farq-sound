// Locale routing disabled — Arabic is the only shipping locale and
// pages live at the root (not under [locale]/). Re-introduce
// next-intl/middleware + an [locale] segment when English ships.
export const config = { matcher: [] };
