import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { ToastProvider } from "@/components/ui/toast";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "TenderProof",
    template: "%s · TenderProof",
  },
  description:
    "Explainable, auditable AI evaluation of government tender eligibility",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900">
        <ToastProvider>
          <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur-md">
            <div className="mx-auto flex h-15 max-w-6xl items-center justify-between px-6 py-3.5">
              <Link href="/" className="group flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-gradient-to-br from-indigo-600 to-indigo-800 text-sm font-bold text-white shadow-sm transition-transform duration-150 group-hover:scale-105">
                  T
                </span>
                <span className="text-[15px] font-semibold tracking-tight text-slate-900">
                  TenderProof
                </span>
              </Link>
              <span className="hidden items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-500 sm:flex">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                LLMs parse · a deterministic rule engine judges
              </span>
            </div>
          </header>
          <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
            {children}
          </main>
          <footer className="border-t border-slate-200/80 bg-white py-5">
            <p className="mx-auto max-w-6xl px-6 text-center text-xs text-slate-400">
              Every verdict cites criterion → document → page → value → rule,
              backed by an append-only hash-chained audit log.
            </p>
          </footer>
        </ToastProvider>
      </body>
    </html>
  );
}
