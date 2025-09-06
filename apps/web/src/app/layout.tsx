import "../styles/globals.css";
import type { Metadata } from "next";
import { Providers } from "@/components/providers/Providers";
import { AppFlagsProvider } from "@/components/providers/FlagsProvider";

export const metadata: Metadata = {
  title: "Smart Graphic Designer",
  description: "Production-grade UI for NanoDesigner"
};

import { Nav } from "@/components/common/Nav";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="[&_*:where(button,a)]:min-h-[44px]">
        <AppFlagsProvider>
          <Providers>
            <Nav />
            {children}
            <script dangerouslySetInnerHTML={{ __html: `if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}))}` }} />
          </Providers>
        </AppFlagsProvider>
      </body>
    </html>
  );
}

