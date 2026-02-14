import {Box, Colors, Tab, Tabs} from '@dagster-io/ui-components';

export type AppMode = 'dashboard' | 'review';

interface ModeToggleProps {
  mode: AppMode;
  onModeChange: (mode: AppMode) => void;
}

export function ModeToggle({mode, onModeChange}: ModeToggleProps) {
  return (
    <Box
      flex={{direction: 'row', gap: 16, alignItems: 'center'}}
      padding={{horizontal: 16, top: 4}}
      background={Colors.backgroundLighterHover()}
      border="bottom"
    >
      <span
        style={{
          fontWeight: 700,
          fontSize: 18,
          fontFamily: 'Geist Mono, monospace',
          color: Colors.linkDefault(),
          marginRight: 8,
          padding: '10px 0',
        }}
      >
        erk
      </span>
      <Tabs selectedTabId={mode} onChange={(newMode: string) => onModeChange(newMode as AppMode)}>
        <Tab id="dashboard" title="Dashboard" />
        <Tab id="review" title="Review plans" />
      </Tabs>
    </Box>
  );
}
