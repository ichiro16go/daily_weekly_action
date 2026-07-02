export function SignOutButton() {
  return (
    <form action="/api/logout" method="post" className="ml-auto">
      <button
        type="submit"
        className="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
      >
        Sign out
      </button>
    </form>
  );
}
