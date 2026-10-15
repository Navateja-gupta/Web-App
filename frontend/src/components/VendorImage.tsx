/** Vendor photo, or a clearly-labelled placeholder when the vendor has not uploaded any. */
export default function VendorImage({ src, alt, className = "" }: { src: string | null; alt: string; className?: string }) {
  if (src) return <img src={src} alt={alt} loading="lazy" className={`object-cover ${className}`} />;
  return (
    <div className={`flex items-center justify-center bg-gradient-to-br from-maroon-50 to-amber-50 text-sm text-stone-500 ${className}`}>
      No photos yet
    </div>
  );
}
