import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Football Analytics",
  description: "Player pizza charts from FBref data",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
