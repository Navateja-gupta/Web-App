import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import Alert from "../../components/Alert";
import Button from "../../components/Button";
import FormField from "../../components/FormField";
import Spinner from "../../components/Spinner";
import { api, getErrorMessage } from "../../lib/api";
import type { PortfolioItem } from "../../types";

const MAX_MB = 5;
const ACCEPT = "image/jpeg,image/png,image/webp";

/** Manage portfolio photos for `/me/vendor` (vendor) or `/admin/vendors/{id}` (admin). */
export default function PortfolioManager({ basePath }: { basePath: string }) {
  const [items, setItems] = useState<PortfolioItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setItems((await api.get<PortfolioItem[]>(`${basePath}/portfolio`)).data);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [basePath]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>, success?: string) {
    setError(null);
    setNotice(null);
    try {
      await action();
      if (success) setNotice(success);
      await load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    const file = fileInput.current?.files?.[0];
    if (!file) return setError("Choose a photo to upload.");
    if (!ACCEPT.split(",").includes(file.type)) return setError("Only JPEG, PNG or WebP images are allowed.");
    if (file.size > MAX_MB * 1024 * 1024) return setError(`Photos must be ${MAX_MB} MB or smaller.`);

    const body = new FormData();
    body.append("file", file);
    if (caption.trim()) body.append("caption", caption.trim());
    setUploading(true);
    await run(async () => {
      await api.post(`${basePath}/portfolio`, body, { timeout: 60_000 });
      setCaption("");
      if (fileInput.current) fileInput.current.value = "";
    }, "Photo uploaded.");
    setUploading(false);
  }

  /** Swap two neighbours and save the new order for every item whose position changed. */
  function move(index: number, direction: -1 | 1) {
    if (!items) return;
    const reordered = [...items];
    const target = index + direction;
    [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    void run(() =>
      Promise.all(
        reordered
          .map((item, position) => ({ item, position }))
          .filter(({ item, position }) => item.display_order !== position)
          .map(({ item, position }) => api.patch(`${basePath}/portfolio/${item.id}`, { display_order: position })),
      ),
    );
  }

  function editCaption(item: PortfolioItem) {
    const next = window.prompt("Photo caption", item.caption ?? "");
    if (next === null) return;
    void run(() => api.patch(`${basePath}/portfolio/${item.id}`, { caption: next.trim() || null }), "Caption saved.");
  }

  if (!items) return error ? <Alert kind="error">{error}</Alert> : <Spinner />;

  return (
    <div className="space-y-4">
      {error && <Alert kind="error">{error}</Alert>}
      {notice && <Alert kind="success">{notice}</Alert>}

      <form onSubmit={handleUpload} className="flex flex-wrap items-end gap-3 rounded-xl border border-stone-200 bg-stone-50 p-4">
        <label className="text-sm">
          <span className="block font-medium text-stone-700">Photo</span>
          <input ref={fileInput} type="file" accept={ACCEPT} className="mt-1 block text-sm" />
        </label>
        <FormField label="Caption" value={caption} onChange={(e) => setCaption(e.target.value)} maxLength={255} className="min-w-56 flex-1" />
        <Button type="submit" loading={uploading}>
          Upload
        </Button>
        <p className="w-full text-xs text-stone-500">
          JPEG, PNG or WebP, up to {MAX_MB} MB. Only upload photos you have permission to use. Location data is removed automatically.
          The first photo is used as the cover image.
        </p>
      </form>

      {items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-stone-300 bg-white p-6 text-center text-stone-600">
          No photos yet. Real photos of past work help customers decide.
        </p>
      ) : (
        <ul className="grid grid-cols-2 gap-4 md:grid-cols-3">
          {items.map((item, index) => (
            <li key={item.id} className="overflow-hidden rounded-xl border border-stone-200 bg-white">
              <img src={item.url} alt={item.caption ?? "Portfolio photo"} className="aspect-[4/3] w-full object-cover" loading="lazy" />
              <div className="space-y-2 p-3 text-sm">
                <p className="min-h-5 text-stone-700">
                  {index === 0 && <span className="mr-1 font-medium text-maroon-700">Cover ·</span>}
                  {item.caption ?? <span className="text-stone-400">No caption</span>}
                </p>
                <div className="flex flex-wrap gap-1">
                  <Button variant="secondary" className="px-2 py-1" disabled={index === 0} onClick={() => move(index, -1)} aria-label="Move earlier">
                    ←
                  </Button>
                  <Button variant="secondary" className="px-2 py-1" disabled={index === items.length - 1} onClick={() => move(index, 1)} aria-label="Move later">
                    →
                  </Button>
                  <Button variant="secondary" className="px-2 py-1" onClick={() => editCaption(item)}>
                    Caption
                  </Button>
                  <Button
                    variant="danger"
                    className="px-2 py-1"
                    onClick={() => window.confirm("Delete this photo?") && run(() => api.delete(`${basePath}/portfolio/${item.id}`), "Photo deleted.")}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
