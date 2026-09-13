import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import { Geist, Geist_Mono, Noto_Sans_Devanagari, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import { AppHeader } from "@/components/shell/AppHeader";
import { AppFooter } from "@/components/shell/AppFooter";
import { PresenterUrlSync } from "@/components/shell/PresenterControls";
import { STRINGS } from "@/lib/strings";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

// The reference sets the wordmark and the headline figures in a sturdy
// transitional serif, the voice of a printed government report. Source
// Serif 4's optical-size axis keeps the 72px wordmark crisp and the 29px
// figures sturdy from one family.
const sourceSerif = Source_Serif_4({ variable: "--font-source-serif", subsets: ["latin"], axes: ["opsz"] });

// Devanagari context marks (भारत सरकार, विकसित भारत, सत्यमेव जयते), self-hosted so
// they render the same on any projector laptop.
const notoDevanagari = Noto_Sans_Devanagari({
  variable: "--font-noto-deva",
  subsets: ["devanagari"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: { default: STRINGS.brand.name, template: `%s | ${STRINGS.brand.name}` },
  description: STRINGS.framing.premise,
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  colorScheme: "light",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${sourceSerif.variable} ${notoDevanagari.variable}`}
    >
      <body>
        <a href="#main" className="skip-link">
          {STRINGS.brand.skip_link}
        </a>
        <Suspense fallback={null}>
          <PresenterUrlSync />
        </Suspense>
        <AppHeader />
        <main id="main" tabIndex={-1}>
          {children}
        </main>
        <AppFooter />
      </body>
    </html>
  );
}
