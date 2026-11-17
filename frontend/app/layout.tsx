import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Necromancer",
  description: "Bring dead COBOL back to life, and prove it still behaves the same.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans bg-paper text-ink">{children}</body>
    </html>
  );
}
