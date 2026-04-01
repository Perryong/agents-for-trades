// SSE event types from the backend
export interface ProgressEvent {
  type: 'node_start' | 'node_end' | 'complete' | 'error';
  node?: string;
  state?: Record<string, unknown>;
  signal?: string;
  message?: string;
}

// Analysis request payload sent to POST /api/analyze/{run_id}
export interface AnalyzeRequest {
  ticker: string;
  date: string;
  analysts: string[];
  enable_options: boolean;
  llm_provider: string;
  deep_think_llm: string;
  quick_think_llm: string;
}

// Full analysis result from the "complete" SSE event
export interface AnalysisResult {
  market_report: string;
  technical_report: string;
  sentiment_report: string;
  news_report: string;
  fundamentals_report: string;
  investment_plan: string;
  trader_investment_plan: string;
  final_trade_decision: string;
  // Options fields (empty string when options disabled)
  volatility_report: string;
  options_flow_report: string;
  options_strategy: string;
  options_legs: string;
  options_pricing_report: string;
  greeks_report: string;
  signal?: string;
}

// State for useReducer in useAnalysis hook
export type AnalysisStatus = 'idle' | 'running' | 'done' | 'error';

export interface AnalysisState {
  status: AnalysisStatus;
  currentNode: string | null;
  completedNodes: string[];
  result: AnalysisResult | null;
  errorMsg: string | null;
}

// Known agent node names for the progress stepper
export const EQUITY_NODES = [
  'Market Analyst',
  'Technical Analyst',
  'Social Analyst',
  'News Analyst',
  'Fundamentals Analyst',
] as const;

export const OPTIONS_NODES = [
  'Options - Volatility Analyst',
  'Options - Flow Analyst',
  'Options - Strategy Selector',
  'Options - Strike/Expiry',
  'Options - Pricing Agent',
  'Options - Legs Builder',
  'Options - Greeks Monitor',
] as const;

export const RESEARCH_NODES = [
  'Bull Researcher',
  'Bear Researcher',
  'Research Manager',
] as const;

export const TRADING_NODES = ['Trader'] as const;

export const RISK_NODES = [
  'Aggressive Analyst',
  'Conservative Analyst',
  'Neutral Analyst',
  'Portfolio Manager',
] as const;

// Report tab definitions
export interface ReportTab {
  id: string;
  label: string;
  stateKey: keyof AnalysisResult;
  optionsOnly?: boolean;
}

export const REPORT_TABS: ReportTab[] = [
  { id: 'market', label: 'Market', stateKey: 'market_report' },
  { id: 'technical', label: 'Technical', stateKey: 'technical_report' },
  { id: 'social', label: 'Social', stateKey: 'sentiment_report' },
  { id: 'news', label: 'News', stateKey: 'news_report' },
  { id: 'fundamentals', label: 'Fundamentals', stateKey: 'fundamentals_report' },
  { id: 'volatility', label: 'Volatility', stateKey: 'volatility_report', optionsOnly: true },
  { id: 'flow', label: 'Flow', stateKey: 'options_flow_report', optionsOnly: true },
  { id: 'strategy', label: 'Strategy', stateKey: 'options_strategy', optionsOnly: true },
  { id: 'legs', label: 'Legs/Order', stateKey: 'options_legs', optionsOnly: true },
  { id: 'pricing', label: 'Pricing', stateKey: 'options_pricing_report', optionsOnly: true },
  { id: 'greeks', label: 'Greeks', stateKey: 'greeks_report', optionsOnly: true },
  { id: 'debate', label: 'Debate History', stateKey: 'investment_plan' },
  { id: 'decision', label: 'Final Decision', stateKey: 'final_trade_decision' },
];
