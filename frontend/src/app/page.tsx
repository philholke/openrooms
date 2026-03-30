export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 py-24 bg-white text-gray-900">
      <div className="max-w-2xl text-center space-y-6">
        <h1 className="text-5xl font-bold tracking-tight">OpenRooms</h1>
        <p className="text-xl text-gray-500">
          Open-source restaurant reservation platform
        </p>
        <p className="text-base text-gray-600 leading-relaxed">
          V1 focuses on the core building blocks every restaurant needs:
          Reservations, Table Management, CRM, and Post-Visit Surveys — all
          open-source and self-hostable.
        </p>
        <div className="flex flex-wrap justify-center gap-3 pt-4">
          {["Reservations", "Table Management", "CRM", "Post-Visit Surveys"].map(
            (feature) => (
              <span
                key={feature}
                className="rounded-full bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-700"
              >
                {feature}
              </span>
            )
          )}
        </div>
      </div>
    </main>
  );
}
