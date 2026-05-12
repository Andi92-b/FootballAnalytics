export default function Home() {
  return (
    <main className="min-h-screen bg-white flex flex-col items-center py-16 px-4">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Football Analytics</h1>
      <p className="text-gray-500 mb-10">Position-specific pizza charts from FBref data</p>
      {/* PlayerSearch + PizzaChart wired in wire-component skill */}
      <p className="text-gray-400 text-sm">Search coming soon…</p>
    </main>
  );
}
