import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "@/styles/globals.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FORGE",
  description: "FORGE document editor",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
