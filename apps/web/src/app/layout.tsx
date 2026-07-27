import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AkademX10 XAI | Intelligent Training Platform",
  description: "AI-supported roleplay, skill development, scoring, and reporting for modern teams.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-[#f5f9ff] text-[#25214d]">{children}</body>
    </html>
  );
}
