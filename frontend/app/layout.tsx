import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Applicant Information Processor",
  description: "Form-first applicant feature extraction",
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
