"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "📊 Overview" },
  { href: "/members", label: "👥 Members" },
  { href: "/ranking", label: "🏆 Ranking" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="flex gap-4 border-b border-gray-200 dark:border-gray-700 px-6 py-3 bg-white dark:bg-gray-900 sticky top-0 z-10">
      <span className="font-bold text-lg mr-4">運用保守 Dashboard</span>
      {NAV_ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={`px-3 py-1 rounded-md text-sm transition ${
            pathname === item.href
              ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 font-medium"
              : "hover:bg-gray-100 dark:hover:bg-gray-800"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
