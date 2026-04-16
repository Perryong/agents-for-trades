import { REPORT_TABS } from '../types';

interface ReportTabsProps {
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

const GROUP_CONFIG: Record<'equity' | 'options' | 'decision', { label: string }> = {
  equity:   { label: 'EQUITY' },
  options:  { label: 'OPTIONS' },
  decision: { label: 'DECISION' },
};

export function ReportTabs({ activeTab, onTabChange }: ReportTabsProps) {
  const groups = ['equity', 'options', 'decision'] as const;

  return (
    <div className="border-b border-border-subtle">
      {groups.map(group => {
        const tabs = REPORT_TABS.filter(t => t.group === group);
        const { label } = GROUP_CONFIG[group];
        return (
          <div key={group} className="flex items-center overflow-x-auto">
            {/* Section label — narrow, uppercase, muted, non-interactive */}
            <span className="px-3 py-2 text-xs font-semibold text-text-tertiary uppercase tracking-wider whitespace-nowrap flex-shrink-0 select-none border-r border-border-subtle">
              {label}
            </span>
            {/* Tabs in this group */}
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-accent-blue text-accent-blue'
                    : 'border-transparent text-text-secondary hover:text-text-primary hover:border-border-default'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        );
      })}
    </div>
  );
}
