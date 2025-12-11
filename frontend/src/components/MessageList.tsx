import { useEffect, useRef } from 'react';
import { MessageSquare, Bot, User } from 'lucide-react';
import type { Message } from '../types';
import { cn } from '../lib/utils';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <MessageSquare className="w-12 h-12 mx-auto mb-4 text-primary/30" />
          <p className="text-foreground font-medium">Start a conversation</p>
          <p className="text-sm mt-2">Messages will appear here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-card">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "flex gap-3",
            message.role === 'user' ? 'justify-end' : 'justify-start'
          )}
        >
          {message.role === 'assistant' && (
            <div className="w-8 h-8 shrink-0 bg-primary/10 flex items-center justify-center">
              <Bot className="w-4 h-4 text-primary" />
            </div>
          )}
          <div
            className={cn(
              "max-w-[80%] px-4 py-2",
              message.role === 'user'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-foreground border border-border'
            )}
          >
            <div className="whitespace-pre-wrap break-words text-sm">{message.content}</div>
            {message.role === 'assistant' && isLoading && message.content === '' && (
              <div className="flex space-x-1 text-muted-foreground">
                <span className="animate-bounce">.</span>
                <span className="animate-bounce" style={{ animationDelay: '0.1s' }}>.</span>
                <span className="animate-bounce" style={{ animationDelay: '0.2s' }}>.</span>
              </div>
            )}
          </div>
          {message.role === 'user' && (
            <div className="w-8 h-8 shrink-0 bg-primary flex items-center justify-center">
              <User className="w-4 h-4 text-primary-foreground" />
            </div>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
