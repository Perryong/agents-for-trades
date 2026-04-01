import { useState, useEffect } from 'react';
import { useAnalysis } from './hooks/useAnalysis';
import { ConfigSidebar } from './components/ConfigSidebar';
import { ProgressStepper } from './components/ProgressStepper';
import { ReportTabs } from './components/ReportTabs';
import { ReportPane } from './components/ReportPane';
import { REPORT_TABS } from './types';
import type { AnalyzeRequest } from './types';

function getInitialDark(): boolean {
  const stored = localStorage.getItem('theme');
  if (stored === 'dark') return true;
  if (stored === 'light') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function App() {
  const { state, startAnalysis } = useAnalysis();
  const [activeTab, setActiveTab] = useState('market');
  const [enableOptions, setEnableOptions] = useState(false);
  const [dark, setDark] = useState(getInitialDark);

  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [dark]);

  const handleAnalyze = (request: AnalyzeRequest) => {
    setEnableOptions(request.enable_options);
    startAnalysis(request);
  };

  // Find current tab's stateKey to get report content
  const currentTab = REPORT_TABS.find(t => t.id === activeTab);
  const reportContent = state.result && currentTab
    ? (state.result[currentTab.stateKey] as string) || null
    : null;

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Config Sidebar */}
      <aside className="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-6 overflow-y-auto flex-shrink-0">
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">TradingAgents</h1>
          <button
            onClick={() => setDark(d => !d)}
            aria-label="Toggle dark mode"
            className="p-1 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-lg leading-none"
          >
            {dark ? '☀️' : '🌙'}
          </button>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Analysis Dashboard</p>
        <ConfigSidebar
          onAnalyze={handleAnalyze}
          isRunning={state.status === 'running'}
        />
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Progress Stepper */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-y-auto max-h-64">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Agent Progress</h2>
          <ProgressStepper
            completedNodes={state.completedNodes}
            currentNode={state.currentNode}
            enableOptions={enableOptions}
            status={state.status}
          />
        </div>

        {/* Error Banner */}
        {state.status === 'error' && state.errorMsg && (
          <div className="px-6 py-3 bg-red-50 dark:bg-red-900/30 border-b border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
            Error: {state.errorMsg}
          </div>
        )}

        {/* Report Tabs */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <ReportTabs
            activeTab={activeTab}
            onTabChange={setActiveTab}
            enableOptions={enableOptions}
          />
        </div>

        {/* Report Content */}
        <div className="flex-1 overflow-auto p-6 bg-gray-50 dark:bg-gray-900">
          <ReportPane
            content={reportContent}
            status={state.status}
          />
        </div>

        {/* Signal Banner */}
        {state.result?.signal && (
          <div className={`px-6 py-3 text-center text-sm font-bold border-t ${
            state.result.signal.toUpperCase().includes('BUY')
              ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800'
              : state.result.signal.toUpperCase().includes('SELL')
              ? 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
              : 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700'
          }`}>
            Signal: {state.result.signal}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
