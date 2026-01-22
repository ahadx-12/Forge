export type PdfJsRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

export type PdfJsNormalizedBbox = [number, number, number, number];

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));

export const roundTo = (value: number, decimals = 2) =>
  Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals);

export function normalizeBbox(
  rect: PdfJsRect,
  viewportWidth: number,
  viewportHeight: number
): PdfJsNormalizedBbox {
  if (!viewportWidth || !viewportHeight) {
    return [0, 0, 0, 0];
  }
  const left = clamp(rect.left / viewportWidth);
  const top = clamp(rect.top / viewportHeight);
  const right = clamp((rect.left + rect.width) / viewportWidth);
  const bottom = clamp((rect.top + rect.height) / viewportHeight);
  return [left, top, right, bottom];
}

export function roundNormalizedBbox(
  bbox: PdfJsNormalizedBbox,
  decimals = 4
): PdfJsNormalizedBbox {
  return bbox.map((value) => roundTo(value, decimals)) as PdfJsNormalizedBbox;
}

const bboxToString = (bbox: PdfJsNormalizedBbox) =>
  roundNormalizedBbox(bbox, 4)
    .map((value) => value.toFixed(4))
    .join(",");

const toHexString = (bytes: number[]) =>
  bytes.map((byte) => byte.toString(16).padStart(2, "0")).join("");

const stringToBytes = (value: string) => {
  const bytes: number[] = [];
  for (let i = 0; i < value.length; i += 1) {
    bytes.push(value.charCodeAt(i));
  }
  return bytes;
};

// SHA-1 and SHA-256 implementations adapted for deterministic client-side hashing.
const sha1Hex = (value: string) => {
  const bytes = stringToBytes(value);
  const words: number[] = [];
  for (let i = 0; i < bytes.length; i += 1) {
    words[i >> 2] |= bytes[i] << (24 - (i % 4) * 8);
  }
  words[bytes.length >> 2] |= 0x80 << (24 - (bytes.length % 4) * 8);
  words[((bytes.length + 8) >> 6) * 16 + 15] = bytes.length * 8;

  let h0 = 0x67452301;
  let h1 = 0xefcdab89;
  let h2 = 0x98badcfe;
  let h3 = 0x10325476;
  let h4 = 0xc3d2e1f0;

  for (let i = 0; i < words.length; i += 16) {
    const w = new Array(80).fill(0);
    for (let t = 0; t < 16; t += 1) {
      w[t] = words[i + t] | 0;
    }
    for (let t = 16; t < 80; t += 1) {
      const value = w[t - 3] ^ w[t - 8] ^ w[t - 14] ^ w[t - 16];
      w[t] = (value << 1) | (value >>> 31);
    }
    let a = h0;
    let b = h1;
    let c = h2;
    let d = h3;
    let e = h4;
    for (let t = 0; t < 80; t += 1) {
      let f = 0;
      let k = 0;
      if (t < 20) {
        f = (b & c) | (~b & d);
        k = 0x5a827999;
      } else if (t < 40) {
        f = b ^ c ^ d;
        k = 0x6ed9eba1;
      } else if (t < 60) {
        f = (b & c) | (b & d) | (c & d);
        k = 0x8f1bbcdc;
      } else {
        f = b ^ c ^ d;
        k = 0xca62c1d6;
      }
      const temp = (((a << 5) | (a >>> 27)) + f + e + k + w[t]) | 0;
      e = d;
      d = c;
      c = (b << 30) | (b >>> 2);
      b = a;
      a = temp;
    }
    h0 = (h0 + a) | 0;
    h1 = (h1 + b) | 0;
    h2 = (h2 + c) | 0;
    h3 = (h3 + d) | 0;
    h4 = (h4 + e) | 0;
  }

  return toHexString([
    (h0 >>> 24) & 0xff,
    (h0 >>> 16) & 0xff,
    (h0 >>> 8) & 0xff,
    h0 & 0xff,
    (h1 >>> 24) & 0xff,
    (h1 >>> 16) & 0xff,
    (h1 >>> 8) & 0xff,
    h1 & 0xff,
    (h2 >>> 24) & 0xff,
    (h2 >>> 16) & 0xff,
    (h2 >>> 8) & 0xff,
    h2 & 0xff,
    (h3 >>> 24) & 0xff,
    (h3 >>> 16) & 0xff,
    (h3 >>> 8) & 0xff,
    h3 & 0xff,
    (h4 >>> 24) & 0xff,
    (h4 >>> 16) & 0xff,
    (h4 >>> 8) & 0xff,
    h4 & 0xff
  ]);
};

const sha256Hex = (value: string) => {
  const bytes = stringToBytes(value);
  const words: number[] = [];
  for (let i = 0; i < bytes.length; i += 1) {
    words[i >> 2] |= bytes[i] << (24 - (i % 4) * 8);
  }
  words[bytes.length >> 2] |= 0x80 << (24 - (bytes.length % 4) * 8);
  words[((bytes.length + 8) >> 6) * 16 + 15] = bytes.length * 8;

  const k = [
    0x428a2f98,
    0x71374491,
    0xb5c0fbcf,
    0xe9b5dba5,
    0x3956c25b,
    0x59f111f1,
    0x923f82a4,
    0xab1c5ed5,
    0xd807aa98,
    0x12835b01,
    0x243185be,
    0x550c7dc3,
    0x72be5d74,
    0x80deb1fe,
    0x9bdc06a7,
    0xc19bf174,
    0xe49b69c1,
    0xefbe4786,
    0x0fc19dc6,
    0x240ca1cc,
    0x2de92c6f,
    0x4a7484aa,
    0x5cb0a9dc,
    0x76f988da,
    0x983e5152,
    0xa831c66d,
    0xb00327c8,
    0xbf597fc7,
    0xc6e00bf3,
    0xd5a79147,
    0x06ca6351,
    0x14292967,
    0x27b70a85,
    0x2e1b2138,
    0x4d2c6dfc,
    0x53380d13,
    0x650a7354,
    0x766a0abb,
    0x81c2c92e,
    0x92722c85,
    0xa2bfe8a1,
    0xa81a664b,
    0xc24b8b70,
    0xc76c51a3,
    0xd192e819,
    0xd6990624,
    0xf40e3585,
    0x106aa070,
    0x19a4c116,
    0x1e376c08,
    0x2748774c,
    0x34b0bcb5,
    0x391c0cb3,
    0x4ed8aa4a,
    0x5b9cca4f,
    0x682e6ff3,
    0x748f82ee,
    0x78a5636f,
    0x84c87814,
    0x8cc70208,
    0x90befffa,
    0xa4506ceb,
    0xbef9a3f7,
    0xc67178f2
  ];

  let h0 = 0x6a09e667;
  let h1 = 0xbb67ae85;
  let h2 = 0x3c6ef372;
  let h3 = 0xa54ff53a;
  let h4 = 0x510e527f;
  let h5 = 0x9b05688c;
  let h6 = 0x1f83d9ab;
  let h7 = 0x5be0cd19;

  for (let i = 0; i < words.length; i += 16) {
    const w = new Array(64).fill(0);
    for (let t = 0; t < 16; t += 1) {
      w[t] = words[i + t] | 0;
    }
    for (let t = 16; t < 64; t += 1) {
      const s0 = ((w[t - 15] >>> 7) | (w[t - 15] << 25)) ^ ((w[t - 15] >>> 18) | (w[t - 15] << 14)) ^ (w[t - 15] >>> 3);
      const s1 = ((w[t - 2] >>> 17) | (w[t - 2] << 15)) ^ ((w[t - 2] >>> 19) | (w[t - 2] << 13)) ^ (w[t - 2] >>> 10);
      w[t] = (w[t - 16] + s0 + w[t - 7] + s1) | 0;
    }

    let a = h0;
    let b = h1;
    let c = h2;
    let d = h3;
    let e = h4;
    let f = h5;
    let g = h6;
    let h = h7;

    for (let t = 0; t < 64; t += 1) {
      const s1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + s1 + ch + k[t] + w[t]) | 0;
      const s0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (s0 + maj) | 0;

      h = g;
      g = f;
      f = e;
      e = (d + temp1) | 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) | 0;
    }

    h0 = (h0 + a) | 0;
    h1 = (h1 + b) | 0;
    h2 = (h2 + c) | 0;
    h3 = (h3 + d) | 0;
    h4 = (h4 + e) | 0;
    h5 = (h5 + f) | 0;
    h6 = (h6 + g) | 0;
    h7 = (h7 + h) | 0;
  }

  return toHexString([
    (h0 >>> 24) & 0xff,
    (h0 >>> 16) & 0xff,
    (h0 >>> 8) & 0xff,
    h0 & 0xff,
    (h1 >>> 24) & 0xff,
    (h1 >>> 16) & 0xff,
    (h1 >>> 8) & 0xff,
    h1 & 0xff,
    (h2 >>> 24) & 0xff,
    (h2 >>> 16) & 0xff,
    (h2 >>> 8) & 0xff,
    h2 & 0xff,
    (h3 >>> 24) & 0xff,
    (h3 >>> 16) & 0xff,
    (h3 >>> 8) & 0xff,
    h3 & 0xff,
    (h4 >>> 24) & 0xff,
    (h4 >>> 16) & 0xff,
    (h4 >>> 8) & 0xff,
    h4 & 0xff,
    (h5 >>> 24) & 0xff,
    (h5 >>> 16) & 0xff,
    (h5 >>> 8) & 0xff,
    h5 & 0xff,
    (h6 >>> 24) & 0xff,
    (h6 >>> 16) & 0xff,
    (h6 >>> 8) & 0xff,
    h6 & 0xff,
    (h7 >>> 24) & 0xff,
    (h7 >>> 16) & 0xff,
    (h7 >>> 8) & 0xff,
    h7 & 0xff
  ]);
};

export function buildElementId(
  pageIndex: number,
  text: string,
  bbox: PdfJsNormalizedBbox,
  styleKey: string
): string {
  const signature = `${text}|${bboxToString(bbox)}|${styleKey}`;
  return `p${pageIndex}_${sha1Hex(signature).slice(0, 8)}`;
}

export function buildContentHash(
  text: string,
  bbox: PdfJsNormalizedBbox,
  styleKey: string
): string {
  const signature = `${text}|${bboxToString(bbox)}|${styleKey}`;
  return sha256Hex(signature).slice(0, 16);
}

export function hitTestSmallest(
  bboxes: { bbox: PdfJsNormalizedBbox }[],
  point: { x: number; y: number },
  slop: { x: number; y: number }
): number | null {
  let chosenIndex: number | null = null;
  let minArea = Number.POSITIVE_INFINITY;
  bboxes.forEach((item, index) => {
    const [left, top, right, bottom] = item.bbox;
    const expandedLeft = left - slop.x;
    const expandedTop = top - slop.y;
    const expandedRight = right + slop.x;
    const expandedBottom = bottom + slop.y;
    if (
      point.x >= expandedLeft &&
      point.x <= expandedRight &&
      point.y >= expandedTop &&
      point.y <= expandedBottom
    ) {
      const area = Math.max(0, right - left) * Math.max(0, bottom - top);
      if (area < minArea) {
        minArea = area;
        chosenIndex = index;
      }
    }
  });
  return chosenIndex;
}
