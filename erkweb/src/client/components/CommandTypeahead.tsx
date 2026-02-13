import {useEffect, useRef} from 'react';

import type {SlashCommandInfo} from '../../shared/types.js';
import './CommandTypeahead.css';

interface CommandTypeaheadProps {
  commands: SlashCommandInfo[];
  filter: string;
  selectedIndex: number;
  onSelect: (command: SlashCommandInfo) => void;
}

export function CommandTypeahead({
  commands,
  filter,
  selectedIndex,
  onSelect,
}: CommandTypeaheadProps) {
  const listRef = useRef<HTMLDivElement>(null);

  // Keep selected item in view
  useEffect(() => {
    const list = listRef.current;
    if (!list) {
      return;
    }
    const item = list.children[selectedIndex] as HTMLElement | undefined;
    item?.scrollIntoView({block: 'nearest'});
  }, [selectedIndex]);

  const filtered = commands.filter((cmd) =>
    cmd.name.toLowerCase().startsWith(filter.toLowerCase()),
  );

  if (filtered.length === 0) {
    return null;
  }

  return (
    <div className="command-typeahead" ref={listRef}>
      {filtered.map((cmd, i) => (
        <div
          key={cmd.name}
          className={`command-item ${i === selectedIndex ? 'selected' : ''}`}
          onMouseDown={(e) => {
            e.preventDefault();
            onSelect(cmd);
          }}
        >
          <span className="command-name">/{cmd.name}</span>
          {cmd.argumentHint && <span className="command-hint">{cmd.argumentHint}</span>}
          <span className="command-desc">{cmd.description}</span>
        </div>
      ))}
    </div>
  );
}

export function filterCommands(commands: SlashCommandInfo[], filter: string): SlashCommandInfo[] {
  return commands.filter((cmd) => cmd.name.toLowerCase().startsWith(filter.toLowerCase()));
}
