import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FixMyCity AI | Civic Command Center",
  description:
    "A civic intelligence platform to report, prioritize, route, and track city issues.",
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
