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
    <div className="border-b border-gray-200 dark:border-gray-700">
      {groups.map(group => {
        const tabs = REPORT_TABS.filter(t => t.group === group);
        const { label } = GROUP_CONFIG[group];
        return (
          <div key={group} className="flex items-center overflow-x-auto">
            {/* Section label — narrow, uppercase, muted, non-interactive */}
            <span className="px-3 py-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider whitespace-nowrap flex-shrink-0 select-none border-r border-gray-200 dark:border-gray-700">
              {label}
            </span>
            {/* Tabs in this group */}
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-500'
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
