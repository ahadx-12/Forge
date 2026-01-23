export type PdfJsFontStyle = {
  fontFamily?: string;
};

export type PdfJsFontMap = Record<string, string>;

export type PdfJsTextTransform = {
  fontSizePx: number;
  matrix: [number, number, number, number, number, number];
};

export function buildPdfJsFontMap(styles: Record<string, PdfJsFontStyle> | undefined): PdfJsFontMap {
  if (!styles) {
    return {};
  }
  return Object.entries(styles).reduce<PdfJsFontMap>((acc, [fontName, style]) => {
    if (style?.fontFamily) {
      acc[fontName] = style.fontFamily;
    }
    return acc;
  }, {});
}

export function getPdfJsFontFamily(fontName: string | null | undefined, fontMap: PdfJsFontMap): string | null {
  if (!fontName) {
    return null;
  }
  return fontMap[fontName] ?? null;
}

export function deriveFontSizePxFromTransform(transform: number[]): number | null {
  if (!transform || transform.length < 6) {
    return null;
  }
  const [a, b, c, d] = transform;
  const primary = Math.hypot(a, b);
  const secondary = Math.hypot(c, d);
  const size = primary > 0 ? primary : secondary;
  return size > 0 ? size : null;
}

export function normalizePdfJsTextTransform(transform: number[]): PdfJsTextTransform | null {
  const fontSizePx = deriveFontSizePxFromTransform(transform);
  if (!fontSizePx) {
    return null;
  }
  const [a, b, c, d, e, f] = transform;
  return {
    fontSizePx,
    matrix: [a / fontSizePx, b / fontSizePx, c / fontSizePx, d / fontSizePx, e, f]
  };
}

export function isPdfFontAvailable(pdfFontName: string | null | undefined, fontMap: PdfJsFontMap): boolean {
  if (!pdfFontName) {
    return true;
  }
  if (fontMap[pdfFontName]) {
    return true;
  }
  const normalized = pdfFontName.trim().toLowerCase();
  return Object.values(fontMap).some((family) =>
    family
      .split(",")
      .map((entry) => entry.replace(/['"]/g, "").trim().toLowerCase())
      .includes(normalized)
  );
}
