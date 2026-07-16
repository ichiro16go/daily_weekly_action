import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { SignOutButton } from "@/components/SignOutButton";

export const metadata: Metadata = {
  title: "運用保守チーム Dashboard",
  description: "Jira チケット分析ダッシュボード",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
        <Nav userMenu={<SignOutButton />} />
        <main className="flex-1 p-6 max-w-7xl mx-auto w-full">{children}</main>
      </body>
    </html>
  );
}
