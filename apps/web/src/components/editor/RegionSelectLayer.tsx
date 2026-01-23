"use client";

import { useRef, useState } from "react";

type RegionSelectLayerProps = {
  width: number;
  height: number;
  onSelect: (bboxNorm: [number, number, number, number]) => void;
};

const MIN_DRAG_PX = 4;
const HIT_SLOP_PX = 8;

type Point = { x: number; y: number };

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function RegionSelectLayer({ width, height, onSelect }: RegionSelectLayerProps) {
  const originRef = useRef<Point | null>(null);
  const [current, setCurrent] = useState<Point | null>(null);

  const toLocalPoint = (event: React.PointerEvent<HTMLDivElement>): Point => {
    const bounds = event.currentTarget.getBoundingClientRect();
    return {
      x: clamp(event.clientX - bounds.left, 0, bounds.width),
      y: clamp(event.clientY - bounds.top, 0, bounds.height)
    };
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    const point = toLocalPoint(event);
    originRef.current = point;
    setCurrent(point);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!originRef.current) {
      return;
    }
    setCurrent(toLocalPoint(event));
  };

  const finalizeSelection = () => {
    const origin = originRef.current;
    if (!origin || !current || width <= 0 || height <= 0) {
      originRef.current = null;
      setCurrent(null);
      return;
    }
    let x0 = Math.min(origin.x, current.x);
    let y0 = Math.min(origin.y, current.y);
    let x1 = Math.max(origin.x, current.x);
    let y1 = Math.max(origin.y, current.y);

    if (Math.abs(x1 - x0) < MIN_DRAG_PX && Math.abs(y1 - y0) < MIN_DRAG_PX) {
      x0 = origin.x - HIT_SLOP_PX;
      y0 = origin.y - HIT_SLOP_PX;
      x1 = origin.x + HIT_SLOP_PX;
      y1 = origin.y + HIT_SLOP_PX;
    }

    x0 = clamp(x0, 0, width);
    y0 = clamp(y0, 0, height);
    x1 = clamp(x1, 0, width);
    y1 = clamp(y1, 0, height);

    const bboxNorm: [number, number, number, number] = [
      clamp(x0 / width, 0, 1),
      clamp(y0 / height, 0, 1),
      clamp(x1 / width, 0, 1),
      clamp(y1 / height, 0, 1)
    ];
    onSelect(bboxNorm);
    originRef.current = null;
    setCurrent(null);
  };

  const handlePointerUp = () => {
    finalizeSelection();
  };

  const handlePointerCancel = () => {
    originRef.current = null;
    setCurrent(null);
  };

  const origin = originRef.current;
  const isDragging = origin && current;
  const left = isDragging ? Math.min(origin.x, current.x) : 0;
  const top = isDragging ? Math.min(origin.y, current.y) : 0;
  const boxWidth = isDragging ? Math.abs(current.x - origin.x) : 0;
  const boxHeight = isDragging ? Math.abs(current.y - origin.y) : 0;

  return (
    <div
      className="absolute inset-0 cursor-crosshair"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
    >
      {isDragging ? (
        <div
          className="absolute rounded-md border border-blue-400 bg-blue-400/10"
          style={{ left, top, width: boxWidth, height: boxHeight }}
        />
      ) : null}
    </div>
  );
}
