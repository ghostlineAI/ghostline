import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { DevelopmentBanner } from "@/components/development-banner";

export const metadata: Metadata = {
  title: "GhostLine - AI-Powered Ghost-Writing Platform",
  description: "Transform your ideas into professionally written books with our multi-agent AI system. Capture your unique voice and style in every page.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <DevelopmentBanner />
          {children}
        </Providers>
      </body>
    </html>
  );
}
