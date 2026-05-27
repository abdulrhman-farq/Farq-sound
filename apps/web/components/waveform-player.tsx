"use client";

import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import { Pause, Play } from "lucide-react";

interface Marker {
  start_ms: number;
  end_ms: number;
  label: string;
}

interface Props {
  url: string;
  markers?: Marker[];
  height?: number;
}

export function WaveformPlayer({ url, markers = [], height = 96 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WaveSurfer | null>(null);
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;
    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "#C8A24B66",
      progressColor: "#C8A24B",
      cursorColor: "#0B1B2B",
      barWidth: 2,
      barRadius: 1,
      height,
      url,
    });
    wsRef.current = ws;
    ws.on("ready", () => setDuration(ws.getDuration()));
    ws.on("play", () => setPlaying(true));
    ws.on("pause", () => setPlaying(false));
    ws.on("finish", () => setPlaying(false));
    return () => {
      ws.destroy();
    };
  }, [url, height]);

  const toggle = () => {
    if (!wsRef.current) return;
    wsRef.current.playPause();
  };

  return (
    <div className="card">
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={toggle}
          className="w-12 h-12 rounded-full bg-navy text-ivory flex items-center justify-center hover:bg-navy/90"
          aria-label={playing ? "pause" : "play"}
        >
          {playing ? <Pause size={20} /> : <Play size={20} />}
        </button>
        <div className="flex-1 relative">
          <div ref={containerRef} />
          {duration > 0 && markers.length > 0 && (
            <div className="absolute inset-0 pointer-events-none">
              {markers.map((m, i) => {
                const left = (m.start_ms / 1000 / duration) * 100;
                const width = ((m.end_ms - m.start_ms) / 1000 / duration) * 100;
                return (
                  <div
                    key={i}
                    className="absolute top-0 bottom-0 rounded-sm border border-gold bg-gold/15"
                    style={{ left: `${left}%`, width: `${width}%` }}
                    title={m.label}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>
      {markers.length > 0 && (
        <p className="mt-3 text-xs text-muted-foreground">
          المساحات الذهبية = الأسامي اللي راح تتغير
        </p>
      )}
    </div>
  );
}
