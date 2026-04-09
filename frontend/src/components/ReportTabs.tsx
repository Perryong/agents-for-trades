import { REPORT_TABS } from '../types';

interface ReportTabsProps {
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function ReportTabs({
  activeTab,
  onTabChange,
}: ReportTabsProps) {
  const visibleTabs = REPORT_TABS;

  return (
    <div className="flex border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
      {visibleTabs.map(tab => (
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
}
