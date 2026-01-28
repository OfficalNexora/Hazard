import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Nexora Ops | Monitoring Station",
  description: "Advanced Emergency Monitoring System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // I implemented this layout to provide a persistent, app-like shell.
  // I chose to fix the Sidebar and Header to ensure navigation is always accessible,
  // preventing the user from getting lost during high-stress monitoring operations.
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen bg-background antialiased overflow-hidden`}>
        <div className="flex h-screen">
          {/* Sidebar */}
          <Sidebar />

          {/* Main Content Area */}
          <div className="flex flex-1 flex-col pl-64 transition-all duration-300">
            <Header />
            <main className="flex-1 overflow-y-auto p-6 scroll-smooth">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
