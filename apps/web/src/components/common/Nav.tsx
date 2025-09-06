import Link from "next/link";

export function Nav() {
  return (
    <nav className="flex items-center gap-4 p-4 border-b border-gray-200">
      <Link href="/" className="font-semibold text-blue-600">SGD</Link>
      <Link href="/dashboard" className="hover:text-blue-600 transition-colors">Dashboard</Link>
      <Link href="/projects/demo/assets" className="hover:text-blue-600 transition-colors">Assets</Link>
      <Link href="/projects/demo/canon" className="hover:text-blue-600 transition-colors">Canon</Link>
      <Link href="/projects/demo/compose" className="hover:text-blue-600 transition-colors">Compose</Link>
      <Link href="/projects/demo/history" className="hover:text-blue-600 transition-colors">History</Link>
      <Link href="/projects/demo/templates" className="hover:text-blue-600 transition-colors">Templates</Link>
      <Link href="/admin" className="hover:text-blue-600 transition-colors">Admin</Link>
      <div className="ml-auto">
        <div className="px-3 py-1 bg-gray-100 rounded-md text-sm text-gray-600">
          Demo Mode
        </div>
      </div>
    </nav>
  );
}

