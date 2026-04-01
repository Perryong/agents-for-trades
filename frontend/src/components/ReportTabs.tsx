import { REPORT_TABS } from '../types';

interface ReportTabsProps {
  activeTab: string;
  onTabChange: (tabId: string) => void;
  enableOptions: boolean;
}

export function ReportTabs({
  activeTab,
  onTabChange,
  enableOptions,
}: ReportTabsProps) {
  const visibleTabs = REPORT_TABS.filter(t => !t.optionsOnly || enableOptions);

  return (
    <div className="flex border-b border-gray-200 overflow-x-auto">
      {visibleTabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeTab === tab.id
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
