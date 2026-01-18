"use client";

import type { MouseEvent } from "react";
import { useMemo, useRef, useState } from "react";

import type { HitTestRequest, IRPage } from "@/lib/api";
import { hitTest } from "@/lib/api";
import { useSelectionStore } from "@/lib/state/store";

type DragState = {
  active: boolean;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
};

const DRAG_THRESHOLD = 4;

function distanceToCenter(px: number, py: number, bbox: number[]) {
  const [x0, y0, x1, y1] = bbox;
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  return (px - cx) ** 2 + (py - cy) ** 2;
}

function findHoverCandidate(primitives: IRPage["primitives"], point: { x: number; y: number }) {
  const matches = primitives
    .map((primitive) => ({
      primitive,
      distance: distanceToCenter(point.x, point.y, primitive.bbox)
    }))
    .filter(({ primitive }) => {
      const [x0, y0, x1, y1] = primitive.bbox;
      return point.x >= x0 && point.x <= x1 && point.y >= y0 && point.y <= y1;
    });

  matches.sort((a, b) => {
    if (a.distance !== b.distance) {
      return a.distance - b.distance;
    }
    return a.primitive.z_index - b.primitive.z_index;
  });

  return matches[0]?.primitive.id ?? null;
}

function toPdfPoint(
  x: number,
  y: number,
  page: IRPage,
  renderedWidth: number,
  renderedHeight: number
) {
  const scaleX = renderedWidth / page.width_pt;
  const scaleY = renderedHeight / page.height_pt;
  return {
    x: x / scaleX,
    y: y / scaleY
  };
}

function bboxToPixels(bbox: number[], page: IRPage, renderedWidth: number, renderedHeight: number) {
  const scaleX = renderedWidth / page.width_pt;
  const scaleY = renderedHeight / page.height_pt;
  const [x0, y0, x1, y1] = bbox;
  return {
    left: x0 * scaleX,
    top: y0 * scaleY,
    width: (x1 - x0) * scaleX,
    height: (y1 - y0) * scaleY
  };
}

interface SelectionLayerProps {
  docId: string;
  pageIndex: number;
  page: IRPage;
  renderedWidth: number;
  renderedHeight: number;
}

export function SelectionLayer({
  docId,
  pageIndex,
  page,
  renderedWidth,
  renderedHeight
}: SelectionLayerProps) {
  const layerRef = useRef<HTMLDivElement>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const { selectedId, hoveredId, setHoveredId, setCandidates } = useSelectionStore();

  const primitivesById = useMemo(() => {
    return new Map(page.primitives.map((primitive) => [primitive.id, primitive]));
  }, [page.primitives]);

  const selectedPrimitive = selectedId ? primitivesById.get(selectedId) : null;
  const hoveredPrimitive = hoveredId ? primitivesById.get(hoveredId) : null;

  const handleMouseDown = (event: MouseEvent<HTMLDivElement>) => {
    const bounds = layerRef.current?.getBoundingClientRect();
    if (!bounds) {
      return;
    }
    setDragState({
      active: true,
      startX: event.clientX - bounds.left,
      startY: event.clientY - bounds.top,
      currentX: event.clientX - bounds.left,
      currentY: event.clientY - bounds.top
    });
  };

  const handleMouseMove = (event: MouseEvent<HTMLDivElement>) => {
    const bounds = layerRef.current?.getBoundingClientRect();
    if (!bounds) {
      return;
    }

    const x = event.clientX - bounds.left;
    const y = event.clientY - bounds.top;

    if (dragState?.active) {
      setDragState((prev) =>
        prev
          ? {
              ...prev,
              currentX: x,
              currentY: y
            }
          : null
      );
      return;
    }

    const pdfPoint = toPdfPoint(x, y, page, renderedWidth, renderedHeight);
    const nextHover = findHoverCandidate(page.primitives, pdfPoint);
    if (nextHover !== hoveredId) {
      setHoveredId(nextHover);
    }
  };

  const handleMouseLeave = () => {
    setHoveredId(null);
    if (dragState?.active) {
      setDragState(null);
    }
  };

  const performHitTest = async (payload: HitTestRequest) => {
    try {
      const response = await hitTest(docId, pageIndex, payload);
      setCandidates(pageIndex, response.candidates);
    } catch (error) {
      console.error("Hit-test failed", error);
    }
  };

  const handleMouseUp = (event: MouseEvent<HTMLDivElement>) => {
    if (!dragState?.active) {
      return;
    }
    const bounds = layerRef.current?.getBoundingClientRect();
    if (!bounds) {
      return;
    }
    const endX = event.clientX - bounds.left;
    const endY = event.clientY - bounds.top;
    const deltaX = Math.abs(endX - dragState.startX);
    const deltaY = Math.abs(endY - dragState.startY);
    const isClick = deltaX < DRAG_THRESHOLD && deltaY < DRAG_THRESHOLD;

    if (isClick) {
      const pdfPoint = toPdfPoint(endX, endY, page, renderedWidth, renderedHeight);
      void performHitTest({ point: pdfPoint });
    } else {
      const pdfStart = toPdfPoint(dragState.startX, dragState.startY, page, renderedWidth, renderedHeight);
      const pdfEnd = toPdfPoint(endX, endY, page, renderedWidth, renderedHeight);
      void performHitTest({
        rect: {
          x0: pdfStart.x,
          y0: pdfStart.y,
          x1: pdfEnd.x,
          y1: pdfEnd.y
        }
      });
    }

    setDragState(null);
  };

  const dragRect = dragState?.active
    ? {
        left: Math.min(dragState.startX, dragState.currentX),
        top: Math.min(dragState.startY, dragState.currentY),
        width: Math.abs(dragState.currentX - dragState.startX),
        height: Math.abs(dragState.currentY - dragState.startY)
      }
    : null;

  return (
    <div
      ref={layerRef}
      className="absolute inset-0 cursor-crosshair"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onMouseUp={handleMouseUp}
      role="presentation"
    >
      {hoveredPrimitive && hoveredPrimitive.id !== selectedPrimitive?.id ? (
        <div
          className="absolute rounded border border-forge-accent/60 bg-forge-accent/10"
          style={bboxToPixels(hoveredPrimitive.bbox, page, renderedWidth, renderedHeight)}
        />
      ) : null}
      {selectedPrimitive ? (
        <div
          className="absolute rounded border-2 border-forge-accent bg-forge-accent/10 shadow-[0_0_0_1px_rgba(15,118,110,0.7)]"
          style={bboxToPixels(selectedPrimitive.bbox, page, renderedWidth, renderedHeight)}
        />
      ) : null}
      {dragRect ? (
        <div
          className="absolute rounded border border-dashed border-forge-accent/70 bg-forge-accent/5"
          style={dragRect}
        />
      ) : null}
    </div>
  );
}
