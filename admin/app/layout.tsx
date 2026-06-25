import type {Metadata} from "next";
import "./globals.css";
import {Providers} from "@/components/providers";
import {Shell} from "@/components/shell";

export const metadata: Metadata = {
  title: "GNS Admin Console",
  description: "Operate applications, templates, providers, and notification delivery.",
};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body><Providers><Shell>{children}</Shell></Providers></body></html>;
}
