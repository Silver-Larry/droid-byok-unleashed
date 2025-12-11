import { useState } from 'react';
import { Terminal, Sun, Moon, Settings, Brain, Github } from 'lucide-react';
import { Toaster } from 'sonner';
import { useConfig } from '../hooks/useConfig';
import { useTheme } from '../hooks/useTheme';
import { StatusBar } from './StatusBar';
import { SettingsPanel } from './SettingsPanel';
import { ThinkingViewer } from './ThinkingViewer';
import { cn } from '../lib/utils';

type Tab = 'thinking';

const tabs: { id: Tab; label: string; icon: typeof Brain }[] = [
  { id: 'thinking', label: 'THINKING', icon: Brain },
];

export function ChatWindow() {
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('thinking');
  const { config, updateConfig } = useConfig();
  const { theme, toggleTheme } = useTheme();

  const sidebarNav = (
    <nav className="w-12 shrink-0 border-r border-border bg-card flex flex-col items-center pt-2">
      {tabs.map(({ id, label, icon: Icon }) => {
        const isActive = activeTab === id && !showSettings;
        return (
          <button
            key={id}
            onClick={() => { setActiveTab(id); setShowSettings(false); }}
            className={cn(
              "relative w-12 h-12 flex items-center justify-center transition-colors cursor-pointer outline-none",
              isActive
                ? "text-primary"
                : "text-primary/40 hover:text-primary/70 dark:text-[#858585] dark:hover:text-primary/70"
            )}
            title={label}
          >
            {isActive && (
              <span className="absolute inset-1.5 bg-[#DDDDE2] dark:bg-primary/20" style={{ borderRadius: '0px' }} />
            )}
            <Icon className="w-6 h-6 relative z-10" strokeWidth={1.5} />
          </button>
        );
      })}
      <div className="mt-auto mb-2">
        <button
          onClick={() => setShowSettings(!showSettings)}
          className={cn(
            "relative w-12 h-12 flex items-center justify-center transition-colors cursor-pointer outline-none",
            showSettings
              ? "text-primary"
              : "text-primary/40 hover:text-primary/70 dark:text-[#858585] dark:hover:text-primary/70"
          )}
          title="Settings"
        >
          {showSettings && (
            <span className="absolute inset-1.5 bg-[#DDDDE2] dark:bg-primary/20" style={{ borderRadius: '0px' }} />
          )}
          <Settings className="w-5 h-5 relative z-10" strokeWidth={1.5} />
        </button>
      </div>
    </nav>
  );

  return (
    <div className="h-screen bg-background text-foreground font-mono selection:bg-primary selection:text-primary-foreground relative overflow-hidden transition-colors duration-300 flex flex-col">
      <Toaster position="bottom-center" theme={theme} richColors />
      <div className="scanline" />
      <div className="w-full flex-1 flex relative z-10 min-h-0">
        {sidebarNav}
        <div className="flex-1 flex flex-col min-h-0">
          <header className="border-b border-border px-4 md:px-6 py-3 shrink-0">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold tracking-tight text-primary flex items-center gap-2">
                <Terminal className="w-5 h-5" />
                <span className="font-pixel text-lg tracking-tighter mt-0.5 text-primary leading-none">DROID BYOK</span>
              </h1>
              <div className="flex items-center gap-3 text-xs">
                <button
                  onClick={toggleTheme}
                  className="flex items-center justify-center w-8 h-8 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer border border-border"
                  title={theme === 'light' ? "Switch to dark mode" : "Switch to light mode"}
                >
                  {theme === 'light' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </header>

          {showSettings ? (
            <SettingsPanel
              config={config}
              onUpdate={updateConfig}
              onClose={() => setShowSettings(false)}
            />
          ) : (
            <ThinkingViewer className="flex-1" />
          )}
        </div>
      </div>
      <footer className="bg-primary text-primary-foreground px-3 py-1 flex justify-between items-center text-[10px] shrink-0">
        <span className="inline-flex items-center gap-3">
          <StatusBar />
        </span>
        <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="hover:opacity-80">
          <Github className="w-3 h-3" />
        </a>
      </footer>
    </div>
  );
}
