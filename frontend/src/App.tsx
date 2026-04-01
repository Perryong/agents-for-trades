import { useState } from 'react';
import { useAnalysis } from './hooks/useAnalysis';
import { ConfigSidebar } from './components/ConfigSidebar';
import { ProgressStepper } from './components/ProgressStepper';
import { ReportTabs } from './components/ReportTabs';
import { ReportPane } from './components/ReportPane';
import { REPORT_TABS } from './types';
import type { AnalyzeRequest } from './types';

function App() {
  const { state, startAnalysis } = useAnalysis();
  const [activeTab, setActiveTab] = useState('market');
  const [enableOptions, setEnableOptions] = useState(false);

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
    <div className="flex h-screen bg-gray-50">
      {/* Config Sidebar */}
      <aside className="w-80 bg-white border-r border-gray-200 p-6 overflow-y-auto flex-shrink-0">
        <h1 className="text-xl font-bold text-gray-900 mb-1">TradingAgents</h1>
        <p className="text-sm text-gray-500 mb-6">Analysis Dashboard</p>
        <ConfigSidebar
          onAnalyze={handleAnalyze}
          isRunning={state.status === 'running'}
        />
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Progress Stepper */}
        <div className="p-4 border-b border-gray-200 bg-white overflow-y-auto max-h-64">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Agent Progress</h2>
          <ProgressStepper
            completedNodes={state.completedNodes}
            currentNode={state.currentNode}
            enableOptions={enableOptions}
            status={state.status}
          />
        </div>

        {/* Error Banner */}
        {state.status === 'error' && state.errorMsg && (
          <div className="px-6 py-3 bg-red-50 border-b border-red-200 text-red-700 text-sm">
            Error: {state.errorMsg}
          </div>
        )}

        {/* Report Tabs */}
        <div className="bg-white border-b border-gray-200">
          <ReportTabs
            activeTab={activeTab}
            onTabChange={setActiveTab}
            enableOptions={enableOptions}
          />
        </div>

        {/* Report Content */}
        <div className="flex-1 overflow-auto p-6">
          <ReportPane
            content={reportContent}
            status={state.status}
          />
        </div>

        {/* Signal Banner */}
        {state.result?.signal && (
          <div className={`px-6 py-3 text-center text-sm font-bold border-t ${
            state.result.signal.toUpperCase().includes('BUY')
              ? 'bg-green-50 text-green-700 border-green-200'
              : state.result.signal.toUpperCase().includes('SELL')
              ? 'bg-red-50 text-red-700 border-red-200'
              : 'bg-gray-50 text-gray-700 border-gray-200'
          }`}>
            Signal: {state.result.signal}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
