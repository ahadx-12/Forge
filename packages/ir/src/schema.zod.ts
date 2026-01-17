export type PdfPageItem = {
  kind: "text" | "drawing";
  bbox: [number, number, number, number];
  text?: string;
  font?: string;
  size?: number;
  color?: number | null;
  width?: number;
  fill?: number | null;
};

export type PdfPage = {
  index: number;
  width_pt: number;
  height_pt: number;
  rotation: number;
  items: PdfPageItem[];
};

export type DecodePayload = {
  doc_id: string;
  page_count: number;
  pages: PdfPage[];
  extracted_at_iso: string;
};
