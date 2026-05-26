// src/components/navigation/TopBar.tsx

export default function TopBar() {
  return (
    <header className="flex h-[80px] items-center justify-between border-b border-gray-200 bg-white px-8">
      <div>
        <p className="text-sm text-gray-400">
          Overview &gt; Daily Dashboard
        </p>
      </div>

      <div className="flex items-center gap-4">
        <button className="rounded-full border border-gray-200 p-2">
          🔔
        </button>

        <div className="flex items-center gap-3 rounded-full border border-gray-200 px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#DDF4EE] text-sm font-semibold text-[#0C6B58]">
            CZ
          </div>

          <span className="text-sm font-medium text-gray-700">
            Claire
          </span>
        </div>
      </div>
    </header>
  );
}