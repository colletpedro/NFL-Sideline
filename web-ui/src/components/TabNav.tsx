export type TabKey = "overview" | "analysis" | "market" | "matchup";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "analysis", label: "Analysis" },
  { key: "market", label: "Market" },
  { key: "matchup", label: "Matchup" },
];

interface TabNavProps {
  active: TabKey;
  onChange: (tab: TabKey) => void;
}

function TabNav({ active, onChange }: TabNavProps) {
  return (
    <nav className="tabnav" role="tablist" aria-label="Game sections">
      {TABS.map((t) => (
        <button
          key={t.key}
          role="tab"
          aria-selected={active === t.key}
          className={`tabnav-tab ${active === t.key ? "active" : ""}`}
          onClick={() => onChange(t.key)}
        >
          {t.label}
        </button>
      ))}
    </nav>
  );
}

export default TabNav;