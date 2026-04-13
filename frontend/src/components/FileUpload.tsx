import { useRef } from "react";

/** Shared with SourcesPanel drop zone + file picker */
export const UPLOAD_ACCEPT =
  ".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp,.mp4,.mov,.webm,.mkv";

interface Props {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

export function FileUpload({ onFiles, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={UPLOAD_ACCEPT}
        hidden
        onChange={(e) => {
          const list = e.target.files;
          if (list?.length) onFiles(Array.from(list));
          e.target.value = "";
        }}
      />
      <button
        type="button"
        className="btn-secondary"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        Add sources
      </button>
    </div>
  );
}
