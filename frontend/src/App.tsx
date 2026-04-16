import { useState, useRef, useEffect, useMemo } from 'react';
import { useAnalysis } from './hooks/useAnalysis';
import { useScreener } from './hooks/useScreener';
import { useRecommendations } from './hooks/useRecommendations';
import { ConfigSidebar } from './components/ConfigSidebar';
import { WatchlistPanel } from './components/WatchlistPanel';
import { ProgressStepper } from './components/ProgressStepper';
import { ReportTabs } from './components/ReportTabs';
import { ReportPane } from './components/ReportPane';
import { ChartScreen } from './components/ChartScreen';
import { TrackRecordScreen } from './components/TrackRecordScreen';
import { GlobalStatusBar } from './components/GlobalStatusBar';
import { SidePanel } from './components/SidePanel';
import { StatusBar } from './components/StatusBar';
import { RecommendationList } from './components/RecommendationList';
import { ConfigPanel } from './components/ConfigPanel';
import { RegimeBadge } from './components/RegimeBadge';
import { REPORT_TABS, getNodeList } from './types';
import type { AnalyzeRequest } from './types';

type MainSection = 'screener' | 'recommendations' | 'chart' | 'trackrecord';

const TAB_LABELS: Record<MainSection, string> = {
  screener: 'Screener',
  recommendations: 'Recommendations',
  chart: 'Chart',
  trackrecord: 'Track Record',
};

function App() {
  const { state, startAnalysis, cancelAnalysis } = useAnalysis();
  const [activeTab, setActiveTab] = useState('market');
  const [mainSection, setMainSection] = useState<MainSection>('recommendations');
  const [prefillTicker, setPrefillTicker] = useState<string | undefined>(undefined);
  const [llmProvider, setLlmProvider] = useState('google');
  const [quickModel, setQuickModel] = useState('gemini-2.5-flash');
  const [chartTicker, setChartTicker] = useState<string>('');

  // Track the ticker being analyzed for auto-navigation (D-04)
  const lastAnalyzedTicker = useRef<string>('');
  const lastRunTime = useRef<string>('');

  const { state: screenerState, runScreen } = useScreener();
  const { recommendations, loading: recsLoading, error: recsError, approve, skip } = useRecommendations();

  // Session summary for StatusBar
  const sessionSummary = useMemo(() => {
    if (recommendations.length === 0) return '';
    const approved = recommendations.filter(r => r.status === 'approved').length;
    const skipped = recommendations.filter(r => r.status === 'skipped').length;
    const expired = recommendations.filter(r => r.status === 'expired').length;
    const parts: string[] = [];
    if (approved > 0) parts.push(`${approved} approved`);
    if (skipped > 0) parts.push(`${skipped} skipped`);
    if (expired > 0) parts.push(`${expired} expired`);
    return parts.join(', ') || `${recommendations.length} pending`;
  }, [recommendations]);
  const nodeList = getNodeList();
  const totalNodes = nodeList.length;
  const nodeSet = new Set(nodeList);
  const completedCount = new Set(state.completedNodes.filter(n => nodeSet.has(n))).size;

  // Auto-navigate to Chart screen when analysis completes (D-04)
  useEffect(() => {
    if (state.status === 'done' && state.result) {
      lastRunTime.current = new Date().toISOString();
      if (lastAnalyzedTicker.current) {
        setChartTicker(lastAnalyzedTicker.current);
        setMainSection('chart');
      }
    }
  }, [state.status]); // eslint-disable-line react-hooks/exhaustive-deps

  // Keyboard shortcuts: 1=Recommendations, 2=Chart, 3=Track Record
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (document.activeElement?.tagName ?? '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      switch (e.key) {
        case '1': setMainSection('screener'); break;
        case '2': setMainSection('recommendations'); break;
        case '3': setMainSection('chart'); break;
        case '4': setMainSection('trackrecord'); break;
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleAnalyze = (request: AnalyzeRequest) => {
    setLlmProvider(request.llm_provider);
    setQuickModel(request.quick_think_llm);
    lastAnalyzedTicker.current = request.ticker;
    startAnalysis(request);
  };

  const handleAnalyzePick = (ticker: string) => {
    setPrefillTicker(ticker);
    setMainSection('recommendations');
  };

  // Find current tab's stateKey to get report content
  const currentTab = REPORT_TABS.find(t => t.id === activeTab);
  const reportContent = state.result && currentTab
    ? (state.result[currentTab.stateKey] as string) || null
    : null;
  const isEquityTab = currentTab?.group === 'equity';

  return (
    <div className="flex flex-col h-screen min-w-[1280px] bg-bg-base">
      {/* ─── Header Bar (40px) ─── */}
      <header className="h-[40px] flex items-center px-4 border-b border-border-subtle bg-bg-primary flex-shrink-0">
        <span className="text-sm font-semibold text-text-primary mr-4">TradingAgents</span>
        <RegimeBadge />
        <nav className="flex h-full">
          {(Object.keys(TAB_LABELS) as MainSection[]).map((section) => (
            <button
              key={section}
              onClick={() => setMainSection(section)}
              className={`px-3 flex items-center text-[13px] font-medium border-b-2 transition-colors ${
                mainSection === section
                  ? 'border-accent-blue text-accent-blue'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              {TAB_LABELS[section]}
            </button>
          ))}
        </nav>
      </header>

      {/* ─── Middle Area (primary + side panel) ─── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Primary Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <GlobalStatusBar
            status={state.status}
            completedCount={completedCount}
            totalCount={totalNodes}
            ticker={lastAnalyzedTicker.current}
            onCancel={cancelAnalysis}
          />

          {mainSection === 'screener' ? (
            <div className="flex-1 overflow-auto p-4 bg-bg-base">
              <WatchlistPanel
                status={screenerState.status}
                picks={screenerState.picks}
                screenedAt={screenerState.screenedAt}
                errorMsg={screenerState.errorMsg}
                onRefresh={(strategy, maxPicks) => runScreen(llmProvider, quickModel, strategy, maxPicks)}
                onAnalyze={handleAnalyzePick}
              />
            </div>
          ) : mainSection === 'recommendations' ? (
            <div className="flex flex-1 overflow-hidden">
              {/* Config Sidebar within Recommendations tab */}
              <aside className="w-80 bg-bg-secondary border-r border-border-subtle p-4 overflow-y-auto flex-shrink-0">
                <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">Analysis Config</p>
                <ConfigSidebar
                  onAnalyze={handleAnalyze}
                  isRunning={state.status === 'running' || state.status === 'cancelling'}
                  prefillTicker={prefillTicker}
                />
                <div className="mt-4 pt-4 border-t border-border-subtle">
                  <ConfigPanel />
                </div>
              </aside>

              {/* Analysis Results + Recommendations */}
              <div className="flex-1 flex flex-col overflow-hidden">
                {/* Recommendation Cards */}
                <div className="border-b border-border-subtle max-h-[40%] overflow-y-auto">
                  <RecommendationList
                    recommendations={recommendations}
                    loading={recsLoading}
                    error={recsError}
                    onApprove={approve}
                    onSkip={skip}
                  />
                </div>

                {/* Progress Stepper */}
                <div className="p-3 border-b border-border-subtle bg-bg-primary overflow-y-auto max-h-48">
                  <h2 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">Agent Progress</h2>
                  <ProgressStepper
                    completedNodes={state.completedNodes}
                    currentNode={state.currentNode}
                    status={state.status}
                  />
                </div>

                {/* Error Banner */}
                {state.status === 'error' && state.errorMsg && (
                  <div className="px-4 py-2 bg-accent-red/10 border-b border-accent-red/30 text-accent-red text-[13px]">
                    Error: {state.errorMsg}
                  </div>
                )}

                {/* Report Tabs */}
                <div className="bg-bg-primary border-b border-border-subtle">
                  <ReportTabs
                    activeTab={activeTab}
                    onTabChange={setActiveTab}
                  />
                </div>

                {/* Report Content */}
                <div className="flex-1 overflow-auto p-4 bg-bg-base">
                  <ReportPane
                    content={reportContent}
                    status={state.status}
                    tabLabel={currentTab?.label ?? 'Report'}
                    volContext={state.result?.vol_context}
                    isEquityTab={isEquityTab}
                  />
                </div>

                {/* Signal Banner */}
                {state.result?.signal && (
                  <div className={`px-4 py-2 text-center text-[13px] font-bold border-t ${
                    state.result.signal.toUpperCase().includes('BUY')
                      ? 'bg-accent-green/10 text-accent-green border-accent-green/30'
                      : state.result.signal.toUpperCase().includes('SELL')
                      ? 'bg-accent-red/10 text-accent-red border-accent-red/30'
                      : 'bg-bg-primary text-text-secondary border-border-subtle'
                  }`}>
                    Signal: {state.result.signal}
                  </div>
                )}

                {/* View Chart cross-link */}
                {state.status === 'done' && (
                  <div className="px-4 py-2 bg-bg-primary border-t border-border-subtle">
                    <button
                      onClick={() => {
                        if (lastAnalyzedTicker.current) {
                          setChartTicker(lastAnalyzedTicker.current);
                          setMainSection('chart');
                        }
                      }}
                      className="text-[13px] text-accent-blue hover:underline"
                    >
                      View Chart →
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : mainSection === 'chart' ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              <ChartScreen
                initialTicker={chartTicker}
                onViewAnalysis={() => setMainSection('recommendations')}
              />
            </div>
          ) : (
            <div className="flex-1 overflow-auto bg-bg-base">
              <TrackRecordScreen onNavigateChart={() => setMainSection('chart')} />
            </div>
          )}
        </main>

        {/* ─── Side Panel (320px) ─── */}
        <SidePanel onNavigateChart={(ticker) => { setChartTicker(ticker); setMainSection('chart'); }} />
      </div>

      {/* ─── Status Bar (28px) ─── */}
      <StatusBar
        sessionSummary={sessionSummary}
        lastRunTime={lastRunTime.current || undefined}
        pipelineStatus={state.status === 'running' ? `Analyzing ${lastAnalyzedTicker.current}...` : undefined}
      />
    </div>
  );
}

export default App;
