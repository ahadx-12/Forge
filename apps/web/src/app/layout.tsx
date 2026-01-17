import "@/styles/globals.css";

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "FORGE",
  description: "Week 1 PDF workflow for FORGE."
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
