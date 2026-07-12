'use client';

import { cn } from '@/lib/utils';
import { Button } from '@/ui/button';

export interface SegmentedControlOption<T extends string> {
  value: T;
  label: string;
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  className,
}: {
  options: readonly SegmentedControlOption<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1 rounded-md bg-muted p-1',
        className
      )}
    >
      {options.map(option => (
        <Button
          key={option.value}
          type='button'
          size='sm'
          variant={option.value === value ? 'secondary' : 'ghost'}
          className='shadow-none'
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
}
