function App() {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Config Sidebar */}
      <aside className="w-80 bg-white border-r border-gray-200 p-6">
        <h1 className="text-xl font-bold text-gray-900">TradingAgents</h1>
        <p className="text-sm text-gray-500 mt-1">Analysis Dashboard</p>
        {/* ConfigSidebar will go here in Plan 03 */}
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Progress Stepper area */}
        <div className="p-4 border-b border-gray-200 bg-white">
          <p className="text-sm text-gray-400">Agent progress will appear here</p>
        </div>

        {/* Report Tabs area */}
        <div className="flex-1 overflow-auto p-6">
          <p className="text-sm text-gray-400">Report tabs will appear here</p>
        </div>
      </main>
    </div>
  )
}

export default App
