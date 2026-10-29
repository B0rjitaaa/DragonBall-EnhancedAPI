import { type RefObject, useEffect, useState } from "react";

export type Facing = "environment" | "user";

type CameraError = "insecure" | "unsupported" | "denied" | "notfound" | "other";

/** ¿Puede este navegador usar la cámara en directo? (HTTPS + getUserMedia) */
export const deviceCameraSupported = () =>
  window.isSecureContext && !!navigator.mediaDevices?.getUserMedia;

function classify(err: unknown): CameraError {
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") return "denied";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "notfound";
  return "other";
}

function ErrorMessage({ error, detail }: { error: CameraError; detail: string }) {
  // Puerto HTTPS del servidor (VITE_HTTPS_PORT al compilar; por defecto el 443).
  const port = import.meta.env.VITE_HTTPS_PORT;
  const httpsUrl = `https://${window.location.hostname}${port && port !== "443" ? `:${port}` : ""}${window.location.pathname}`;
  switch (error) {
    case "insecure":
      return (
        <>
          The browser only allows the live camera over HTTPS.{" "}
          <a href={httpsUrl}>Open the secure version</a>
        </>
      );
    case "unsupported":
      return <>This browser doesn't support the live camera. Use “Upload photo”.</>;
    case "denied":
      return (
        <>
          Camera permission denied. On iPhone: Settings → Chrome (or Safari) → Camera → Allow, then reload the
          page.
        </>
      );
    case "notfound":
      return <>No camera found on this device.</>;
    default:
      return <>Couldn't open the camera: {detail}</>;
  }
}

/**
 * Cámara del propio dispositivo (móvil o portátil) en directo con getUserMedia.
 * El <video> se comparte con el padre por `videoRef` para capturar fotogramas.
 */
export default function DeviceCamera({
  videoRef,
  facing,
}: {
  videoRef: RefObject<HTMLVideoElement | null>;
  facing: Facing;
}) {
  const [error, setError] = useState<{ kind: CameraError; detail: string } | null>(
    !window.isSecureContext
      ? { kind: "insecure", detail: "" }
      : !navigator.mediaDevices?.getUserMedia
        ? { kind: "unsupported", detail: "" }
        : null,
  );

  useEffect(() => {
    if (!deviceCameraSupported()) return;
    let stream: MediaStream | null = null;
    let wakeLock: WakeLockSentinel | null = null;
    let cancelled = false;

    // Con el móvil en un soporte, que la pantalla no se apague.
    const requestWakeLock = async () => {
      try {
        if ("wakeLock" in navigator && document.visibilityState === "visible") {
          wakeLock = await navigator.wakeLock.request("screen");
        }
      } catch {
        /* sin Wake Lock: no es imprescindible */
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible" && stream) void requestWakeLock();
    };

    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: facing },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          await video.play().catch(() => undefined);
        }
        setError(null);
        void requestWakeLock();
        document.addEventListener("visibilitychange", onVisibility);
      } catch (err) {
        if (!cancelled) setError({ kind: classify(err), detail: String(err) });
      }
    })();

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisibility);
      stream?.getTracks().forEach((t) => t.stop());
      void wakeLock?.release().catch(() => undefined);
      if (videoRef.current) videoRef.current.srcObject = null;
    };
  }, [facing, videoRef]);

  return (
    <>
      {/* playsInline + muted: imprescindibles para que iOS reproduzca en la página. */}
      <video ref={videoRef} className="preview" playsInline muted autoPlay hidden={!!error} />
      {error && (
        <div className="preview placeholder">
          <span>
            <ErrorMessage error={error.kind} detail={error.detail} />
          </span>
        </div>
      )}
    </>
  );
}
