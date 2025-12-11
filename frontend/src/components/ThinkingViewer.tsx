import { useState, useEffect, useRef } from 'react';
import { Brain, Play, Square, Trash2, Clock } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '../lib/utils';
import type { ThinkingContent } from '../types';

interface ThinkingViewerProps {
  className?: string;
}

export function ThinkingViewer({ className }: ThinkingViewerProps) {
  const [thinkingItems, setThinkingItems] = useState<ThinkingContent[]>([]);
  const [isCapturing, setIsCapturing] = useState(false);
  const [currentThinking, setCurrentThinking] = useState<string>('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thinkingItems, currentThinking]);

  const startCapture = () => {
    setIsCapturing(true);
    setCurrentThinking('');
    
    // Connect to SSE endpoint for thinking content
    const eventSource = new EventSource('/v1/thinking/stream');
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'thinking') {
          setCurrentThinking(prev => prev + data.content);
        } else if (data.type === 'done') {
          // Save completed thinking
          if (currentThinking) {
            const newItem: ThinkingContent = {
              id: Date.now().toString(),
              content: currentThinking + (data.content || ''),
              timestamp: new Date(),
              model: data.model,
            };
            setThinkingItems(prev => [...prev, newItem]);
            setCurrentThinking('');
          }
        }
      } catch {
        // Handle plain text thinking content
        setCurrentThinking(prev => prev + event.data);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setIsCapturing(false);
      // Save any remaining thinking content
      if (currentThinking) {
        const newItem: ThinkingContent = {
          id: Date.now().toString(),
          content: currentThinking,
          timestamp: new Date(),
        };
        setThinkingItems(prev => [...prev, newItem]);
        setCurrentThinking('');
      }
    };
  };

  const stopCapture = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsCapturing(false);
    // Save any current thinking
    if (currentThinking) {
      const newItem: ThinkingContent = {
        id: Date.now().toString(),
        content: currentThinking,
        timestamp: new Date(),
      };
      setThinkingItems(prev => [...prev, newItem]);
      setCurrentThinking('');
    }
  };

  const clearAll = () => {
    setThinkingItems([]);
    setCurrentThinking('');
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
            Thinking Capture
          </h2>
          {isCapturing && (
            <span className="flex items-center gap-1 text-xs text-primary animate-pulse">
              <span className="w-2 h-2 bg-primary rounded-full" />
              Capturing...
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!isCapturing ? (
            <Button variant="outline" size="sm" onClick={startCapture}>
              <Play className="w-3.5 h-3.5 mr-1.5" />
              Start
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={stopCapture}>
              <Square className="w-3.5 h-3.5 mr-1.5" />
              Stop
            </Button>
          )}
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={clearAll}
            disabled={thinkingItems.length === 0 && !currentThinking}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {thinkingItems.length === 0 && !currentThinking ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <Brain className="w-16 h-16 mb-4 text-primary/20" />
            <p className="text-foreground font-medium">No thinking content captured</p>
            <p className="text-sm mt-2">
              Click "Start" to begin capturing thinking content from the proxy
            </p>
          </div>
        ) : (
          <>
            {/* Historical thinking items */}
            {thinkingItems.map((item) => (
              <div 
                key={item.id} 
                className="border border-border rounded-lg bg-card overflow-hidden"
              >
                <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 border-b border-border text-xs text-muted-foreground">
                  <Clock className="w-3 h-3" />
                  <span>{formatTime(item.timestamp)}</span>
                  {item.model && (
                    <>
                      <span className="text-border">|</span>
                      <span>{item.model}</span>
                    </>
                  )}
                </div>
                <pre className="p-3 text-sm whitespace-pre-wrap font-mono text-foreground/90 leading-relaxed">
                  {item.content}
                </pre>
              </div>
            ))}

            {/* Current streaming thinking */}
            {currentThinking && (
              <div className="border border-primary/50 rounded-lg bg-primary/5 overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-primary/10 border-b border-primary/30 text-xs text-primary">
                  <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
                  <span>Live</span>
                </div>
                <pre className="p-3 text-sm whitespace-pre-wrap font-mono text-foreground/90 leading-relaxed">
                  {currentThinking}
                  <span className="animate-pulse">▊</span>
                </pre>
              </div>
            )}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  );
}
