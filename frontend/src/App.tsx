import { useState, useEffect, useRef } from 'react';
import { useAnalysis } from './hooks/useAnalysis';
import { useScreener } from './hooks/useScreener';
import { ConfigSidebar } from './components/ConfigSidebar';
import { WatchlistPanel } from './components/WatchlistPanel';
import { ProgressStepper } from './components/ProgressStepper';
import { ReportTabs } from './components/ReportTabs';
import { ReportPane } from './components/ReportPane';
import { ChartScreen } from './components/ChartScreen';
import { TrackRecordScreen } from './components/TrackRecordScreen';
import { GlobalStatusBar } from './components/GlobalStatusBar';
import { REPORT_TABS, getNodeList } from './types';
import type { AnalyzeRequest } from './types';

function getInitialDark(): boolean {
  const stored = localStorage.getItem('theme');
  if (stored === 'dark') return true;
  if (stored === 'light') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function App() {
  const { state, startAnalysis, cancelAnalysis } = useAnalysis();
  const [activeTab, setActiveTab] = useState('market');
  const [enableOptions, setEnableOptions] = useState(false);
  const [dark, setDark] = useState(getInitialDark);
  const [mainSection, setMainSection] = useState<'analysis' | 'screener' | 'chart' | 'trackrecord'>('analysis');
  const [prefillTicker, setPrefillTicker] = useState<string | undefined>(undefined);
  const [llmProvider, setLlmProvider] = useState('google');
  const [quickModel, setQuickModel] = useState('gemini-2.5-flash');
  const [chartTicker, setChartTicker] = useState<string>('');

  // Track the ticker being analyzed for auto-navigation (D-04)
  const lastAnalyzedTicker = useRef<string>('');

  const { state: screenerState, runScreen } = useScreener();
  const totalNodes = getNodeList(enableOptions).length;

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

  // Auto-navigate to Chart screen when analysis completes (D-04)
  useEffect(() => {
    if (state.status === 'done' && state.result) {
      if (lastAnalyzedTicker.current) {
        setChartTicker(lastAnalyzedTicker.current);
        setMainSection('chart');
      }
    }
  }, [state.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAnalyze = (request: AnalyzeRequest) => {
    setEnableOptions(request.enable_options);
    setLlmProvider(request.llm_provider);
    setQuickModel(request.quick_think_llm);
    lastAnalyzedTicker.current = request.ticker;
    startAnalysis(request);
  };

  const handleAnalyzePick = (ticker: string) => {
    setPrefillTicker(ticker);
    setMainSection('analysis');
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
          isRunning={state.status === 'running' || state.status === 'cancelling'}
          prefillTicker={prefillTicker}
        />
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top-level Section Nav */}
        <div className="flex border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <button
            onClick={() => setMainSection('analysis')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              mainSection === 'analysis'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Analysis
          </button>
          <button
            onClick={() => setMainSection('screener')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              mainSection === 'screener'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Screener
          </button>
          <button
            onClick={() => setMainSection('chart')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              mainSection === 'chart'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Chart
          </button>
          <button
            onClick={() => setMainSection('trackrecord')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              mainSection === 'trackrecord'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Track Record
          </button>
        </div>

        <GlobalStatusBar
          status={state.status}
          completedCount={state.completedNodes.length}
          totalCount={totalNodes}
          ticker={lastAnalyzedTicker.current}
          onCancel={cancelAnalysis}
        />

        {mainSection === 'analysis' ? (
          <>
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
                tabLabel={currentTab?.label ?? 'Report'}
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

            {/* View Chart cross-link — shown after analysis completes (D-05) */}
            {state.status === 'done' && (
              <div className="px-6 py-2 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => {
                    if (lastAnalyzedTicker.current) {
                      setChartTicker(lastAnalyzedTicker.current);
                      setMainSection('chart');
                    }
                  }}
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                >
                  View Chart →
                </button>
              </div>
            )}
          </>
        ) : mainSection === 'screener' ? (
          <div className="flex-1 overflow-auto p-6 bg-gray-50 dark:bg-gray-900">
            <WatchlistPanel
              status={screenerState.status}
              picks={screenerState.picks}
              screenedAt={screenerState.screenedAt}
              errorMsg={screenerState.errorMsg}
              onRefresh={() => runScreen(llmProvider, quickModel)}
              onAnalyze={handleAnalyzePick}
            />
          </div>
        ) : mainSection === 'chart' ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            <ChartScreen
              dark={dark}
              initialTicker={chartTicker}
              onViewAnalysis={() => setMainSection('analysis')}
            />
          </div>
        ) : (
          <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900">
            <TrackRecordScreen dark={dark} onNavigateChart={() => setMainSection('chart')} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
