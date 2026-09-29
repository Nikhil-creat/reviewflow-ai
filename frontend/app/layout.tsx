import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReviewFlow AI - Autonomous Reputation Engine",
  description: "Multi-agent AI that replies to reviews in your brand voice and turns 5-star reviews into social content. Designed & developed by NIKHIL CHARY SRIRAMOJU.",
  authors: [{ name: "NIKHIL CHARY SRIRAMOJU" }],
  creator: "NIKHIL CHARY SRIRAMOJU",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
