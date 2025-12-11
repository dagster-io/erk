import {Tooltip} from './Tooltip';

interface TruncatedNameProps {
  name: string;
  maxLength?: number;
  className?: string;
  mode?: 'middle' | 'left';
  cursor?: 'help' | 'pointer';
}

export function TruncatedName({
  name,
  maxLength = 30,
  className = '',
  mode = 'middle',
  cursor = 'help',
}: TruncatedNameProps) {
  if (name.length <= maxLength) {
    return <span className={className}>{name}</span>;
  }

  let truncatedName: string;
  if (mode === 'left') {
    // Left-truncation: show the end of the name (useful for table names)
    truncatedName = `...${name.slice(-(maxLength - 3))}`;
  } else {
    // Middle-truncation: show start and end (default)
    const startLength = Math.floor((maxLength - 3) / 2);
    const endLength = maxLength - 3 - startLength;
    truncatedName = `${name.slice(0, startLength)}...${name.slice(-endLength)}`;
  }

  return (
    <Tooltip content={name} cursor={cursor}>
      <span className={className}>{truncatedName}</span>
    </Tooltip>
  );
}
