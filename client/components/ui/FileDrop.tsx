"use client";

import { useRef, useState } from "react";
import { IconDocument, IconUpload, IconX } from "./icons";

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileDrop({
  files,
  onChange,
  accept,
  multiple = false,
  hint,
}: {
  files: File[];
  onChange: (files: File[]) => void;
  accept: string; // e.g. ".pdf,.docx"
  multiple?: boolean;
  hint: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const acceptedExts = accept.split(",").map((s) => s.trim().toLowerCase());
  const isAccepted = (f: File) =>
    acceptedExts.some((ext) => f.name.toLowerCase().endsWith(ext));

  const addFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const valid = Array.from(incoming).filter(isAccepted);
    onChange(multiple ? [...files, ...valid] : valid.slice(0, 1));
  };

  const removeAt = (index: number) =>
    onChange(files.filter((_, i) => i !== index));

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          addFiles(e.dataTransfer.files);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors duration-150 ${
          dragging
            ? "border-indigo-400 bg-indigo-50/60"
            : "border-slate-300 bg-slate-50/60 hover:border-indigo-300 hover:bg-indigo-50/40"
        }`}
      >
        <span className="mb-2.5 flex h-10 w-10 items-center justify-center rounded-xl bg-white text-indigo-500 shadow-sm ring-1 ring-slate-200">
          <IconUpload className="h-4.5 w-4.5" />
        </span>
        <p className="text-sm font-medium text-slate-700">
          {dragging ? "Drop to attach" : "Click to browse or drag files here"}
        </p>
        <p className="mt-1 text-xs text-slate-400">{hint}</p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = ""; // allow re-selecting the same file
          }}
        />
      </div>

      {files.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {files.map((f, i) => (
            <li
              key={`${f.name}-${i}`}
              className="flex items-center gap-2.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <IconDocument className="h-4 w-4 shrink-0 text-slate-400" />
              <span className="min-w-0 flex-1 truncate font-medium text-slate-700">
                {f.name}
              </span>
              <span className="shrink-0 text-xs tabular-nums text-slate-400">
                {formatSize(f.size)}
              </span>
              <button
                type="button"
                onClick={() => removeAt(i)}
                className="shrink-0 rounded p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-rose-600"
                aria-label={`Remove ${f.name}`}
              >
                <IconX className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
