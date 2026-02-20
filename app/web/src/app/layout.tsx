import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RollMind Oracle | D&D 2024 Reference",
  description: "Consult the Oracle for authoritative D&D 2024 rules and mechanics.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
