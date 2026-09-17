import { PenIcon, UploadIcon, CheckIcon } from "./icons";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

const panelClass = "bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800";

type Mode = "draw" | "upload" | "skip";
type Point = { x: number; y: number };

const INK = "#1e2a4a";
const LINE_WIDTH = 2.6;

interface Props {
  value: string | null;
  onChange: (dataUrl: string | null) => void;
}

/** Draw a signature with a pointer, upload an image, or leave it for paper. */
export default function SignaturePad({ value, onChange }: Props) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<Mode>(value ? "draw" : "skip");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const strokes = useRef<Point[][]>([]);
  const current = useRef<Point[] | null>(null);
  const [hasInk, setHasInk] = useState(false);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState("");

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width / dpr, canvas.height / dpr);
    ctx.strokeStyle = INK;
    ctx.lineWidth = LINE_WIDTH;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    const all = current.current ? [...strokes.current, current.current] : strokes.current;
    for (const stroke of all) {
      if (stroke.length === 0) continue;
      ctx.beginPath();
      ctx.moveTo(stroke[0].x, stroke[0].y);
      if (stroke.length < 3) {
        ctx.lineTo(stroke[stroke.length - 1].x + 0.1, stroke[stroke.length - 1].y + 0.1);
      } else {
        for (let i = 1; i < stroke.length - 1; i += 1) {
          const midX = (stroke[i].x + stroke[i + 1].x) / 2;
          const midY = (stroke[i].y + stroke[i + 1].y) / 2;
          ctx.quadraticCurveTo(stroke[i].x, stroke[i].y, midX, midY);
        }
      }
      ctx.stroke();
    }
  }, []);

  // Keep the canvas at its true resolution (devicePixelRatio), on resize too.
  useEffect(() => {
    if (mode !== "draw") return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      redraw();
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [mode, redraw]);

  const commit = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (strokes.current.length === 0) {
      setHasInk(false);
      onChange(null);
      return;
    }
    setHasInk(true);
    onChange(canvas.toDataURL("image/png"));
  }, [onChange]);

  const pointFrom = (e: React.PointerEvent<HTMLCanvasElement>): Point => {
    const rect = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    current.current = [pointFrom(e)];
    redraw();
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!current.current) return;
    current.current.push(pointFrom(e));
    redraw();
  };

  const onPointerUp = () => {
    if (!current.current) return;
    if (current.current.length > 0) strokes.current.push(current.current);
    current.current = null;
    redraw();
    commit();
  };

  const undo = () => {
    strokes.current.pop();
    redraw();
    commit();
  };

  const clear = () => {
    strokes.current = [];
    current.current = null;
    redraw();
    commit();
  };

  const handleUpload = (file: File | undefined) => {
    setUploadError("");
    if (!file) return;
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
      setUploadError(t("signature.uploadInvalid"));
      return;
    }
    if (file.size > 3_000_000) {
      setUploadError(t("signature.uploadTooLarge"));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = String(reader.result);
      setUploadPreview(dataUrl);
      onChange(dataUrl);
    };
    reader.readAsDataURL(file);
  };

  const switchMode = (next: Mode) => {
    setMode(next);
    if (next === "skip") {
      onChange(null);
    } else if (next === "draw") {
      commit();
    } else if (next === "upload") {
      onChange(uploadPreview);
    }
  };

  const tabClass = (active: boolean) =>
    `px-4 py-2 rounded-lg text-sm font-medium min-h-[40px] transition ${
      active
        ? "bg-brand-600 text-white"
        : "border border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
    }`;

  return (
    <section className={`${panelClass} p-4 sm:p-6`}>
      <h4 className="font-semibold text-slate-900 dark:text-slate-100">{t("signature.title")}</h4>

      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" aria-pressed={mode === "draw"} className={tabClass(mode === "draw")} onClick={() => switchMode("draw")}>
          <PenIcon className="mr-2 inline h-4 w-4" />{t("signature.draw")}
        </button>
        <button type="button" aria-pressed={mode === "upload"} className={tabClass(mode === "upload")} onClick={() => switchMode("upload")}>
          <UploadIcon className="mr-2 inline h-4 w-4" />{t("signature.upload")}
        </button>
        <button type="button" aria-pressed={mode === "skip"} className={tabClass(mode === "skip")} onClick={() => switchMode("skip")}>
          {t("signature.skip")}
        </button>
      </div>

      {mode === "draw" && (
        <div className="mt-3">
          <canvas
            ref={canvasRef}
            aria-label={t("signature.draw")}
            className="h-40 w-full max-w-xl cursor-crosshair touch-none rounded-xl border-2 border-dashed border-slate-300 bg-white dark:border-slate-600"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          />
          <div className="mt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={undo}
              disabled={!hasInk}
              className="text-sm text-slate-600 hover:underline disabled:opacity-40 dark:text-slate-300"
            >
              ↩ {t("signature.undo")}
            </button>
            <button
              type="button"
              onClick={clear}
              disabled={!hasInk}
              className="text-sm text-slate-600 hover:underline disabled:opacity-40 dark:text-slate-300"
            >
              🗑 {t("signature.clear")}
            </button>
          </div>
        </div>
      )}

      {mode === "upload" && (
        <div className="mt-3 space-y-2">
          <label className="flex min-h-[44px] w-fit focus-within:ring-2 focus-within:ring-brand-500 cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              onChange={(e) => handleUpload(e.target.files?.[0])}
            />
            {t("signature.chooseFile")}
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400">{t("signature.uploadHint")}</p>
          {uploadError && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{uploadError}</p>}
          {uploadPreview && (
            <div className="flex items-center gap-3">
              <img
                src={uploadPreview}
                alt={t("signature.previewAlt")}
                className="max-h-24 rounded-lg border border-slate-200 bg-white p-1 dark:border-slate-700"
              />
              <button
                type="button"
                onClick={() => {
                  setUploadPreview(null);
                  onChange(null);
                }}
                className="text-sm text-slate-600 hover:underline dark:text-slate-300"
              >
                {t("signature.remove")}
              </button>
            </div>
          )}
        </div>
      )}


      {value && mode !== "skip" && (
        <p className="mt-3 text-xs text-emerald-700 dark:text-emerald-300"><CheckIcon className="mr-1 inline h-4 w-4" />{t("signature.applied")}</p>
      )}
    </section>
  );
}
