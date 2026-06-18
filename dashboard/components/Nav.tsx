"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/members", label: "Members" },
  { href: "/ranking", label: "Ranking" },
  { href: "/cohort", label: "Cohort" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="flex items-center gap-1 border-b border-gray-100 dark:border-gray-800 px-6 py-3 bg-white dark:bg-gray-900 sticky top-0 z-10">
      <span className="font-semibold text-base text-gray-700 dark:text-gray-200 mr-6">運用保守 Dashboard</span>
      {NAV_ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
            pathname === item.href
              ? "bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-medium"
              : "text-gray-500 hover:text-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 dark:hover:text-gray-300"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
