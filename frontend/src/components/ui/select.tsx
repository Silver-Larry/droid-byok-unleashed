import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface SelectOption {
  value: string;
  label: string;
  description?: string;
  disabled?: boolean;
}

export interface SelectProps {
  value?: string;
  onValueChange?: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ value, onValueChange, options, placeholder, disabled = false, className }, ref) => {
    return (
      <div className={cn('relative', className)}>
        <select
          ref={ref}
          value={value ?? ''}
          onChange={(e) => onValueChange?.(e.target.value)}
          disabled={disabled}
          className={cn(
            'flex h-9 w-full appearance-none items-center justify-between border border-input bg-background px-3 py-2 text-sm',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'pr-8'
          )}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 opacity-50 pointer-events-none" />
      </div>
    );
  }
);

Select.displayName = 'Select';

export { Select };
